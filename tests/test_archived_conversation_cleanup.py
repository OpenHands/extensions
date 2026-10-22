"""Retention and deletion rules for the archived conversation cleanup script."""

import importlib.util
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "automations"
    / "catalog"
    / "archived-conversation-cleanup"
    / "main.py"
)


def load_script():
    spec = importlib.util.spec_from_file_location("archived_cleanup", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_config(directory: Path, body: str) -> None:
    (directory / "config.json").write_text(body)


def test_retention_days_comes_from_the_rendered_config(tmp_path: Path) -> None:
    """The setup form's value replaces the 14-day default."""
    module = load_script()

    assert module.RETENTION_DAYS == 14
    assert module.load_config(tmp_path) == {}

    write_config(tmp_path, '{"retention_days": 3}')
    assert module.load_config(tmp_path)["retention_days"] == 3

    write_config(tmp_path, '{"retention_days": 14.0}')
    assert module.load_config(tmp_path)["retention_days"] == 14

    write_config(tmp_path, '{"retention_days": 2.5}')
    assert module.load_config(tmp_path)["retention_days"] == 2.5


@pytest.mark.parametrize(
    "body",
    [
        '{"retention_days": 0}',
        '{"retention_days": -1}',
        '{"retention_days": "14"}',
        '{"retention_days": true}',
        '{"retention_days": null}',
        '{"retention_days": "forever"}',
    ],
)
def test_retention_days_rejects_anything_but_a_positive_number(
    tmp_path: Path, body: str
) -> None:
    module = load_script()
    write_config(tmp_path, body)

    with pytest.raises(ValueError):
        module.load_config(tmp_path)


def test_peer_agent_server_url_is_optional_and_trimmed(tmp_path: Path) -> None:
    module = load_script()

    write_config(tmp_path, '{"peer_agent_server_url": " http://127.0.0.1:18000 "}')
    peer = module.load_config(tmp_path)["peer_agent_server_url"]
    assert peer == "http://127.0.0.1:18000"

    write_config(tmp_path, '{"peer_agent_server_url": 18000}')
    with pytest.raises(ValueError):
        module.load_config(tmp_path)


def test_a_config_beside_the_script_is_read_at_run_time(tmp_path: Path) -> None:
    """Import must not read the file: a bad config then ended the run silently."""
    script = tmp_path / "main.py"
    script.write_text(SCRIPT.read_text())
    write_config(tmp_path, '{"retention_days": 5}')

    spec = importlib.util.spec_from_file_location(
        "archived_cleanup_configured", script
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.RETENTION_DAYS == 14
    assert module.load_config()["retention_days"] == 5


def test_run_uses_the_configured_window() -> None:
    module = load_script()
    module.SESSION_KEY = "session"
    module.load_config = lambda directory=None: {"retention_days": 3}
    module.agent_servers = lambda peer_url: ["http://one"]
    cutoffs = []

    module.collect_expired = lambda cutoff, servers: cutoffs.append(cutoff) or []

    module.run()

    expected = datetime.now(timezone.utc) - timedelta(days=3)
    assert abs((cutoffs[0] - expected).total_seconds()) < 60


def test_agent_servers_combines_the_run_server_and_the_peer() -> None:
    module = load_script()

    assert module.agent_servers("") == []

    module.AGENT_SERVER_URL = "http://run"
    assert module.agent_servers("http://peer/") == ["http://run", "http://peer"]
    assert module.agent_servers("http://run") == ["http://run"]


def test_run_falls_back_to_the_peer_environment_variable(monkeypatch) -> None:
    """An empty rendered value must not make a configured environment useless."""
    module = load_script()
    module.SESSION_KEY = "session"
    module.load_config = lambda directory=None: {"peer_agent_server_url": ""}
    captured = []
    module.agent_servers = lambda peer_url: captured.append(peer_url) or [peer_url]
    module.collect_expired = lambda cutoff, servers: []
    monkeypatch.setenv("PEER_AGENT_SERVER_URL", "http://peer")

    module.run()

    assert captured == ["http://peer"]


def test_only_archived_settled_conversations_past_the_window_expire() -> None:
    """Archiving is the opt-in, a settled status the guard, idle time the clock."""
    module = load_script()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=14)
    long_idle = (now - timedelta(days=20)).isoformat()
    recently_used = (now - timedelta(days=1)).isoformat()

    def conversation(**overrides):
        return {
            "tags": {"archived": "true"},
            "execution_status": "finished",
            "updated_at": long_idle,
        } | overrides

    assert module.is_expired(conversation(), cutoff)

    for status in ("idle", "running", "paused", "waiting_for_confirmation", "future"):
        assert not module.is_expired(conversation(execution_status=status), cutoff)

    # A missing status could still be live work, so a delete run leaves it alone.
    assert not module.is_expired(conversation(execution_status=None), cutoff)
    assert not module.is_expired(conversation(tags={}), cutoff)
    assert not module.is_expired(conversation(updated_at=recently_used), cutoff)
    assert not module.is_expired(conversation(updated_at=None), cutoff)


def expired_conversation(identifier: str = "conv-1") -> dict:
    return {
        "id": identifier,
        "tags": {"archived": "true"},
        "execution_status": "finished",
        "updated_at": (datetime.now(timezone.utc) - timedelta(days=20)).isoformat(),
    }


def runnable(module, servers, conversations, request_impl) -> None:
    """Point a loaded script at stand-in servers so run() deletes nothing real."""
    module.SESSION_KEY = "session"
    module.load_config = lambda directory=None: {}
    module.agent_servers = lambda peer_url: servers
    module.list_conversations = lambda server_url: conversations
    module.request = request_impl


def rejecting(code: int):
    def request(server_url, method, path, body=None):
        raise urllib.error.HTTPError(server_url, code, "rejected", None, None)

    return request


def test_list_conversations_follows_next_page_id() -> None:
    module = load_script()
    pages = {
        "limit=100": {"items": [{"id": "conv-1"}], "next_page_id": "page-2"},
        "limit=100&page_id=page-2": {"items": [{"id": "conv-2"}]},
    }
    queries = []

    def fake_request(server_url, method, path, body=None):
        query = path.split("?", 1)[1]
        queries.append(query)
        return pages[query]

    module.SESSION_KEY = "session"
    module.request = fake_request

    found = module.list_conversations("http://one")

    assert [conversation["id"] for conversation in found] == ["conv-1", "conv-2"]
    assert queries == ["limit=100", "limit=100&page_id=page-2"]


def test_a_conversation_listed_by_both_servers_is_deleted_through_the_first() -> None:
    """Each server keeps its own catalog, so a row can arrive twice."""
    module = load_script()
    calls = []
    runnable(
        module,
        ["http://one", "http://two"],
        [expired_conversation()],
        lambda url, method, path, body=None: calls.append((url, method, path)),
    )

    module.run()

    assert calls == [("http://one", "DELETE", "/api/conversations/conv-1")]


@pytest.mark.parametrize("code", [400, 404])
def test_a_delete_answered_gone_counts_as_already_removed(code: int) -> None:
    """The second catalog still lists a row whose data the first delete removed."""
    module = load_script()
    runnable(module, ["http://one"], [expired_conversation()], rejecting(code))

    module.run()


def test_a_failed_delete_fails_the_run() -> None:
    module = load_script()
    runnable(module, ["http://one"], [expired_conversation()], rejecting(500))

    with pytest.raises(RuntimeError, match="deletions failed"):
        module.run()


def test_a_run_that_cannot_list_any_server_fails() -> None:
    """Reporting COMPLETED for a sweep that read nothing would hide an outage."""
    module = load_script()
    module.SESSION_KEY = "session"
    module.load_config = lambda directory=None: {}
    module.agent_servers = lambda peer_url: ["http://one"]

    def unreachable(server_url):
        raise OSError("connection refused")

    module.list_conversations = unreachable

    with pytest.raises(RuntimeError, match="no agent server could be listed"):
        module.run()


def test_a_broken_config_reports_failure_instead_of_ending_at_import() -> None:
    """Before this, a bad config exited at import and no callback ever fired."""
    module = load_script()
    callbacks = []
    module.fire_callback = lambda status="COMPLETED", error=None: callbacks.append(
        (status, error)
    )

    def broken_config(directory=None):
        raise ValueError("config.json: retention_days must be a positive number")

    module.load_config = broken_config

    with pytest.raises(SystemExit) as exited:
        module.main()

    assert exited.value.code == 1
    assert callbacks and callbacks[0][0] == "FAILED"
    assert "positive number" in callbacks[0][1]