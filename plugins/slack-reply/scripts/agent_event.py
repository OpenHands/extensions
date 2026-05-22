"""Push-mode entrypoint: one run per Slack Events API webhook delivery.

Reads the Slack event from `AUTOMATION_EVENT_PAYLOAD`, validates that the
message matches the configured trigger phrases and channel scope, runs the
OpenHands agent, and posts the result back to Slack as a threaded reply.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import traceback

from config import Config
from prompt import Trigger, build_prompt
from slack_client import SlackClient

log = logging.getLogger("slack_reply.event")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def extract_trigger(event_payload: dict) -> Trigger | None:
    """Pull the Slack `event` object out of the webhook envelope and normalise it."""
    # The webhook payload from the automation dispatcher wraps the original
    # provider payload under "payload" or "body" depending on version. We
    # try both, then fall back to assuming the top-level dict is the
    # Slack event_callback envelope itself.
    body = event_payload.get("payload") or event_payload.get("body") or event_payload
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            return None

    inner = body.get("event") if isinstance(body, dict) else None
    if not isinstance(inner, dict):
        return None
    if inner.get("type") != "message":
        return None
    # Ignore bots talking to themselves and message edits/deletes.
    if inner.get("subtype") in {"bot_message", "message_changed", "message_deleted"}:
        return None
    if inner.get("bot_id"):
        return None

    return Trigger(
        channel=inner.get("channel", ""),
        channel_name=None,  # not present in `message` events; resolve on demand if needed
        ts=inner.get("ts", ""),
        thread_ts=inner.get("thread_ts"),
        user=inner.get("user"),
        text=inner.get("text", ""),
    )


def main() -> int:
    cfg = Config.from_env()
    raw = os.environ.get("AUTOMATION_EVENT_PAYLOAD", "{}")
    try:
        event_payload = json.loads(raw)
    except json.JSONDecodeError:
        log.error("AUTOMATION_EVENT_PAYLOAD is not valid JSON: %r", raw[:200])
        return 1

    trigger = extract_trigger(event_payload)
    if trigger is None:
        log.info("event did not produce a usable trigger; skipping")
        return 0

    if not cfg.channel_in_scope(trigger.channel):
        log.info("channel %s not in scope; skipping", trigger.channel)
        return 0

    if not cfg.matches_phrase(trigger.text):
        log.info("message did not match any trigger phrase; skipping")
        return 0

    slack = SlackClient(cfg.bot_token)

    if cfg.reply_mode == "thread+reaction":
        slack.add_reaction(trigger.channel, trigger.ts, cfg.ack_reaction)

    try:
        _run_agent_and_reply(cfg, slack, trigger)
    except Exception:  # noqa: BLE001
        log.exception("agent run failed")
        if cfg.reply_mode != "none":
            slack.post_thread_reply(
                trigger.channel,
                trigger.reply_thread_ts,
                ":warning: I hit an error while working on this. "
                "Check the automation run logs for details.\n"
                f"```{traceback.format_exc(limit=2)}```",
            )
        if cfg.reply_mode == "thread+reaction":
            slack.add_reaction(trigger.channel, trigger.ts, cfg.fail_reaction)
        return 1

    if cfg.reply_mode == "thread+reaction":
        slack.add_reaction(trigger.channel, trigger.ts, cfg.done_reaction)
    return 0


def _run_agent_and_reply(cfg: Config, slack: SlackClient, trigger: Trigger) -> None:
    # Imported lazily so the dry-run / unit-test path doesn't require the SDK.
    from openhands.sdk import Conversation
    from openhands.tools.preset.default import get_default_agent
    from openhands.workspace import OpenHandsCloudWorkspace

    api_key = os.environ["OPENHANDS_API_KEY"]
    api_url = os.environ["OPENHANDS_CLOUD_API_URL"]
    prompt = build_prompt(trigger, slack, cfg)
    log.info("assembled prompt (%d chars)", len(prompt))

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


def _final_assistant_text(conversation) -> str | None:
    """Return the text of the last assistant message in the conversation."""
    events = getattr(getattr(conversation, "state", None), "events", None) or []
    for ev in reversed(list(events)):
        # Be permissive across SDK versions: look for an assistant role and any text content.
        role = getattr(ev, "source", None) or getattr(ev, "role", None)
        if role and str(role).lower() not in {"assistant", "agent"}:
            continue
        text = _coerce_text(ev)
        if text:
            return text
    return None


def _coerce_text(ev) -> str | None:
    # Try common fields used across SDK event shapes.
    for attr in ("text", "content", "message"):
        v = getattr(ev, attr, None)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, list):
            joined = "\n".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in v
            ).strip()
            if joined:
                return joined
    return None


if __name__ == "__main__":
    sys.exit(main())
