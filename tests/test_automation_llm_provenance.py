"""Regression coverage for runtime profiles and deterministic review provenance."""

import io
import json
import re
import sys
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


# --- Legacy reviewer (main.py polling): a footer only on this run's own review

DISCLOSURE = "_This review was posted by an AI agent (OpenHands)._"
CONV_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
CONV_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
FOOTER_A = "LLM profile: `selected-profile` · Model: `openai/selected`"


def _marked(conversation_id, text="Assessment\n\n✅ APPROVED"):
    return f"{DISCLOSURE}\n<!-- openhands-review-run: {conversation_id} -->\n\n{text}"


@pytest.fixture
def reviewer(monkeypatch, tmp_path):
    module = _load_script("github-pr-reviewer", monkeypatch, tmp_path)
    module._AUTH_LOGIN = "review-bot"
    monkeypatch.setattr(module, "conversation_status", lambda *_: "finished")
    monkeypatch.setattr(module, "conversation_final_response", lambda *_: "Review text")
    monkeypatch.setattr(module, "_release_checkout", lambda *_: None)
    return module


def _record(conversation_id=CONV_A, profile="selected-profile", model="openai/selected"):
    return {
        "status": "active",
        "conversation_id": conversation_id,
        "pr_number": 42,
        "head_sha": "head",
        "last_activity": 0.0,
        "llm_profile": profile,
        "llm_model": model,
    }


@pytest.fixture
def completion():
    return _record()


class _GitHub:
    """One PR's reviews and comments, shared by every run that reads them."""

    def __init__(self, *bodies):
        self.reviews = [
            {
                "id": 101 + index,
                "user": {"login": "review-bot"},
                "commit_id": "head",
                "state": "COMMENTED",
                "submitted_at": f"2026-09-10T10:0{index}:00Z",
                "body": body,
            }
            for index, body in enumerate(bodies)
        ]
        self.writes = []

    def paginate(self, _token, path):
        assert path == "/repos/owner/repo/pulls/42/reviews"
        return [dict(review) for review in self.reviews]

    def request(self, _token, method, path, body=None):
        self.writes.append((method, path, body))
        if method == "PUT":
            review_id = int(path.rsplit("/", 1)[1])
            for review in self.reviews:
                if review["id"] == review_id:
                    review["body"] = body["body"]
        return {}

    def install(self, module, monkeypatch):
        monkeypatch.setattr(module, "_github_paginate", self.paginate)
        monkeypatch.setattr(module, "_github_request", self.request)
        return self


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
def test_own_review_gets_exact_provenance_before_closing(
    reviewer, completion, monkeypatch, footer
):
    github = _GitHub(_marked(CONV_A) + footer).install(reviewer, monkeypatch)

    _complete(reviewer, completion)

    assert completion["status"] == "closed"
    assert github.writes == [
        (
            "PUT",
            "/repos/owner/repo/pulls/42/reviews/101",
            {"body": f"{_marked(CONV_A)}\n\n{FOOTER_A}"},
        )
    ]


def test_correct_review_footer_needs_no_write(reviewer, completion, monkeypatch):
    github = _GitHub(f"{_marked(CONV_A)}\n\n{FOOTER_A}").install(reviewer, monkeypatch)

    _complete(reviewer, completion)

    assert completion["status"] == "closed"
    assert github.writes == []


@pytest.mark.parametrize("failure", ["lookup", "repair", "fallback"])
def test_failed_publication_remains_active_for_retry(
    reviewer, completion, monkeypatch, failure
):
    def fail(*args, **kwargs):
        raise RuntimeError("GitHub unavailable")

    _GitHub(_marked(CONV_A)).install(reviewer, monkeypatch)
    if failure == "lookup":
        monkeypatch.setattr(reviewer, "_github_paginate", fail)
    elif failure == "fallback":
        monkeypatch.setattr(reviewer, "_github_paginate", lambda *_: [])
    monkeypatch.setattr(reviewer, "_github_request", fail)
    _complete(reviewer, completion)
    assert completion["status"] == "active"
    assert "completed_at" not in completion


@pytest.mark.parametrize(
    "body",
    [
        "Assessment\n\n✅ APPROVED",
        _marked(CONV_B),
        f"{_marked(CONV_A)}\n\n> Quoted: <!-- openhands-review-run: {CONV_B} -->",
    ],
    ids=["no-marker", "another-run", "two-markers"],
)
def test_reviews_this_run_cannot_claim_are_never_edited(
    reviewer, completion, monkeypatch, body
):
    github = _GitHub(body).install(reviewer, monkeypatch)

    _complete(reviewer, completion)

    # The review exists, so the run is complete and posts no duplicate result,
    # but nothing marks it as this conversation's, so its body is left alone.
    assert completion["status"] == "closed"
    assert github.writes == []
    assert github.reviews[0]["body"] == body


@pytest.mark.parametrize(
    "change",
    [{"state": "PENDING"}, {"user": {"login": "someone-else"}}, {"commit_id": "old"}],
)
def test_unrelated_reviews_are_not_relabelled(
    reviewer, completion, monkeypatch, change
):
    github = _GitHub(_marked(CONV_A)).install(reviewer, monkeypatch)
    github.reviews[0].update(change)

    _complete(reviewer, completion)

    assert completion["status"] == "closed"
    [(method, path, body)] = github.writes
    assert (method, path) == ("POST", "/repos/owner/repo/issues/42/comments")
    assert "Review text" in body["body"]
    assert body["body"].endswith(FOOTER_A)


def test_overlapping_runs_on_one_head_each_annotate_only_their_own_review(
    reviewer, monkeypatch
):
    """Two automations share a bot account and both review the same head."""
    github = _GitHub(_marked(CONV_A), _marked(CONV_B)).install(reviewer, monkeypatch)
    run_a = _record(CONV_A, "review-sonnet", "anthropic/claude-sonnet-4-5")
    run_b = _record(CONV_B, "review-gpt", "openai/gpt-5.5")

    _complete(reviewer, run_a)
    _complete(reviewer, run_b)
    # A collector that runs again finds its review already correct; the later,
    # latest review by the same bot (B's) is still not its to rewrite.
    _complete(reviewer, _record(CONV_A, "review-sonnet", "anthropic/claude-sonnet-4-5"))

    assert [(method, path) for method, path, _ in github.writes] == [
        ("PUT", "/repos/owner/repo/pulls/42/reviews/101"),
        ("PUT", "/repos/owner/repo/pulls/42/reviews/102"),
    ]
    assert github.reviews[0]["body"] == (
        f"{_marked(CONV_A)}\n\n"
        "LLM profile: `review-sonnet` · Model: `anthropic/claude-sonnet-4-5`"
    )
    assert github.reviews[1]["body"] == (
        f"{_marked(CONV_B)}\n\nLLM profile: `review-gpt` · Model: `openai/gpt-5.5`"
    )


def test_legacy_prompt_names_its_conversation_and_leaves_the_footer_to_the_script(
    reviewer, monkeypatch, tmp_path
):
    created = {}

    def create(_url, _key, prompt, _workspace, agent=None, conversation_id=None):
        created.update(prompt=prompt, conversation_id=conversation_id, agent=agent)
        return conversation_id

    monkeypatch.setattr(reviewer, "_prepare_repository", lambda *_: tmp_path)
    monkeypatch.setattr(
        reviewer,
        "_get_agent_and_llm_provenance",
        lambda *_: ({"kind": "Agent"}, "selected-profile", "openai/selected"),
    )
    monkeypatch.setattr(reviewer, "create_conversation", create)
    monkeypatch.setattr(reviewer, "_post_github_comment", lambda *_: True)
    reviews = {}

    conversation_id = reviewer._process_review_request(
        "token",
        "http://agent",
        "key",
        "http://canvas",
        "owner/repo",
        {"number": 42, "head": {"sha": "head"}},
        {"id": 7, "created_at": "2026-09-10T10:00:00Z"},
        reviews,
        lambda: None,
    )

    assert conversation_id == created["conversation_id"]
    assert f"<!-- openhands-review-run: {conversation_id} -->" in created["prompt"]
    assert "do not write that footer yourself" in created["prompt"]
    assert "LLM profile:" not in created["prompt"]
    [record] = reviews.values()
    assert record["conversation_id"] == conversation_id
    assert (record["llm_profile"], record["llm_model"]) == (
        "selected-profile",
        "openai/selected",
    )


# --- Catalog reviewer (worker.py): provenance from the conversation that ran

PROFILE_ID = "11111111-1111-4111-8111-111111111111"


class _AgentServer:
    """The Agent Server routes the dispatcher reads provenance from."""

    def __init__(self):
        self.conversations = {}
        self.profiles = [
            {
                "id": PROFILE_ID,
                "name": "Code reviewer",
                "revision": 3,
                "llm_profile_ref": "review-sonnet",
            }
        ]
        self.paths = []

    def add(self, conversation_id, model, revision=3):
        self.conversations[str(conversation_id)] = {
            "id": str(conversation_id),
            "agent": {"kind": "Agent", "llm": {"model": model, "api_key": "**********"}},
            "launched_agent_profile": {
                "agent_profile_id": PROFILE_ID,
                "revision": revision,
            },
        }

    def __enter__(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                server.paths.append(self.path)
                if self.headers.get("X-Session-API-Key") != "session":
                    self.send_error(401)
                    return
                if self.path == "/api/agent-profiles":
                    body = {"profiles": server.profiles}
                elif self.path.startswith("/api/conversations/"):
                    body = server.conversations.get(self.path.rsplit("/", 1)[1])
                else:
                    body = None
                if body is None:
                    self.send_error(404)
                    return
                content = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

        self._http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._http.serve_forever, daemon=True)
        self._thread.start()
        self.url = f"http://127.0.0.1:{self._http.server_port}"
        return self

    def __exit__(self, *_exc):
        self._http.shutdown()
        self._thread.join()
        self._http.server_close()


@pytest.fixture
def shipped(tmp_path, monkeypatch):
    """The catalog bundle's worker, with the SDK and KV boundaries faked."""
    from unittest.mock import MagicMock

    from github_automation_helpers import worker

    module = worker("github-pr-reviewer", tmp_path, monkeypatch)
    dispatch = sys.modules["agent_conversation"]
    kv = {}

    def kv_request(key, method, value=None):
        if method == "GET":
            return kv.get(key)
        kv[key] = value
        return {"key": key, "value": value}

    monkeypatch.setattr(dispatch, "_kv_request", kv_request)
    monkeypatch.setattr(dispatch, "_register_tools", lambda: None)
    workspace = MagicMock()
    workspace.__enter__.return_value = workspace
    workspace.get_secrets.return_value = {}
    monkeypatch.setattr(dispatch, "RemoteWorkspace", lambda **_kwargs: workspace)
    sent = {}
    live = {}

    def attach(_workspace, conversation_id, visualizer=None):
        if str(conversation_id) not in live:
            raise dispatch.httpx.HTTPStatusError(
                "missing", request=MagicMock(), response=MagicMock(status_code=404)
            )
        conversation = MagicMock()
        conversation.state.execution_status = (
            dispatch.ConversationExecutionStatus.IDLE
        )
        conversation.send_message.side_effect = (
            lambda text: sent.setdefault(str(conversation_id), []).append(text)
        )
        return conversation

    def create(_workspace, request, visualizer=None):
        live[str(request.conversation_id)] = request
        sent.setdefault(str(request.conversation_id), []).append(
            request.initial_message.content[0].text
        )
        return MagicMock()

    monkeypatch.setattr(dispatch.RemoteConversation, "attach", attach)
    monkeypatch.setattr(dispatch.RemoteConversation, "create", create)
    monkeypatch.delenv("AUTOMATION_EVENT_PAYLOAD", raising=False)
    return types.SimpleNamespace(module=module, kv=kv, sent=sent, live=live)


def _dispatcher(shipped, monkeypatch, server, automation_id):
    monkeypatch.setenv("AGENT_SERVER_URL", server.url)
    monkeypatch.setenv("SESSION_API_KEY", "session")
    monkeypatch.setenv("AUTOMATION_AGENT_PROFILE_ID", PROFILE_ID)
    monkeypatch.setenv(
        "AUTOMATION_EVENT_PAYLOAD", json.dumps({"automation_id": automation_id})
    )
    dispatcher = sys.modules["agent_conversation"].AgentConversationDispatcher()
    monkeypatch.delenv("AUTOMATION_EVENT_PAYLOAD")
    return dispatcher


def _pr_reviewer(shipped, dispatcher, github):
    run = object.__new__(shipped.module.PullRequestReviewer)
    run.config = {"trigger_label": "openhands-review"}
    run.repository = "owner/repo"
    run.token = "token"
    run.token_name = "GITHUB_TOKEN"
    run.github_login = "all-hands-bot"
    run.dispatcher = dispatcher
    run.gh = github.gh
    run.gh_pages = github.gh_pages
    return run


class _Repository:
    """A pull request's reviews, shared by every automation using one bot."""

    def __init__(self, sha="head-2"):
        self.pr = {"number": 2, "head": {"sha": sha}, "labels": []}
        self.reviews = []
        self.writes = []

    def publish(self, body, sha=None):
        review = {
            "id": 101 + len(self.reviews),
            "user": {"login": "all-hands-bot"},
            "commit_id": sha or self.pr["head"]["sha"],
            "state": "COMMENTED",
            "submitted_at": f"2026-09-10T10:0{len(self.reviews) + 1}:00Z",
            "body": body,
        }
        self.reviews.append(review)
        return review

    def gh(self, method, path, body=None):
        if (method, path) == ("GET", ""):
            return {"id": 99}
        if (method, path) == ("GET", "/pulls/2"):
            return self.pr
        self.writes.append((method, path, body))
        if method == "PUT":
            review_id = int(path.rsplit("/", 1)[1])
            next(r for r in self.reviews if r["id"] == review_id)["body"] = body["body"]
        return {}

    def gh_pages(self, path):
        assert path == "/pulls/2/reviews"
        return [dict(review) for review in self.reviews]


TRIGGER = {"id": 42, "created_at": "2026-09-10T10:00:00Z"}


def _review_text(prompt):
    """The review an agent following the prompt publishes."""
    marker = re.search(r"`(<!-- openhands-review-run: [^`]+ -->)`", prompt).group(1)
    return f"{DISCLOSURE}\n{marker}\n\nLooks correct.\n\n✅ APPROVED"


def test_shipped_worker_stamps_the_selected_profile_model_on_its_review(
    shipped, monkeypatch
):
    repository = _Repository()
    with _AgentServer() as server:
        with _dispatcher(shipped, monkeypatch, server, "automation-a") as dispatcher:
            run = _pr_reviewer(shipped, dispatcher, repository)
            result = run._start_review(99, repository.pr, TRIGGER, "head-2", None)
            conversation_id = result["conversation_id"]
            # The profile-backed conversation the server started runs the model
            # its selected agent profile resolves to.
            server.add(conversation_id, "anthropic/claude-sonnet-4-5")
            [prompt] = shipped.sent[conversation_id]
            review = repository.publish(_review_text(prompt))

            completed = run._finish_completed_review(repository.pr, TRIGGER)

    assert result["disposition"] == "created"
    assert f"<!-- openhands-review-run: {conversation_id} -->" in prompt
    assert "LLM profile:" not in prompt
    assert completed is True
    assert repository.writes == [
        (
            "PUT",
            f"/pulls/2/reviews/{review['id']}",
            {
                "body": _review_text(prompt)
                + "\n\nLLM profile: `review-sonnet` · Model: `anthropic/claude-sonnet-4-5`"
            },
        )
    ]
    # Provenance came from the conversation and its launching agent profile,
    # never from the scanner's own default settings.
    assert "/api/settings" not in server.paths
    assert server.paths == [
        f"/api/conversations/{conversation_id}",
        "/api/agent-profiles",
    ]


def test_shipped_worker_reports_a_reused_conversation_s_own_llm(shipped, monkeypatch):
    repository = _Repository()
    with _AgentServer() as server:
        with _dispatcher(shipped, monkeypatch, server, "automation-a") as dispatcher:
            run = _pr_reviewer(shipped, dispatcher, repository)
            first = run._start_review(99, repository.pr, TRIGGER, "head-2", None)
            conversation_id = first["conversation_id"]
            server.add(conversation_id, "anthropic/claude-sonnet-4-5")
            repository.publish(_review_text(shipped.sent[conversation_id][0]))
            # The agent profile is edited to another LLM profile, and the PR
            # moves to a new head that the same conversation reviews next.
            server.profiles[0].update(revision=4, llm_profile_ref="review-gpt")
            repository.pr["head"]["sha"] = "head-3"
            second = run._start_review(
                99, repository.pr, {"id": 43, "created_at": "2026-09-10T11:00:00Z"},
                "head-3", None,
            )
            prompt = shipped.sent[conversation_id][-1]
            review = repository.publish(_review_text(prompt))

            run._finish_completed_review(
                repository.pr, {"id": 43, "created_at": "2026-09-10T10:00:30Z"}
            )

    assert second == {"disposition": "resumed", "conversation_id": conversation_id}
    assert f"<!-- openhands-review-run: {conversation_id} -->" in prompt
    # The reused conversation still runs the model it was launched with. Its
    # launching profile has moved on, so the profile name is not guessed.
    [(_, path, body)] = repository.writes
    assert path == f"/pulls/2/reviews/{review['id']}"
    assert body["body"].endswith(
        "LLM profile: `unknown` · Model: `anthropic/claude-sonnet-4-5`"
    )


def test_two_automations_sharing_a_bot_each_annotate_only_their_own_review(
    shipped, monkeypatch
):
    """Overlapping runs, same bot, same head: neither rewrites the other's review."""
    repository = _Repository()
    with _AgentServer() as server:
        server.profiles.append(
            {"id": "22222222-2222-4222-8222-222222222222", "name": "GPT reviewer",
             "revision": 1, "llm_profile_ref": "review-gpt"}
        )
        with (
            _dispatcher(shipped, monkeypatch, server, "automation-a") as dispatcher_a,
            _dispatcher(shipped, monkeypatch, server, "automation-b") as dispatcher_b,
        ):
            run_a = _pr_reviewer(shipped, dispatcher_a, repository)
            run_b = _pr_reviewer(shipped, dispatcher_b, repository)
            conversation_a = run_a._start_review(
                99, repository.pr, TRIGGER, "head-2", None
            )["conversation_id"]
            conversation_b = run_b._start_review(
                99, repository.pr, TRIGGER, "head-2", None
            )["conversation_id"]
            server.add(conversation_a, "anthropic/claude-sonnet-4-5")
            server.add(conversation_b, "openai/gpt-5.5")
            server.conversations[conversation_b]["launched_agent_profile"] = {
                "agent_profile_id": "22222222-2222-4222-8222-222222222222",
                "revision": 1,
            }
            review_a = repository.publish(_review_text(shipped.sent[conversation_a][0]))
            review_b = repository.publish(_review_text(shipped.sent[conversation_b][0]))

            # B's review is the latest one by the bot on this head, which is
            # the review a login/head/time match would have rewritten.
            run_a._finish_completed_review(repository.pr, TRIGGER)
            run_b._finish_completed_review(repository.pr, TRIGGER)
            run_a._finish_completed_review(repository.pr, TRIGGER)

    assert conversation_a != conversation_b
    assert [path for _, path, _ in repository.writes] == [
        f"/pulls/2/reviews/{review_a['id']}",
        f"/pulls/2/reviews/{review_b['id']}",
    ]
    bodies = {review["id"]: review["body"] for review in repository.reviews}
    assert bodies[review_a["id"]].endswith(
        "LLM profile: `review-sonnet` · Model: `anthropic/claude-sonnet-4-5`"
    )
    assert bodies[review_b["id"]].endswith(
        "LLM profile: `review-gpt` · Model: `openai/gpt-5.5`"
    )
    assert "gpt" not in bodies[review_a["id"]]
    assert "claude" not in bodies[review_b["id"]]


def test_worker_reads_the_verdict_above_the_provenance_footer(shipped, monkeypatch):
    """A stamped approval still hands off: the footer follows the verdict."""
    repository = _Repository()
    repository.publish(
        f"{DISCLOSURE}\n\nLooks correct.\n\n✅ APPROVED\n\n"
        "LLM profile: `review-sonnet` · Model: `anthropic/claude-sonnet-4-5`"
    )
    run = _pr_reviewer(shipped, None, repository)
    run.config["maintainers"] = "alice,bob"
    handoffs = []
    monkeypatch.setattr(
        shipped.module,
        "request_maintainer_review",
        lambda _run, pr, maintainers: handoffs.append(maintainers) or "alice",
    )

    assert run._finish_completed_review(repository.pr, TRIGGER) is True
    assert handoffs == [["alice", "bob"]]
    assert repository.writes == []


def test_a_stamped_footer_is_kept_after_the_agent_profile_changes(
    shipped, monkeypatch
):
    """Provenance is recorded once; a later profile edit cannot rewrite it."""
    repository = _Repository()
    with _AgentServer() as server:
        with _dispatcher(shipped, monkeypatch, server, "automation-a") as dispatcher:
            run = _pr_reviewer(shipped, dispatcher, repository)
            conversation_id = run._start_review(
                99, repository.pr, TRIGGER, "head-2", None
            )["conversation_id"]
            server.add(conversation_id, "anthropic/claude-sonnet-4-5")
            repository.publish(_review_text(shipped.sent[conversation_id][0]))
            run._finish_completed_review(repository.pr, TRIGGER)
            stamped = repository.reviews[0]["body"]
            # The agent profile now points at another LLM profile, so a fresh
            # read would name the profile `unknown`.
            server.profiles[0].update(revision=4, llm_profile_ref="review-gpt")

            run._finish_completed_review(repository.pr, TRIGGER)

    assert stamped.endswith(
        "LLM profile: `review-sonnet` · Model: `anthropic/claude-sonnet-4-5`"
    )
    assert len(repository.writes) == 1
    assert repository.reviews[0]["body"] == stamped


def test_a_provenance_failure_never_blocks_the_verdict_or_handoff(
    shipped, monkeypatch, capsys
):
    repository = _Repository()
    repository.publish(
        f"{DISCLOSURE}\n<!-- openhands-review-run: {CONV_A} -->\n\n"
        "Looks correct.\n\n✅ APPROVED"
    )

    class Unavailable:
        def subject_conversation(self, subject):
            return CONV_A

        def llm_provenance(self, conversation_id):
            raise RuntimeError("agent server unavailable")

    run = _pr_reviewer(shipped, Unavailable(), repository)
    run.config["maintainers"] = "alice,bob"
    handoffs = []
    monkeypatch.setattr(
        shipped.module,
        "request_maintainer_review",
        lambda _run, pr, maintainers: handoffs.append(maintainers) or "alice",
    )

    assert run._finish_completed_review(repository.pr, TRIGGER) is True
    assert handoffs == [["alice", "bob"]]
    assert repository.writes == []
    logged = [
        json.loads(line)
        for line in capsys.readouterr().out.splitlines()
        if "llm_provenance_error" in line
    ]
    assert logged == [
        {
            "repository": "owner/repo",
            "pr": 2,
            "llm_provenance_error": "RuntimeError: agent server unavailable",
        }
    ]
