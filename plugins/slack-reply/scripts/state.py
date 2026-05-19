"""Persistent state for the Slack-reply poll-mode entrypoint.

Tracks "have I already processed this Slack message?" across cron runs
so the same message is never handled twice.

Two backends are supported and selected automatically by `get_store()`:

1. **KVApiStore** - preferred. Uses the platform-provided automation KV
   store (see https://github.com/OpenHands/automation/pull/69). Activated
   when `AUTOMATION_KV_TOKEN` and an API URL are present in the
   environment - i.e., the automation was created with
   `enable_kv_store: true` and the runtime supports it. No mounted
   filesystem state; data lives in the platform, encrypted at rest, and
   round-trips over HTTPS.

2. **SQLiteStore** - fallback. Writes `slack-listener.sqlite3` under
   `$SLACK_STATE_DIR` (default `/automation/storage/state`). If the
   directory isn't writable, falls back further to a tempdir with a
   warning (acceptable for dogfooding; state will not survive sandbox
   restarts in that mode).

The `Store` protocol is small on purpose - the agent_poll script only
needs `claim`, `mark_done`, `mark_failed`, `status_of`, and `prune`.
"""
from __future__ import annotations

import abc
import json
import logging
import os
import random
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib import error as urlerror
from urllib import request as urlrequest

log = logging.getLogger(__name__)

DEFAULT_STATE_DIR = "/automation/storage/state"
DB_FILENAME = "slack-listener.sqlite3"

# All state for the slack-channel-listener lives under this single KV key.
# The single-document model is per-design of the KV API; using one key
# means every claim/mark serializes through the same row lock, which is
# what we want for "exactly once per Slack ts" semantics.
KV_KEY = "slack_listener_state"

# Cap retries on optimistic-concurrency conflicts. Cron runs are
# single-instance by default, so contention is rare; this is a guardrail
# against pathological cases (e.g., manual dispatch overlapping a cron).
KV_MAX_RETRIES = 6


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _key(channel_id: str, ts: str) -> str:
    return f"{channel_id}:{ts}"


# --------------------------------------------------------------------------- #
# Public protocol
# --------------------------------------------------------------------------- #


class Store(abc.ABC):
    """Backend-agnostic interface for the poll-mode state store."""

    @abc.abstractmethod
    def claim(self, channel_id: str, ts: str) -> bool:
        """Atomically reserve a message. True if this caller won the race."""

    @abc.abstractmethod
    def mark_done(self, channel_id: str, ts: str) -> None: ...

    @abc.abstractmethod
    def mark_failed(self, channel_id: str, ts: str, error: str) -> None: ...

    @abc.abstractmethod
    def status_of(self, channel_id: str, ts: str) -> str | None: ...

    @abc.abstractmethod
    def prune_older_than(self, cutoff_iso: str) -> int:
        """Delete entries claimed before `cutoff_iso`. Returns count removed."""

    @abc.abstractmethod
    def close(self) -> None: ...

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #


def get_store() -> Store:
    """Pick the best available backend.

    Prefers the platform KV store when its env vars are present; falls back
    to SQLite otherwise. Emits one INFO line per call so it's obvious in run
    logs which backend was selected.
    """
    if os.environ.get("AUTOMATION_KV_TOKEN") and _resolve_api_url():
        try:
            store = KVApiStore()
            log.info("state backend: KVApiStore (%s)", store.base_url)
            return store
        except Exception:  # noqa: BLE001
            log.warning("KVApiStore init failed; falling back to SQLite", exc_info=True)
    store = SQLiteStore()
    log.info("state backend: SQLiteStore (%s)", store.path)
    return store


def _resolve_api_url() -> str | None:
    # `AUTOMATION_API_URL` is the canonical name per the KV client guide;
    # fall back to `OPENHANDS_CLOUD_API_URL` which is set today by the
    # automation backend for the SDK boilerplate.
    return os.environ.get("AUTOMATION_API_URL") or os.environ.get("OPENHANDS_CLOUD_API_URL")


# --------------------------------------------------------------------------- #
# KV API backend
# --------------------------------------------------------------------------- #


class KVApiStore(Store):
    """State stored in the platform-provided automation KV store.

    Storage layout - a single JSON document at key `slack_listener_state`:

        {
          "<channel>:<ts>": {
            "status": "claimed" | "done" | "failed",
            "claimed_at": "<iso8601>",
            "finished_at": "<iso8601>" | null,
            "error": "<truncated>" | null
          },
          ...
        }

    Every mutator is a read-modify-write with `if_version` for optimistic
    concurrency, retrying on 409 with jittered exponential backoff per the
    KV client guide.
    """

    def __init__(self):
        token = os.environ.get("AUTOMATION_KV_TOKEN")
        api_url = _resolve_api_url()
        if not token or not api_url:
            raise RuntimeError(
                "KVApiStore requires AUTOMATION_KV_TOKEN and AUTOMATION_API_URL"
            )
        self._token = token
        self.base_url = api_url.rstrip("/") + "/v1/kv"

    # ---- HTTP helpers ----

    def _request(
        self, method: str, path: str, body: object | None = None
    ) -> tuple[int, dict, dict]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        data = None if body is None else json.dumps(body).encode()
        req = urlrequest.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._token}")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            resp = urlrequest.urlopen(req, timeout=10)
            payload = resp.read()
            return resp.status, dict(resp.headers), json.loads(payload) if payload else {}
        except urlerror.HTTPError as e:
            payload = e.read()
            try:
                parsed = json.loads(payload) if payload else {}
            except json.JSONDecodeError:
                parsed = {"detail": payload.decode(errors="replace")}
            return e.code, dict(e.headers or {}), parsed

    def _read_state(self) -> tuple[dict, int | None]:
        status, _, body = self._request("GET", f"{KV_KEY}?meta=true")
        if status == 200:
            return body.get("value") or {}, body.get("version")
        if status == 404:
            return {}, None
        raise RuntimeError(f"KV GET failed: {status} {body}")

    def _write_state(self, state: dict, if_version: int | None) -> int:
        path = KV_KEY
        if if_version is not None:
            path = f"{KV_KEY}?if_version={if_version}"
        elif not state:
            path = f"{KV_KEY}?nx=true"
        status, _, _ = self._request("PUT", path, body=state)
        return status

    # ---- RMW loop ----

    def _txn(self, mutate) -> bool:
        """Run a transactional read-modify-write.

        `mutate(state)` may return False to abort the write (returned to
        the caller as False). Returning a truthy value commits the new
        state and returns True. Retries on 409 up to KV_MAX_RETRIES.
        """
        for attempt in range(KV_MAX_RETRIES):
            state, version = self._read_state()
            result = mutate(state)
            if result is False:
                return False
            status = self._write_state(state, if_version=version)
            if status in (200, 201):
                return True
            if status == 409:
                # Jittered exponential backoff. Per the client guide the
                # server suggests a baseline via Retry-After: 1 second.
                delay = (0.1 * (2**attempt)) + random.uniform(0, 0.1)
                time.sleep(delay)
                continue
            if status == 413:
                # State too large. Best-effort: drop entries older than 24h
                # and retry once.
                log.warning("KV state at 64KB cap; pruning aggressively")
                cutoff = datetime.now(tz=timezone.utc).replace(microsecond=0)
                cutoff = cutoff.replace(hour=max(0, cutoff.hour - 24))
                self.prune_older_than(cutoff.isoformat())
                continue
            raise RuntimeError(f"KV PUT failed: {status}")
        raise RuntimeError(f"KV write contention after {KV_MAX_RETRIES} retries")

    # ---- Store interface ----

    def claim(self, channel_id: str, ts: str) -> bool:
        k = _key(channel_id, ts)

        def mutate(state: dict) -> bool:
            if k in state:
                return False  # someone else already has it (or it's done)
            state[k] = {"status": "claimed", "claimed_at": _now_iso(),
                        "finished_at": None, "error": None}
            return True

        return self._txn(mutate)

    def mark_done(self, channel_id: str, ts: str) -> None:
        k = _key(channel_id, ts)

        def mutate(state: dict) -> bool:
            entry = state.get(k) or {}
            entry.update(status="done", finished_at=_now_iso(), error=None)
            state[k] = entry
            return True

        self._txn(mutate)

    def mark_failed(self, channel_id: str, ts: str, error: str) -> None:
        k = _key(channel_id, ts)

        def mutate(state: dict) -> bool:
            entry = state.get(k) or {}
            entry.update(status="failed", finished_at=_now_iso(),
                         error=error[:2000])
            state[k] = entry
            return True

        self._txn(mutate)

    def status_of(self, channel_id: str, ts: str) -> str | None:
        state, _ = self._read_state()
        entry = state.get(_key(channel_id, ts))
        return entry.get("status") if entry else None

    def prune_older_than(self, cutoff_iso: str) -> int:
        removed = 0

        def mutate(state: dict) -> bool:
            nonlocal removed
            to_drop = [
                k for k, v in state.items()
                if (v.get("finished_at") or v.get("claimed_at") or "") < cutoff_iso
            ]
            for k in to_drop:
                del state[k]
            removed = len(to_drop)
            return bool(to_drop) or True  # always commit (no-op write is fine)

        self._txn(mutate)
        return removed

    def close(self) -> None:
        # No persistent connection; nothing to release.
        return None


# --------------------------------------------------------------------------- #
# SQLite backend
# --------------------------------------------------------------------------- #


def _resolve_state_dir() -> Path:
    preferred = Path(os.environ.get("SLACK_STATE_DIR", DEFAULT_STATE_DIR))
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".write-probe"
        probe.write_text("ok")
        probe.unlink(missing_ok=True)
        return preferred
    except OSError as e:
        fallback = Path(tempfile.gettempdir()) / "slack-listener-state"
        fallback.mkdir(parents=True, exist_ok=True)
        log.warning(
            "state dir %s is not writable (%s); falling back to %s. "
            "State will be lost when the sandbox restarts.",
            preferred, e, fallback,
        )
        return fallback


_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_messages (
    channel_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('claimed', 'done', 'failed')),
    claimed_at TEXT NOT NULL,
    finished_at TEXT,
    error TEXT,
    PRIMARY KEY (channel_id, ts)
);
"""


class SQLiteStore(Store):
    """Fallback backend for environments without the platform KV store."""

    def __init__(self, path: Path | None = None):
        self.path = path or (_resolve_state_dir() / DB_FILENAME)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._conn.executescript(_SQLITE_SCHEMA)
        self._conn.commit()

    def claim(self, channel_id: str, ts: str) -> bool:
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO processed_messages "
            "(channel_id, ts, status, claimed_at) VALUES (?, ?, 'claimed', ?)",
            (channel_id, ts, _now_iso()),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def mark_done(self, channel_id: str, ts: str) -> None:
        self._conn.execute(
            "UPDATE processed_messages "
            "SET status='done', finished_at=?, error=NULL "
            "WHERE channel_id=? AND ts=?",
            (_now_iso(), channel_id, ts),
        )
        self._conn.commit()

    def mark_failed(self, channel_id: str, ts: str, error: str) -> None:
        self._conn.execute(
            "UPDATE processed_messages "
            "SET status='failed', finished_at=?, error=? "
            "WHERE channel_id=? AND ts=?",
            (_now_iso(), error[:2000], channel_id, ts),
        )
        self._conn.commit()

    def status_of(self, channel_id: str, ts: str) -> str | None:
        row = self._conn.execute(
            "SELECT status FROM processed_messages WHERE channel_id=? AND ts=?",
            (channel_id, ts),
        ).fetchone()
        return row[0] if row else None

    def prune_older_than(self, cutoff_iso: str) -> int:
        cur = self._conn.execute(
            "DELETE FROM processed_messages "
            "WHERE COALESCE(finished_at, claimed_at) < ?",
            (cutoff_iso,),
        )
        self._conn.commit()
        return cur.rowcount

    def close(self) -> None:
        try:
            self._conn.close()
        except sqlite3.Error:
            pass
