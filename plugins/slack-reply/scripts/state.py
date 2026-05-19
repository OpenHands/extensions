"""Persistent state for the Slack-reply scripts.

Tracks "have I already processed this Slack message?" in a small SQLite
database so the poll-mode entrypoint is idempotent across cron runs.

State lives in `$SLACK_STATE_DIR` (default `/automation/storage/state`),
which is expected to be a directory backed by a volume that survives
across automation runs. If the directory isn't writable, we fall back to
a tempdir and emit a warning - useful for local dogfooding when the
persistent mount may not be present yet.

Schema:

    CREATE TABLE processed_messages (
        channel_id TEXT NOT NULL,
        ts TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('claimed', 'done', 'failed')),
        claimed_at TEXT NOT NULL,
        finished_at TEXT,
        error TEXT,
        PRIMARY KEY (channel_id, ts)
    );

A row in state `claimed` means another concurrent runner has already taken
this message. Concurrent runners race on `INSERT OR IGNORE`; the loser
sees `False` from `claim()` and moves on.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_STATE_DIR = "/automation/storage/state"
DB_FILENAME = "slack-listener.sqlite3"

_SCHEMA = """
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


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _resolve_state_dir() -> Path:
    """Pick the state directory, falling back gracefully if it's not writable."""
    preferred = Path(os.environ.get("SLACK_STATE_DIR", DEFAULT_STATE_DIR))
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        # Probe writability with a tiny file.
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
            preferred,
            e,
            fallback,
        )
        return fallback


class Store:
    """Thin wrapper around a single SQLite file.

    Designed for short-lived poll-mode runs: each `Store` instance opens a
    connection, does its work, then closes. There's no long-lived
    connection pool because cron runs are short.
    """

    def __init__(self, path: Path | None = None):
        self._path = path or (_resolve_state_dir() / DB_FILENAME)
        self._conn = sqlite3.connect(self._path)
        # WAL gives us safe concurrent reads while a writer holds the
        # exclusive write lock; we expect at most a handful of concurrent
        # cron runs, so this is plenty.
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    @property
    def path(self) -> Path:
        return self._path

    def close(self) -> None:
        try:
            self._conn.close()
        except sqlite3.Error:
            pass

    # ---------------- claim/finish lifecycle ----------------

    def claim(self, channel_id: str, ts: str) -> bool:
        """Atomically reserve a message for processing.

        Returns True if this caller successfully claimed it (and should now
        process it), False if another caller already did or it's already
        finished.
        """
        now = _now_iso()
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO processed_messages "
            "(channel_id, ts, status, claimed_at) VALUES (?, ?, 'claimed', ?)",
            (channel_id, ts, now),
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

    # ---------------- diagnostic helpers ----------------

    def status_of(self, channel_id: str, ts: str) -> str | None:
        row = self._conn.execute(
            "SELECT status FROM processed_messages WHERE channel_id=? AND ts=?",
            (channel_id, ts),
        ).fetchone()
        return row[0] if row else None

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
