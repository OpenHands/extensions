"""Unit tests for the datadog-error-monitor automation script.

Focuses on state persistence via the automation KV store.  The cron
script authenticates with a KV JWT token (AUTOMATION_KV_TOKEN); spawned
investigation conversations authenticate with a session API key +
automation_id query param (user-authenticated KV access).
"""

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).parent.parent / "skills" / "datadog-error-monitor" / "scripts" / "main.py"
)


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


def _load_module(monkeypatch, kv_token: str = "", kv_url: str = ""):
    """Import main.py under a unique module name with given KV env."""
    if kv_token:
        monkeypatch.setenv("AUTOMATION_KV_TOKEN", kv_token)
    else:
        monkeypatch.delenv("AUTOMATION_KV_TOKEN", raising=False)
    if kv_url:
        monkeypatch.setenv("AUTOMATION_API_URL", kv_url)
    else:
        monkeypatch.delenv("AUTOMATION_API_URL", raising=False)
    mod_name = f"dd_monitor_{'kv' if kv_token else 'plain'}_{abs(hash((kv_token, kv_url)))}"
    spec = importlib.util.spec_from_file_location(mod_name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def main_no_kv(monkeypatch):
    """Module with no KV env vars — KV unavailable."""
    return _load_module(monkeypatch)


@pytest.fixture
def main_with_kv(monkeypatch, kv_store):
    """Module with KV env vars and patched _kv_get/_kv_set."""
    module = _load_module(monkeypatch, kv_token="fake-kv-token", kv_url="https://fake-kv.example.com")
    monkeypatch.setattr(module, "_kv_get", kv_store.get)
    monkeypatch.setattr(module, "_kv_set", kv_store.set)
    return module


# ── KV availability detection ──────────────────────────────────────────────────


def test_kv_available_with_token(main_with_kv):
    assert main_with_kv._kv_available() is True


def test_kv_unavailable_without_token(main_no_kv):
    assert main_no_kv._kv_available() is False


# ── State persistence (KV store) ──────────────────────────────────────────────


def test_state_defaults_when_kv_empty(main_with_kv, kv_store):
    state = main_with_kv.load_state()
    assert state["version"] == 1
    assert state["known_patterns"] == {}
    assert state["active_conversation"] is None
    assert "last_poll_timestamp" in state


def test_state_round_trips_through_kv(main_with_kv, kv_store):
    state = {
        "version": 1,
        "last_poll_timestamp": "2025-01-01T00:00:00Z",
        "active_conversation": {"id": "conv-1", "status": "running"},
        "known_patterns": {"abc": {"name": "test", "regex": "Error.*"}},
    }
    main_with_kv.save_state(state)
    loaded = main_with_kv.load_state()
    assert loaded == state


def test_state_returns_defaults_when_kv_unavailable(main_no_kv):
    """Without KV, load_state returns defaults and save_state is a no-op."""
    state = main_no_kv.load_state()
    assert state["version"] == 1
    assert state["known_patterns"] == {}


def test_save_warns_when_kv_unavailable(main_no_kv, capsys):
    main_no_kv.save_state({"version": 1, "known_patterns": {}})
    captured = capsys.readouterr()
    assert "not persisted" in captured.out.lower()


# ── Archive persistence ───────────────────────────────────────────────────────


def test_archive_round_trips_through_kv(main_with_kv, kv_store):
    archive = {"pid-1": {"name": "old", "archived_at": "2025-01-01T00:00:00Z"}}
    main_with_kv._save_archive(archive)
    loaded = main_with_kv._load_archive()
    assert loaded == archive


def test_archive_defaults_empty_when_no_kv(main_no_kv):
    assert main_no_kv._load_archive() == {}


# ── archive_stale_patterns ───────────────────────────────────────────────────


def test_archive_stale_patterns_moves_old_patterns(main_with_kv, kv_store):
    old_date = "2020-01-01T00:00:00Z"
    recent_date = "2099-01-01T00:00:00Z"
    state = {
        "version": 1,
        "known_patterns": {
            "old-pid": {"name": "old error", "regex": "old", "last_seen": old_date},
            "new-pid": {"name": "new error", "regex": "new", "last_seen": recent_date},
        },
    }

    count = main_with_kv.archive_stale_patterns(state)
    assert count == 1
    assert "old-pid" not in state["known_patterns"]
    assert "new-pid" in state["known_patterns"]

    archive = main_with_kv._load_archive()
    assert "old-pid" in archive
    assert "archived_at" in archive["old-pid"]


def test_archive_stale_patterns_noop_when_all_recent(main_with_kv, kv_store):
    state = {
        "version": 1,
        "known_patterns": {
            "pid": {"name": "err", "regex": "err", "last_seen": "2099-01-01T00:00:00Z"},
        },
    }

    count = main_with_kv.archive_stale_patterns(state)
    assert count == 0
    assert "pid" in state["known_patterns"]
