"""Unit tests for the datadog-error-monitor automation script.

Focuses on state persistence: the KV-first/local-file-fallback hybrid.
The cron script reads/writes both KV and local file; the spawned
investigation conversation reads/writes only the local file (it has no
AUTOMATION_KV_TOKEN), so the local file must always be written.
"""

import importlib.util
import json
import urllib.error
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).parent.parent / "skills" / "datadog-error-monitor" / "scripts" / "main.py"
)


def _load_module(monkeypatch, workspace_base: Path):
    """Import main.py under its own module name, with a scratch workspace."""
    monkeypatch.setenv("WORKSPACE_BASE", str(workspace_base))
    monkeypatch.delenv("AUTOMATION_KV_TOKEN", raising=False)
    monkeypatch.delenv("AUTOMATION_API_URL", raising=False)
    spec = importlib.util.spec_from_file_location("dd_monitor_main", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def main(monkeypatch, tmp_path):
    return _load_module(monkeypatch, tmp_path / "workspace")


# ── State persistence (local file, no KV) ─────────────────────────────────────


def test_state_defaults_when_no_file_exists(main, tmp_path):
    path = main._state_file_path()
    state = main.load_state(path)

    assert state["version"] == 1
    assert state["known_patterns"] == {}
    assert state["active_conversation"] is None
    assert "last_poll_timestamp" in state


def test_state_round_trips_through_local_file(main):
    path = main._state_file_path()
    state = {
        "version": 1,
        "last_poll_timestamp": "2025-01-01T00:00:00Z",
        "active_conversation": {"id": "conv-1", "status": "running"},
        "known_patterns": {"abc": {"name": "test", "regex": "Error.*"}},
    }
    main.save_state(path, state)

    loaded = main.load_state(path)
    assert loaded == state


def test_unreadable_state_starts_fresh(main):
    path = main._state_file_path()
    Path(path).write_text("{not json")

    state = main.load_state(path)
    assert state["known_patterns"] == {}
    assert state["active_conversation"] is None


def test_state_is_written_atomically(main):
    path = main._state_file_path()
    main.save_state(path, {"version": 1, "known_patterns": {}})

    assert Path(path).exists()
    assert not Path(f"{path}.tmp").exists()


def test_save_always_writes_local_file_even_without_kv(main):
    """The conversation reads/writes the local file, so it must always exist."""
    path = main._state_file_path()
    main.save_state(path, {"version": 1, "known_patterns": {}})

    assert Path(path).exists()
    assert json.loads(Path(path).read_text())["version"] == 1


# ── KV store integration ──────────────────────────────────────────────────────


class _FakeKVStore:
    """In-memory KV store that mimics the automation service's /v1/kv API."""

    def __init__(self):
        self.data: dict[str, object] = {}

    def get(self, key: str):
        return self.data.get(key)

    def set(self, key: str, value):
        self.data[key] = value


@pytest.fixture
def kv_store():
    return _FakeKVStore()


@pytest.fixture
def main_with_kv(monkeypatch, tmp_path, kv_store):
    """Load main.py with KV env vars and patched kv_get/kv_set."""
    monkeypatch.setenv("WORKSPACE_BASE", str(tmp_path / "workspace"))
    monkeypatch.setenv("AUTOMATION_KV_TOKEN", "fake-kv-token")
    monkeypatch.setenv("AUTOMATION_API_URL", "https://fake-kv.example.com")
    spec = importlib.util.spec_from_file_location("dd_monitor_kv_main", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setattr(module, "_kv_get", kv_store.get)
    monkeypatch.setattr(module, "_kv_set", kv_store.set)
    return module


def test_kv_available_detects_token_and_url(main_with_kv):
    assert main_with_kv._kv_available() is True


def test_kv_unavailable_without_token(main, monkeypatch):
    monkeypatch.delenv("AUTOMATION_KV_TOKEN", raising=False)
    assert main._kv_available() is False


def test_save_writes_to_both_kv_and_local_file(main_with_kv, kv_store):
    path = main_with_kv._state_file_path()
    state = {"version": 1, "known_patterns": {"x": {"name": "err"}}}
    main_with_kv.save_state(path, state)

    # Local file written
    assert json.loads(Path(path).read_text()) == state
    # KV written
    assert kv_store.data[main_with_kv._STATE_KEY] == state


def test_load_falls_back_to_kv_when_local_file_missing(main_with_kv, kv_store, monkeypatch):
    """On a fresh pod, the local file is gone but KV has the state."""
    # Use a unique automation_id so no prior test created the file
    monkeypatch.setenv(
        "AUTOMATION_EVENT_PAYLOAD",
        json.dumps({"automation_id": "fresh-pod-test"}),
    )
    path = main_with_kv._state_file_path()
    state = {"version": 1, "known_patterns": {"x": {"name": "err"}}, "active_conversation": None}
    kv_store.set(main_with_kv._STATE_KEY, state)

    # No local file exists
    assert not Path(path).exists()

    loaded = main_with_kv.load_state(path)
    assert loaded == state
    # KV state was written to local file so the conversation can read it
    assert json.loads(Path(path).read_text()) == state


def test_load_prefers_local_file_over_kv(main_with_kv, kv_store):
    """Local file has the conversation's latest changes; it wins over KV."""
    path = main_with_kv._state_file_path()
    local_state = {"version": 1, "known_patterns": {"local": {"name": "new"}}}
    kv_state = {"version": 1, "known_patterns": {"kv": {"name": "old"}}}

    # Write both — local file should be preferred
    main_with_kv._write_local_file(path, local_state)
    kv_store.set(main_with_kv._STATE_KEY, kv_state)

    loaded = main_with_kv.load_state(path)
    assert "local" in loaded["known_patterns"]
    assert "kv" not in loaded["known_patterns"]


def test_load_falls_back_to_kv_on_corrupt_local_file(main_with_kv, kv_store):
    """If the local file is corrupt, KV state is used."""
    path = main_with_kv._state_file_path()
    Path(path).write_text("{corrupt")

    kv_state = {"version": 1, "known_patterns": {"x": {"name": "recovered"}}}
    kv_store.set(main_with_kv._STATE_KEY, kv_state)

    loaded = main_with_kv.load_state(path)
    assert loaded == kv_state


# ── Archive persistence ───────────────────────────────────────────────────────


def test_archive_round_trips_through_local_file(main):
    state_path = main._state_file_path()
    archive_path = main._archive_file_path(state_path)
    archive = {"pid-1": {"name": "old", "archived_at": "2025-01-01T00:00:00Z"}}
    main._save_archive(archive_path, archive)

    loaded = main._load_archive(archive_path)
    assert loaded == archive


def test_archive_writes_to_kv_when_available(main_with_kv, kv_store):
    state_path = main_with_kv._state_file_path()
    archive_path = main_with_kv._archive_file_path(state_path)
    archive = {"pid-1": {"name": "old", "archived_at": "2025-01-01T00:00:00Z"}}
    main_with_kv._save_archive(archive_path, archive)

    assert kv_store.data[main_with_kv._ARCHIVE_KEY] == archive


def test_archive_load_falls_back_to_kv(main_with_kv, kv_store, monkeypatch):
    monkeypatch.setenv(
        "AUTOMATION_EVENT_PAYLOAD",
        json.dumps({"automation_id": "archive-fresh-pod"}),
    )
    state_path = main_with_kv._state_file_path()
    archive_path = main_with_kv._archive_file_path(state_path)
    archive = {"pid-1": {"name": "old", "archived_at": "2025-01-01T00:00:00Z"}}

    # No local file, but KV has it
    kv_store.set(main_with_kv._ARCHIVE_KEY, archive)
    assert not Path(archive_path).exists()

    loaded = main_with_kv._load_archive(archive_path)
    assert loaded == archive


# ── archive_stale_patterns ────────────────────────────────────────────────────


def test_archive_stale_patterns_moves_old_patterns(main):
    state_path = main._state_file_path()
    old_date = "2020-01-01T00:00:00Z"
    recent_date = "2099-01-01T00:00:00Z"
    state = {
        "version": 1,
        "known_patterns": {
            "old-pid": {"name": "old error", "regex": "old", "last_seen": old_date},
            "new-pid": {"name": "new error", "regex": "new", "last_seen": recent_date},
        },
    }

    count = main.archive_stale_patterns(state, state_path)
    assert count == 1
    assert "old-pid" not in state["known_patterns"]
    assert "new-pid" in state["known_patterns"]

    archive = main._load_archive(main._archive_file_path(state_path))
    assert "old-pid" in archive
    assert "archived_at" in archive["old-pid"]


def test_archive_stale_patterns_noop_when_all_recent(main):
    state_path = main._state_file_path()
    state = {
        "version": 1,
        "known_patterns": {
            "pid": {"name": "err", "regex": "err", "last_seen": "2099-01-01T00:00:00Z"},
        },
    }

    count = main.archive_stale_patterns(state, state_path)
    assert count == 0
    assert "pid" in state["known_patterns"]
