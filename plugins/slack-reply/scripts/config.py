"""Configuration loaded from environment variables for the slack-reply scripts.

The `slack-channel-listener` skill bakes these into the automation when it is
created. They are read fresh on every run so a `PATCH` to the automation env
can change behaviour without rebuilding the tarball.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _csv(name: str) -> list[str]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    bot_token: str
    trigger_phrases: list[str]
    scope: str  # single | list | all-public | all-accessible
    channel_id: str | None
    channel_ids: list[str] = field(default_factory=list)
    include_thread_context: bool = True
    include_channel_recent: int = 0
    resolve_user_ids: bool = True
    reply_mode: str = "thread"  # none | thread | thread+reaction
    ack_reaction: str = "eyes"
    done_reaction: str = "white_check_mark"
    fail_reaction: str = "warning"
    poll_lookback_minutes: int = 15

    @classmethod
    def from_env(cls) -> "Config":
        scope = os.environ.get("SLACK_CHANNEL_SCOPE", "single").strip().lower()
        if scope not in {"single", "list", "all-public", "all-accessible"}:
            raise ValueError(
                f"SLACK_CHANNEL_SCOPE must be single|list|all-public|all-accessible, got: {scope!r}"
            )

        phrases = _csv("SLACK_TRIGGER_PHRASES")
        if not phrases:
            raise ValueError("SLACK_TRIGGER_PHRASES is required (comma-separated list)")

        return cls(
            bot_token=os.environ["SLACK_BOT_TOKEN"],
            trigger_phrases=phrases,
            scope=scope,
            channel_id=(os.environ.get("SLACK_CHANNEL_ID") or None),
            channel_ids=_csv("SLACK_CHANNEL_IDS"),
            include_thread_context=_bool("SLACK_INCLUDE_THREAD_CONTEXT", True),
            include_channel_recent=_int("SLACK_INCLUDE_CHANNEL_RECENT", 0),
            resolve_user_ids=_bool("SLACK_RESOLVE_USER_IDS", True),
            reply_mode=os.environ.get("SLACK_REPLY_MODE", "thread").strip().lower(),
            ack_reaction=os.environ.get("SLACK_ACK_REACTION", "eyes"),
            done_reaction=os.environ.get("SLACK_DONE_REACTION", "white_check_mark"),
            fail_reaction=os.environ.get("SLACK_FAIL_REACTION", "warning"),
            poll_lookback_minutes=_int("SLACK_POLL_LOOKBACK_MINUTES", 15),
        )

    def matches_phrase(self, text: str) -> bool:
        lower = text.lower()
        return any(p.lower() in lower for p in self.trigger_phrases)

    def channel_in_scope(self, channel_id: str) -> bool:
        if self.scope == "single":
            return channel_id == self.channel_id
        if self.scope == "list":
            return channel_id in self.channel_ids
        # all-public / all-accessible are scoped at the Slack-app / token level
        # rather than at the filter level, so we accept everything that reaches us.
        return True
