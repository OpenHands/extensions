"""Poll-mode entrypoint: cron-triggered scan for new matching messages.

Designed for environments where the Slack Events API cannot reach the
automation backend (developer laptops, corporate firewalls). Uses message
reactions as persistent state: a message is "claimed" by adding the
`ack_reaction` before processing and "completed" by adding the
`done_reaction` (or `fail_reaction` on error). Already-claimed messages are
skipped on subsequent runs, so this is safe to run more frequently than the
agent itself takes to finish.
"""
from __future__ import annotations

import logging
import os
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone

from agent_event import _final_assistant_text  # reuse the extraction logic
from config import Config
from prompt import Trigger, build_prompt
from slack_client import SlackClient

log = logging.getLogger("slack_reply.poll")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> int:
    cfg = Config.from_env()
    slack = SlackClient(cfg.bot_token)
    self_id = (slack.auth_test() or {}).get("user_id", "")
    if not self_id:
        log.error("auth.test did not return a user_id; cannot use reaction-based state")
        return 1

    oldest = _oldest_ts(cfg)
    candidates = _collect_candidates(cfg, slack, oldest)
    log.info("found %d candidate message(s) older=%s", len(candidates), oldest)

    exit_code = 0
    for trigger in candidates:
        if slack.has_reaction_from_self(trigger.channel, trigger.ts, cfg.ack_reaction, self_id):
            log.info("skipping %s/%s - already acknowledged", trigger.channel, trigger.ts)
            continue
        if slack.has_reaction_from_self(trigger.channel, trigger.ts, cfg.done_reaction, self_id):
            log.info("skipping %s/%s - already completed", trigger.channel, trigger.ts)
            continue

        # Claim the message before doing any work. If another runner also
        # tries to claim it, Slack returns `already_reacted` which we treat
        # as a no-op - the loser will still see the reaction on its next
        # `has_reaction_from_self` check.
        slack.add_reaction(trigger.channel, trigger.ts, cfg.ack_reaction)

        try:
            _run_agent_and_reply(cfg, slack, trigger)
            slack.add_reaction(trigger.channel, trigger.ts, cfg.done_reaction)
        except Exception:  # noqa: BLE001
            log.exception("agent run failed for %s/%s", trigger.channel, trigger.ts)
            slack.add_reaction(trigger.channel, trigger.ts, cfg.fail_reaction)
            if cfg.reply_mode != "none":
                slack.post_thread_reply(
                    trigger.channel,
                    trigger.reply_thread_ts,
                    ":warning: I hit an error while working on this. "
                    "Check the automation run logs for details.\n"
                    f"```{traceback.format_exc(limit=2)}```",
                )
            exit_code = 1

    return exit_code


def _oldest_ts(cfg: Config) -> str:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=cfg.poll_lookback_minutes)
    return f"{cutoff.timestamp():.6f}"


def _collect_candidates(cfg: Config, slack: SlackClient, oldest: str) -> list[Trigger]:
    if cfg.scope == "all-accessible":
        return _candidates_from_search(cfg, slack)
    channels = _scoped_channels(cfg)
    out: list[Trigger] = []
    for channel in channels:
        msgs = slack.conversations_history(channel, oldest=oldest, limit=50)
        for m in msgs:
            text = m.get("text", "")
            if not cfg.matches_phrase(text):
                continue
            if m.get("subtype") in {"bot_message", "message_changed", "message_deleted"}:
                continue
            if m.get("bot_id"):
                continue
            out.append(
                Trigger(
                    channel=channel,
                    channel_name=None,
                    ts=m.get("ts", ""),
                    thread_ts=m.get("thread_ts"),
                    user=m.get("user"),
                    text=text,
                )
            )
    return out


def _scoped_channels(cfg: Config) -> list[str]:
    if cfg.scope == "single":
        return [cfg.channel_id] if cfg.channel_id else []
    if cfg.scope == "list":
        return list(cfg.channel_ids)
    if cfg.scope == "all-public":
        # Walk the workspace's public channels via the bot token. Note: the
        # bot must be a member of each channel to read history; `channels:read`
        # is sufficient for listing, `channels:history` for reading.
        try:
            from slack_sdk import WebClient
            client = WebClient(token=cfg.bot_token)
            ids: list[str] = []
            cursor = None
            while True:
                resp = client.conversations_list(
                    types="public_channel", limit=200, cursor=cursor
                )
                for ch in resp.get("channels", []):
                    if ch.get("is_member"):
                        ids.append(ch["id"])
                cursor = (resp.get("response_metadata") or {}).get("next_cursor")
                if not cursor:
                    break
                time.sleep(0.2)  # gentle on Tier 2 rate limit
            return ids
        except Exception:  # noqa: BLE001
            log.exception("failed to enumerate all-public channels")
            return []
    return []


def _candidates_from_search(cfg: Config, slack: SlackClient) -> list[Trigger]:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=cfg.poll_lookback_minutes)
    after = cutoff.strftime("%Y-%m-%d")
    out: list[Trigger] = []
    for phrase in cfg.trigger_phrases:
        q = f'"{phrase}" after:{after}'
        for hit in slack.search_messages(q, count=50):
            ts = hit.get("ts") or ""
            if not ts:
                continue
            if float(ts) < cutoff.timestamp():
                continue
            channel = (hit.get("channel") or {}).get("id") or ""
            if not channel:
                continue
            out.append(
                Trigger(
                    channel=channel,
                    channel_name=(hit.get("channel") or {}).get("name"),
                    ts=ts,
                    thread_ts=hit.get("thread_ts"),
                    user=hit.get("user"),
                    text=hit.get("text", ""),
                )
            )
    # De-duplicate by (channel, ts) - the same message may match multiple phrases.
    seen: set[tuple[str, str]] = set()
    deduped: list[Trigger] = []
    for t in out:
        key = (t.channel, t.ts)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(t)
    return deduped


def _run_agent_and_reply(cfg: Config, slack: SlackClient, trigger: Trigger) -> None:
    from openhands.sdk import Conversation
    from openhands.tools.preset.default import get_default_agent
    from openhands.workspace import OpenHandsCloudWorkspace

    api_key = os.environ["OPENHANDS_API_KEY"]
    api_url = os.environ["OPENHANDS_CLOUD_API_URL"]
    prompt = build_prompt(trigger, slack, cfg)
    log.info("assembled prompt for %s/%s (%d chars)", trigger.channel, trigger.ts, len(prompt))

    with OpenHandsCloudWorkspace(
        local_agent_server_mode=True,
        cloud_api_url=api_url,
        cloud_api_key=api_key,
    ) as workspace:
        llm = workspace.get_llm()
        secrets = workspace.get_secrets()
        agent = get_default_agent(llm=llm, cli_mode=True)
        conversation = Conversation(agent=agent, workspace=workspace)
        if secrets:
            conversation.update_secrets(secrets)
        conversation.send_message(prompt)
        conversation.run()

        final_text = _final_assistant_text(conversation) or "(agent produced no text output)"
        if cfg.reply_mode != "none":
            slack.post_thread_reply(trigger.channel, trigger.reply_thread_ts, final_text)
        conversation.close()


if __name__ == "__main__":
    sys.exit(main())
