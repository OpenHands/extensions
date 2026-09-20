"""Regression coverage for runtime profiles and deterministic review provenance."""

import io
import json
import threading
import types
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


def _load_script(name, monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_BASE", str(tmp_path))
    monkeypatch.delenv("AUTOMATION_MODEL", raising=False)
    path = Path(__file__).parents[1] / "skills" / name / "scripts" / "main.py"
    monkeypatch.syspath_prepend(str(path.parent))
    module = types.ModuleType(name.replace("-", "_"))
    module.__file__ = str(path)
    source = path.read_text()
    if name == "slack-channel-monitor":
        source = source.split("\nPOLL_ITERATIONS = 10", 1)[0]
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


@pytest.fixture(params=["github-pr-reviewer", "slack-channel-monitor"])
def automation(request, monkeypatch, tmp_path):
    return _load_script(request.param, monkeypatch, tmp_path)


@pytest.fixture
def settings(automation, monkeypatch):
    data = {
        "active_profile": "active-profile",
        "agent_settings": {
            "llm": {
                "model": "openai/active",
                "provider_connection_id": "shared-provider",
                "api_key": "resolved-key",
                "base_url": "https://provider.example/v1",
            }
        },
    }
    monkeypatch.setattr(automation, "_fetch_settings", lambda *_: data)
    return data


def test_active_settings_reach_conversation(
    automation, settings, monkeypatch, tmp_path
):
    agent, profile, model = automation._get_agent_and_llm_provenance(
        "http://agent", "session-key"
    )
    payloads = []

    def request(_url, _key, method, path, payload):
        assert (method, path) == ("POST", "/api/conversations")
        payloads.append(payload)
        return {"id": "conversation"}

    monkeypatch.setattr(automation, "_oh_request", request)
    monkeypatch.setattr(automation, "_build_secrets_payload", lambda *_: {})
    monkeypatch.setattr(automation, "_get_mcp_config", lambda *_: None)
    kwargs = {"agent": agent}
    if automation.__name__ == "github_pr_reviewer":
        kwargs["workspace_dir"] = tmp_path
    automation.create_conversation(
        "http://agent", "session-key", "Review this", **kwargs
    )

    assert payloads[0]["agent"]["llm"] == settings["agent_settings"]["llm"]
    assert (profile, model) == ("default", "openai/active")


@pytest.mark.parametrize("linked_provider", [False, True])
def test_selected_profile_reaches_conversation_over_http(
    automation, settings, monkeypatch, tmp_path, linked_provider
):
    """Exercise the real profile GET and conversation POST with a different default."""
    monkeypatch.setenv("AUTOMATION_MODEL", "gpt-latest-med")
    selected = {
        "model": "openai/selected-model",
        "api_key": "synthetic-profile-key",
        "base_url": "https://selected.example/v1",
        "reasoning_effort": "medium",
    }
    if linked_provider:
        # This is the runtime response supplied by Agent Server #4952.
        selected["provider_connection_id"] = "selected-provider"
    requests = []
    payloads = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def respond(self, body):
            content = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            requests.append(("GET", self.path))
            if (
                self.path != "/api/profiles/gpt-latest-med"
                or self.headers.get("X-Session-API-Key") != "test-session"
                or self.headers.get("X-Expose-Secrets") != "plaintext"
            ):
                self.send_error(400)
                return
            self.respond({"config": selected})

        def do_POST(self):
            requests.append(("POST", self.path))
            if (
                self.path != "/api/conversations"
                or self.headers.get("X-Session-API-Key") != "test-session"
            ):
                self.send_error(400)
                return
            body = self.rfile.read(int(self.headers["Content-Length"]))
            payloads.append(json.loads(body))
            self.respond({"id": "test-conversation"})

    monkeypatch.setattr(automation, "_build_secrets_payload", lambda *_: {})
    monkeypatch.setattr(automation, "_get_mcp_config", lambda *_: None)
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}"
            agent, profile, model = automation._get_agent_and_llm_provenance(
                url, "test-session"
            )
            kwargs = {"agent": agent}
            if automation.__name__ == "github_pr_reviewer":
                kwargs["workspace_dir"] = tmp_path
            conversation_id = automation.create_conversation(
                url, "test-session", "Review this", **kwargs
            )
        finally:
            server.shutdown()
            thread.join()

    assert conversation_id == "test-conversation"
    assert payloads[0]["agent"]["llm"] == selected
    assert (profile, model) == ("gpt-latest-med", "openai/selected-model")
    assert requests == [
        ("GET", "/api/profiles/gpt-latest-med"),
        ("POST", "/api/conversations"),
    ]


def test_deleted_profile_falls_back_to_concrete_default(
    automation, settings, monkeypatch
):
    monkeypatch.setenv("AUTOMATION_MODEL", "deleted-profile")

    def fetch(_request):
        raise urllib.error.HTTPError("http://agent", 404, "Not found", {}, None)

    monkeypatch.setattr(automation.urllib.request, "urlopen", fetch)

    agent, profile, model = automation._get_agent_and_llm_provenance(
        "http://agent", "key"
    )

    assert agent["llm"] == settings["agent_settings"]["llm"]
    assert (profile, model) == ("default", "openai/active")


@pytest.mark.parametrize("status", [401, 403, 422, 500])
def test_profile_read_errors_do_not_fall_back(automation, monkeypatch, status):
    monkeypatch.setenv("AUTOMATION_MODEL", "gpt-latest-med")

    def fetch(_request):
        raise urllib.error.HTTPError("http://agent", status, "Failure", {}, None)

    def unexpected_default(*_args):
        pytest.fail("Only a missing profile may fall back to default settings")

    monkeypatch.setattr(automation.urllib.request, "urlopen", fetch)
    monkeypatch.setattr(automation, "_fetch_settings", unexpected_default)
    with pytest.raises(urllib.error.HTTPError) as caught:
        automation._get_agent_and_llm_provenance("http://agent", "key")
    assert caught.value.code == status


@pytest.mark.parametrize("config", [None, {}, "invalid", {"model": "  "}])
def test_invalid_profile_is_not_used(automation, settings, monkeypatch, config):
    monkeypatch.setenv("AUTOMATION_MODEL", "gpt-latest-med")
    monkeypatch.setattr(
        automation.urllib.request,
        "urlopen",
        lambda _request: io.BytesIO(json.dumps({"config": config}).encode()),
    )
    with pytest.raises(RuntimeError, match="no valid model configuration"):
        automation._get_agent_and_llm_provenance("http://agent", "key")


def test_old_server_linked_profile_fails_with_actionable_error(
    automation, settings, monkeypatch
):
    monkeypatch.setenv("AUTOMATION_MODEL", "gpt-latest-med")
    config = {
        "model": "openai/selected-model",
        "provider_connection_id": "selected-provider",
        "api_key": None,
        "base_url": None,
    }
    monkeypatch.setattr(
        automation.urllib.request,
        "urlopen",
        lambda _request: io.BytesIO(json.dumps({"config": config}).encode()),
    )
    with pytest.raises(RuntimeError, match="update Agent Server"):
        automation._get_agent_and_llm_provenance("http://agent", "key")


def test_unnamed_settings_use_default_profile_label(automation, settings):
    settings["active_profile"] = None

    agent, profile, model = automation._get_agent_and_llm_provenance(
        "http://agent", "key"
    )

    assert agent["llm"] == settings["agent_settings"]["llm"]
    assert (profile, model) == ("default", "openai/active")


def test_provenance_footer_replaces_incorrect_model(automation):
    body = "Assessment\n\nLLM profile: `wrong` · Model: `wrong`"
    result = automation._with_llm_provenance(body, "selected", "openai/selected")
    assert result == (
        "Assessment\n\nLLM profile: `selected` · Model: `openai/selected`"
    )
    assert (
        automation._with_llm_provenance(result, "selected", "openai/selected") == result
    )


@pytest.fixture
def reviewer(monkeypatch, tmp_path):
    module = _load_script("github-pr-reviewer", monkeypatch, tmp_path)
    module._AUTH_LOGIN = "review-bot"
    monkeypatch.setattr(module, "conversation_status", lambda *_: "finished")
    monkeypatch.setattr(module, "conversation_final_response", lambda *_: "Review text")
    monkeypatch.setattr(module, "_release_checkout", lambda *_: None)
    return module


@pytest.fixture
def completion():
    rec = {
        "status": "active",
        "conversation_id": "conv",
        "pr_number": 42,
        "head_sha": "head",
        "last_activity": 0.0,
        "review_started_at": "2026-09-10T10:00:00Z",
        "llm_profile": "selected-profile",
        "llm_model": "openai/selected",
    }
    return rec


@pytest.fixture
def review(reviewer, monkeypatch):
    data = {
        "id": 123,
        "user": {"login": "review-bot"},
        "commit_id": "head",
        "state": "COMMENTED",
        "submitted_at": "2026-09-10T10:01:00Z",
        "body": "Assessment",
    }
    monkeypatch.setattr(reviewer, "_github_paginate", lambda *_: [data])
    return data


def _complete(reviewer, rec):
    reviewer._check_conversation_completion(
        rec,
        {42: {"head": {"sha": "head"}}},
        "token",
        "http://agent",
        "key",
        "owner/repo",
    )


@pytest.mark.parametrize("footer", ["", "\n\nLLM profile: `wrong` · Model: `wrong`"])
def test_successful_review_gets_exact_provenance_before_closing(
    reviewer, completion, review, monkeypatch, footer
):
    review["body"] += footer
    writes = []
    monkeypatch.setattr(
        reviewer,
        "_github_request",
        lambda *args, **kwargs: writes.append((args, kwargs)),
    )

    _complete(reviewer, completion)

    assert completion["status"] == "closed"
    assert len(writes) == 1
    args, kwargs = writes[0]
    assert args[1:] == ("PUT", "/repos/owner/repo/pulls/42/reviews/123")
    assert (
        kwargs["body"]["body"]
        == "Assessment\n\nLLM profile: `selected-profile` · Model: `openai/selected`"
    )


def test_correct_review_footer_needs_no_write(
    reviewer, completion, review, monkeypatch
):
    review["body"] = (
        "Assessment\n\nLLM profile: `selected-profile` · Model: `openai/selected`"
    )
    writes = []
    monkeypatch.setattr(
        reviewer, "_github_request", lambda *args, **kwargs: writes.append(args)
    )
    _complete(reviewer, completion)
    assert completion["status"] == "closed"
    assert writes == []


@pytest.mark.parametrize("failure", ["lookup", "repair", "fallback"])
def test_failed_publication_remains_active_for_retry(
    reviewer, completion, review, monkeypatch, failure
):
    def fail(*args, **kwargs):
        raise RuntimeError("GitHub unavailable")

    if failure == "lookup":
        monkeypatch.setattr(reviewer, "_github_paginate", fail)
    elif failure == "fallback":
        monkeypatch.setattr(reviewer, "_github_paginate", lambda *_: [])
    monkeypatch.setattr(reviewer, "_github_request", fail)
    _complete(reviewer, completion)
    assert completion["status"] == "active"
    assert "completed_at" not in completion


@pytest.mark.parametrize(
    "change",
    [
        {"submitted_at": "2026-09-10T09:00:00Z"},
        {"state": "PENDING"},
        {"user": {"login": "someone-else"}},
    ],
)
def test_unrelated_reviews_are_not_relabelled(
    reviewer, completion, review, monkeypatch, change
):
    review.update(change)
    writes = []
    monkeypatch.setattr(
        reviewer,
        "_github_request",
        lambda *args, **kwargs: writes.append((args, kwargs)),
    )
    _complete(reviewer, completion)
    assert completion["status"] == "closed"
    assert len(writes) == 1
    args, kwargs = writes[0]
    assert args[1:] == ("POST", "/repos/owner/repo/issues/42/comments")
    assert "Review text" in kwargs["body"]["body"]
    assert kwargs["body"]["body"].endswith(
        "LLM profile: `selected-profile` · Model: `openai/selected`"
    )
