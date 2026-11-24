import io
import json
import urllib.error
from pathlib import Path

import pytest
from automation_kv_fake import serve_kv


SCRIPT_PATH = (
    Path(__file__).parent.parent
    / "skills"
    / "github-repo-monitor"
    / "scripts"
    / "main.py"
)


def load_repo_monitor_helpers():
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    namespace: dict = {"__name__": "repo_monitor_main"}
    exec(compile(source, str(SCRIPT_PATH), "exec"), namespace)
    return namespace


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def read(self):
        return json.dumps(self._payload).encode()


def _http_error(url: str, code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, code, "error", {}, io.BytesIO(b"{}"))


def _patch_urlopen(monkeypatch, helpers, handler):
    monkeypatch.setattr(helpers["urllib"].request, "urlopen", handler)


ACTIVE_LLM = {"model": "openai/gpt-5.5", "api_key": "sk-active"}
PROFILE_LLM = {"model": "openai/gpt-5.6-sol", "api_key": "sk-profile"}


def test_automation_model_profile_resolves(monkeypatch):
    helpers = load_repo_monitor_helpers()
    monkeypatch.setenv("AUTOMATION_MODEL", "gpt-5.6-sol")
    monkeypatch.setitem(
        helpers, "_fetch_settings", lambda url, key: {"agent_settings": {"llm": ACTIVE_LLM}}
    )
    seen: dict = {}

    def fake_urlopen(req, *args, **kwargs):
        seen["url"] = req.full_url
        seen["headers"] = {k.lower(): v for k, v in req.header_items()}
        return _FakeResponse({"config": dict(PROFILE_LLM)})

    _patch_urlopen(monkeypatch, helpers, fake_urlopen)

    agent = helpers["_get_agent_dict"]("http://agent:8000", "key")

    assert seen["url"] == "http://agent:8000/api/profiles/gpt-5.6-sol"
    assert seen["headers"]["x-expose-secrets"] == "plaintext"
    assert agent["llm"]["model"] == "openai/gpt-5.6-sol"
    assert agent["llm"]["api_key"] == "sk-profile"
    assert agent["llm"]["usage_id"] == "profile:gpt-5.6-sol"


def test_missing_profile_falls_back_to_active(monkeypatch):
    helpers = load_repo_monitor_helpers()
    monkeypatch.setenv("AUTOMATION_MODEL", "renamed-profile")
    monkeypatch.setitem(
        helpers, "_fetch_settings", lambda url, key: {"agent_settings": {"llm": ACTIVE_LLM}}
    )

    def fake_urlopen(req, *args, **kwargs):
        raise _http_error(req.full_url, 404)

    _patch_urlopen(monkeypatch, helpers, fake_urlopen)

    agent = helpers["_get_agent_dict"]("http://agent:8000", "key")

    assert agent["llm"] == ACTIVE_LLM


def test_no_automation_model_uses_active_profile(monkeypatch):
    helpers = load_repo_monitor_helpers()
    monkeypatch.delenv("AUTOMATION_MODEL", raising=False)
    monkeypatch.setitem(
        helpers, "_fetch_settings", lambda url, key: {"agent_settings": {"llm": ACTIVE_LLM}}
    )
    calls: list = []

    def fake_urlopen(req, *args, **kwargs):
        calls.append(req.full_url)
        raise AssertionError("no profile request expected")

    _patch_urlopen(monkeypatch, helpers, fake_urlopen)

    agent = helpers["_get_agent_dict"]("http://agent:8000", "key")

    assert agent["llm"] == ACTIVE_LLM
    assert calls == []


# ── State size and the KV store's per-value limit ─────────────────────────────


@pytest.fixture
def kv_server():
    with serve_kv() as handler:
        yield handler


def _load_with_kv(kv_server) -> dict:
    helpers = load_repo_monitor_helpers()
    helpers["_KV_TOKEN"] = "kv-token"
    helpers["_KV_BASE"] = kv_server.base
    return helpers


def _state_size(state: dict) -> int:
    return len(json.dumps(state, ensure_ascii=False).encode())


def _closed_conversation(number: int) -> dict:
    return {
        "conversation_id": f"{number:08d}-0000-4000-8000-000000000000",
        "issue_number": number,
        "issue_type": "issue",
        "html_url": f"https://github.com/owner/repo/issues/{number}",
        "status": "closed",
        "last_activity": 1_700_000_000.0 + number,
    }


def _long_used_state(target_bytes: int, ids: int = 5000) -> dict:
    """A state as the monitor leaves it after a long time on a busy repo:
    `ids` comment IDs (MAX_PROCESSED_IDS by default) and closed conversations,
    which are never pruned, added up to `target_bytes`."""
    state = {
        "version": 1,
        "repo": "owner/repo",
        "last_poll": "2026-01-01T00:00:00Z",
        "conversations": {},
        "processed_comment_ids": list(range(3_000_005_000 - ids, 3_000_005_000)),
        "own_comment_ids": list(range(3_100_000_000, 3_100_000_020)),
    }
    for number in range(1, 10_000):
        state["conversations"][str(number)] = _closed_conversation(number)
        if _state_size(state) > target_bytes:
            del state["conversations"][str(number)]
            break
    return state


def _fake_github_and_agent(monkeypatch, helpers, trigger: dict, calls: dict) -> None:
    """Stub the GitHub API and the agent server, the script's external boundary."""

    def github_request(token, method, path, params=None, body=None):
        if path.endswith("/permission"):
            return {"permission": "write"}, {}
        if method == "POST" and path.endswith("/comments"):
            calls["acks"].append(path)
            return {"id": 3_200_000_000 + len(calls["acks"])}, {}
        if path.startswith("/repos/owner/repo/issues/"):
            return {"number": 9999, "title": "Bug", "body": "", "html_url": trigger["html_url"]}, {}
        raise AssertionError(f"unexpected GitHub request {method} {path}")

    def github_paginate(token, path, params=None):
        return [trigger] if path == "/repos/owner/repo/issues/comments" else []

    def create_conversation(agent_url, api_key, prompt, *args, **kwargs):
        calls["conversations"].append(prompt)
        return f"conv-{len(calls['conversations'])}"

    for name, fake in {
        "_resolve_github_token": lambda: "gh-token",
        "_verify_token_and_repo": lambda token, repo: "repo-owner",
        "get_secret": lambda name: "",
        "_github_request": github_request,
        "_github_paginate": github_paginate,
        "create_conversation": create_conversation,
        "send_to_conversation": lambda *args: None,
        "conversation_status": lambda *args: "running",
    }.items():
        monkeypatch.setitem(helpers, name, fake)


def test_a_trigger_is_handled_once_when_the_state_has_grown_to_the_kv_limit(
    monkeypatch, kv_server
):
    kv_server.store["state"] = _long_used_state(64 * 1024 - 200)
    trigger = {
        "id": 3_999_999_999,
        "body": "@openhands please fix this",
        "user": {"login": "maintainer", "type": "User"},
        "created_at": "2026-01-01T00:05:00Z",
        "html_url": "https://github.com/owner/repo/issues/9999#issuecomment-3999999999",
        "issue_url": "https://api.github.com/repos/owner/repo/issues/9999",
    }
    errors = []
    calls = {"acks": [], "conversations": []}
    for _ in range(2):  # two cron runs; GitHub returns the comment both times
        helpers = _load_with_kv(kv_server)
        _fake_github_and_agent(monkeypatch, helpers, trigger, calls)
        try:
            helpers["main"]()
        except Exception as exc:  # noqa: BLE001 - the run's outcome is what is tested
            errors.append(exc)

    assert len(calls["conversations"]) == 1, "the same trigger started a second conversation"
    assert len(calls["acks"]) == 1
    assert errors == []
    saved = kv_server.store["state"]
    assert _state_size(saved) <= helpers["STATE_BUDGET_BYTES"]
    assert trigger["id"] in saved["processed_comment_ids"]
    assert saved["conversations"]["9999"]["status"] == "active"


def test_state_is_trimmed_to_the_limit_a_deployment_reports(kv_server):
    kv_server.limit = 16 * 1024
    helpers = _load_with_kv(kv_server)
    state = _long_used_state(40 * 1024, ids=2000)

    helpers["save_state"](state)

    first, second = kv_server.puts
    assert first > kv_server.limit
    assert second <= kv_server.limit * 3 // 4
    assert kv_server.store["state"]["processed_comment_ids"][-1] == 3_000_004_999


def test_a_413_without_a_limit_is_reported_with_the_key_and_size(monkeypatch):
    helpers = load_repo_monitor_helpers()
    helpers["_KV_BASE"] = "http://kv"

    def refuse(req, *args, **kwargs):
        raise urllib.error.HTTPError(req.full_url, 413, "too large", {}, io.BytesIO(b""))

    _patch_urlopen(monkeypatch, helpers, refuse)

    with pytest.raises(helpers["KVValueTooLarge"], match="key 'state' is 15 bytes"):
        helpers["_kv_set"]("state", {"a": "x" * 6})


def test_fit_state_drops_old_ids_then_closed_conversations_never_active_ones():
    helpers = load_repo_monitor_helpers()
    state = _long_used_state(80 * 1024)
    state["conversations"]["9999"] = dict(_closed_conversation(9999), status="active")
    newest_closed = max(
        (k for k, r in state["conversations"].items() if r["status"] == "closed"),
        key=lambda k: state["conversations"][k]["last_activity"],
    )

    helpers["_fit_state"](state, 24 * 1024)

    assert _state_size(state) <= 24 * 1024
    assert len(state["processed_comment_ids"]) == helpers["MIN_KEPT_IDS"]
    assert state["processed_comment_ids"][-1] == 3_000_004_999
    assert state["conversations"]["9999"]["status"] == "active"
    assert newest_closed in state["conversations"]
    assert "1" not in state["conversations"]
