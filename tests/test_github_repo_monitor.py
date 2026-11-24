import io
import json
import urllib.error
from pathlib import Path


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
