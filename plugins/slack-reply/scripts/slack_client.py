"""Thin Slack Web API wrapper used by the slack-reply scripts.

We use the official `slack_sdk` to handle retries and rate limits. All
methods are best-effort: callers should treat failures as recoverable and
fall back to logging rather than crashing the automation run.
"""
from __future__ import annotations

import logging
import re
from typing import Iterable

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

log = logging.getLogger(__name__)

_USER_MENTION_RE = re.compile(r"<@([UW][A-Z0-9]+)>")


class SlackClient:
    def __init__(self, token: str):
        self._client = WebClient(token=token)
        self._user_cache: dict[str, str] = {}

    # ---------------- posting ----------------

    def post_thread_reply(self, channel: str, thread_ts: str, text: str) -> dict | None:
        try:
            return self._client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=text,
                reply_broadcast=False,
                unfurl_links=False,
                unfurl_media=False,
            ).data
        except SlackApiError as e:
            log.warning("chat.postMessage failed: %s", e.response.get("error"))
            return None

    def add_reaction(self, channel: str, ts: str, name: str) -> None:
        try:
            self._client.reactions_add(channel=channel, timestamp=ts, name=name)
        except SlackApiError as e:
            # already_reacted is a no-op for our purposes
            err = e.response.get("error")
            if err and err != "already_reacted":
                log.warning("reactions.add(%s) failed: %s", name, err)

    # ---------------- reading ----------------

    def get_permalink(self, channel: str, ts: str) -> str | None:
        try:
            return self._client.chat_getPermalink(channel=channel, message_ts=ts).get("permalink")
        except SlackApiError:
            return None

    def conversations_history(
        self, channel: str, *, latest: str | None = None, oldest: str | None = None, limit: int = 20
    ) -> list[dict]:
        try:
            resp = self._client.conversations_history(
                channel=channel, latest=latest, oldest=oldest, limit=limit
            )
            return list(resp.get("messages", []))
        except SlackApiError as e:
            log.warning("conversations.history failed: %s", e.response.get("error"))
            return []

    def conversations_replies(self, channel: str, thread_ts: str, *, limit: int = 50) -> list[dict]:
        try:
            resp = self._client.conversations_replies(
                channel=channel, ts=thread_ts, limit=limit
            )
            return list(resp.get("messages", []))
        except SlackApiError as e:
            log.warning("conversations.replies failed: %s", e.response.get("error"))
            return []

    def reactions_on_message(self, channel: str, ts: str) -> list[dict]:
        try:
            resp = self._client.reactions_get(channel=channel, timestamp=ts)
            return list((resp.get("message") or {}).get("reactions", []))
        except SlackApiError as e:
            err = e.response.get("error")
            # `no_reaction` is the expected "nothing here" response
            if err and err != "no_reaction":
                log.warning("reactions.get failed: %s", err)
            return []

    def has_reaction_from_self(self, channel: str, ts: str, name: str, self_user_id: str) -> bool:
        for r in self.reactions_on_message(channel, ts):
            if r.get("name") == name and self_user_id in (r.get("users") or []):
                return True
        return False

    # ---------------- search (multi-channel poll mode) ----------------

    def search_messages(self, query: str, *, count: int = 50) -> list[dict]:
        """Workspace-wide message search. Requires a user token with `search:read`."""
        try:
            resp = self._client.search_messages(query=query, count=count, sort="timestamp", sort_dir="desc")
            return list(((resp.get("messages") or {}).get("matches")) or [])
        except SlackApiError as e:
            log.warning("search.messages failed: %s", e.response.get("error"))
            return []

    # ---------------- identity / user resolution ----------------

    def auth_test(self) -> dict:
        try:
            return self._client.auth_test().data
        except SlackApiError as e:
            log.warning("auth.test failed: %s", e.response.get("error"))
            return {}

    def display_name(self, user_id: str) -> str:
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        try:
            resp = self._client.users_info(user=user_id)
            user = resp.get("user") or {}
            profile = user.get("profile") or {}
            name = (
                profile.get("display_name_normalized")
                or profile.get("real_name_normalized")
                or user.get("name")
                or user_id
            )
        except SlackApiError:
            name = user_id
        self._user_cache[user_id] = name
        return name

    def resolve_mentions(self, text: str) -> str:
        """Replace `<@U123>` mentions with `@DisplayName` for human readability."""
        def _sub(m: re.Match) -> str:
            return f"@{self.display_name(m.group(1))}"

        return _USER_MENTION_RE.sub(_sub, text)


def iter_message_chunks(messages: Iterable[dict]) -> Iterable[tuple[str, str, str]]:
    """Yield `(ts, user_id, text)` for renderable messages, oldest first."""
    seen: list[tuple[str, str, str]] = []
    for m in messages:
        if m.get("subtype") in {"channel_join", "channel_leave"}:
            continue
        seen.append((m.get("ts", ""), m.get("user") or m.get("bot_id") or "?", m.get("text", "")))
    seen.sort(key=lambda row: row[0])
    yield from seen
