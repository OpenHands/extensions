"""Build the agent prompt from a Slack message + optional surrounding context."""
from __future__ import annotations

from dataclasses import dataclass

from config import Config
from slack_client import SlackClient, iter_message_chunks


@dataclass(frozen=True)
class Trigger:
    """The Slack message that caused this automation run."""
    channel: str
    channel_name: str | None
    ts: str
    thread_ts: str | None  # parent thread ts, or None if not in a thread
    user: str | None
    text: str

    @property
    def reply_thread_ts(self) -> str:
        """Always reply in a thread - if the trigger is not yet a thread, start one at its ts."""
        return self.thread_ts or self.ts


def build_prompt(trigger: Trigger, slack: SlackClient, cfg: Config) -> str:
    """Compose the initial agent message from the trigger and configured context."""
    pieces: list[str] = []

    triggered_by = slack.display_name(trigger.user) if trigger.user else "an unknown user"
    channel_label = f"#{trigger.channel_name}" if trigger.channel_name else trigger.channel
    permalink = slack.get_permalink(trigger.channel, trigger.ts)

    header = [
        f"You were triggered by a Slack message in {channel_label}.",
        f"Triggering user: @{triggered_by}",
    ]
    if permalink:
        header.append(f"Permalink: {permalink}")
    pieces.append("\n".join(header))

    if cfg.include_thread_context and trigger.thread_ts and trigger.thread_ts != trigger.ts:
        thread_msgs = slack.conversations_replies(trigger.channel, trigger.thread_ts, limit=50)
        # Exclude the trigger message itself from "prior" context (it appears at the end).
        prior = [m for m in thread_msgs if m.get("ts") != trigger.ts]
        if prior:
            rendered = _render_messages(prior, slack, cfg)
            pieces.append(f"Thread context ({len(prior)} prior messages):\n{rendered}")

    if cfg.include_channel_recent > 0:
        recent = slack.conversations_history(
            trigger.channel, latest=trigger.ts, limit=cfg.include_channel_recent
        )
        # `latest` includes the boundary - drop the trigger message if present.
        recent = [m for m in recent if m.get("ts") != trigger.ts]
        if recent:
            rendered = _render_messages(recent, slack, cfg)
            pieces.append(
                f"Recent channel context ({len(recent)} messages before the trigger):\n{rendered}"
            )

    trigger_text = (
        slack.resolve_mentions(trigger.text) if cfg.resolve_user_ids else trigger.text
    )
    pieces.append(f"Triggering message:\n  @{triggered_by}: {trigger_text}")

    pieces.append(
        "Treat the triggering message (with the trigger phrase stripped) as the user's "
        "request and respond to it. When you finish, return your final answer as your "
        "last assistant message - the automation will post it back to Slack as a "
        "threaded reply automatically."
    )

    return "\n\n".join(pieces)


def _render_messages(messages: list[dict], slack: SlackClient, cfg: Config) -> str:
    lines: list[str] = []
    for ts, user_id, text in iter_message_chunks(messages):
        if cfg.resolve_user_ids and user_id and user_id.startswith(("U", "W")):
            speaker = f"@{slack.display_name(user_id)}"
        elif user_id:
            speaker = f"<{user_id}>"
        else:
            speaker = "<unknown>"
        body = slack.resolve_mentions(text) if cfg.resolve_user_ids else text
        lines.append(f"  {speaker}: {body}")
    return "\n".join(lines)
