"""Factory worker snapshots and bounded continuation, without network access."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "skills/github-software-factory/scripts/main.py"


@pytest.fixture
def worker(monkeypatch, tmp_path):
    import json

    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WORKSPACE_BASE", str(tmp_path))
    monkeypatch.setenv("AUTOMATION_CONVERSATION_ID", "test-conversation")
    monkeypatch.setenv("AGENT_SERVER_URL", "http://localhost:8000")
    monkeypatch.setenv("SESSION_API_KEY", "only-inner-key")
    (tmp_path / "config.json").write_text(
        json.dumps({"role": "developer", "repository": "owner/private"})
    )
    spec = importlib.util.spec_from_file_location(
        "factory_worker", SCRIPT.with_name("main.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mock_server(monkeypatch, worker, request):
    from types import SimpleNamespace

    server = SimpleNamespace(
        get_conversation=lambda cid: request("conversation"),
        send_message=lambda cid, text: request(
            "conversation/events",
            "POST",
            {
                "content": [{"type": "text", "text": text}],
                "run": True,
            },
        ),
        get_errors=lambda cid, limit: request("conversation/events/search?"),
        interrupt=lambda cid: request("conversation/interrupt", "POST", {}),
    )
    monkeypatch.setattr(worker, "SERVER", server)


def snapshot(monkeypatch, worker, filename="README.md", symlink=False):
    import base64
    import io
    import tarfile

    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as tar:
        item = tarfile.TarInfo("github-prefix/" + filename)
        if symlink:
            item.type = tarfile.SYMTYPE
            item.linkname = "/etc/passwd"
        else:
            item.size = 5
        tar.addfile(item, None if symlink else io.BytesIO(b"hello"))
    sha = "a" * 40

    def gh(method, path, body=None):
        if path == "/git/ref/heads/main":
            return {"object": {"sha": sha}}
        assert path == "/factory/archive"
        assert body == {"sha": sha}
        return {"sha": sha, "tarball": base64.b64encode(out.getvalue()).decode()}

    monkeypatch.setattr(worker, "gh", gh)
    return sha


def test_private_checkout_has_exact_evidence_and_no_credential_remote(
    monkeypatch, worker
):
    import json

    sha = snapshot(monkeypatch, worker)
    remote_sha, local_sha = worker.clone(expected_sha=sha)
    assert remote_sha == sha
    assert local_sha
    assert (worker.PROJECT / "README.md").read_text() == "hello"
    assert worker.shell(["git", "remote", "-v"]) == ""
    assert json.loads((worker.EVIDENCE / "checkout.json").read_text())["sha"] == sha


def test_checkout_rejects_a_head_change(monkeypatch, worker):
    snapshot(monkeypatch, worker)
    with pytest.raises(RuntimeError, match="head changed"):
        worker.clone(expected_sha="b" * 40)
    assert not worker.PROJECT.exists()


@pytest.mark.parametrize("symlink", [False, True])
def test_snapshot_rejects_links_and_traversal(monkeypatch, worker, symlink):
    import tarfile

    snapshot(monkeypatch, worker, "../../escape", symlink=symlink)
    with pytest.raises((RuntimeError, tarfile.FilterError)):
        worker.clone()
    assert not (worker.WORKSPACE / "escape").exists()


@pytest.mark.parametrize(
    "code,expected", [("MaxIterationsReached", 2), ("LLMAuthenticationError", 1)]
)
def test_only_step_budget_errors_receive_bounded_continuation(
    monkeypatch, worker, code, expected
):
    states = iter(["error", "finished"])
    posts = []

    def request(url, method="GET", body=None, token=None):
        if method == "POST":
            posts.append(body)
            return {}
        if "/events/search?" in url:
            return {"items": [{"code": code}]}
        return {"execution_status": next(states)}

    mock_server(monkeypatch, worker, request)
    monkeypatch.setattr(worker.time, "sleep", lambda _: None)
    if code == "MaxIterationsReached":
        assert worker.agent("Implement issue")["execution_status"] == "finished"
    else:
        with pytest.raises(RuntimeError, match="error"):
            worker.agent("Implement issue")
    assert len(posts) == expected


def test_step_budget_continuations_have_a_hard_limit(monkeypatch, worker):
    posts = []

    def request(url, method="GET", body=None, token=None):
        if method == "POST":
            posts.append(body)
            return {}
        if "/events/search?" in url:
            return {"items": [{"code": "MaxIterationsReached"}]}
        return {"execution_status": "error"}

    mock_server(monkeypatch, worker, request)
    monkeypatch.setattr(worker.time, "sleep", lambda _: None)
    with pytest.raises(RuntimeError):
        worker.agent("Implement issue")
    assert len(posts) == 3


def test_incomplete_work_is_checkpointed_only_after_agent_stops(monkeypatch, worker):
    def agent(_):
        raise worker.AgentStopped("Agent stopped with error")

    comments = []
    monkeypatch.setattr(worker, "agent", agent)
    mock_server(monkeypatch, worker, lambda *args: {"execution_status": "error"})
    monkeypatch.setattr(worker, "comment", lambda *args: comments.append(args))
    worker.implement("Implement issue", 42)
    assert (worker.EVIDENCE / "checkpoint.json").exists()
    assert comments[0][0] == 42
    assert "independent review" in comments[0][1]


def test_timeout_interrupts_before_checkpoint_publication(monkeypatch, worker):
    def agent(_):
        raise TimeoutError("Step deadline")

    calls = []
    states = iter(["running", "paused"])

    def request(url, method="GET", body=None):
        calls.append((url, method))
        return {} if method == "POST" else {"execution_status": next(states)}

    monkeypatch.setattr(worker, "agent", agent)
    mock_server(monkeypatch, worker, request)
    monkeypatch.setattr(worker, "comment", lambda *args: None)
    worker.implement("Implement issue", 42)
    assert any(url.endswith("/interrupt") and method == "POST" for url, method in calls)
    assert (worker.EVIDENCE / "checkpoint.json").exists()


def test_developer_waits_for_review_findings_after_test_failure(monkeypatch, worker):
    monkeypatch.setattr(
        worker,
        "gh",
        lambda *args: [{"head": {"sha": "a" * 40, "ref": "factory/issue-1"}}],
    )
    monkeypatch.setattr(worker, "open_issues", lambda: [])
    monkeypatch.setattr(
        worker, "statuses", lambda sha: {"software-factory/tests": "failure"}
    )
    # Starting a revision here would try to read this PR's missing issue/body.
    worker.developer()


def test_pagination_preserves_existing_query(monkeypatch, worker):
    calls = []
    monkeypatch.setattr(worker, "gh", lambda method, path: calls.append(path) or [])
    assert worker.gh_pages("/pulls?state=open") == []
    assert calls == ["/pulls?state=open&per_page=100&page=1"]


@pytest.mark.parametrize(
    "name", ["/outside/credential", "../credential", "linked/credential"]
)
def test_publish_rejects_paths_outside_project(monkeypatch, worker, name):
    worker.PROJECT.mkdir()
    (worker.WORKSPACE / "credential").write_text("private-canary")
    (worker.PROJECT / "linked").symlink_to(worker.WORKSPACE, target_is_directory=True)
    monkeypatch.setattr(worker, "shell", lambda args: name if "diff" in args else "")
    calls = []
    monkeypatch.setattr(worker, "gh", lambda *args: calls.append(args))
    with pytest.raises(RuntimeError, match="outside the project"):
        worker.publish({"number": 1}, "base", "branch", None, "local-base")
    assert not calls


def test_developer_skips_closed_source_issue(monkeypatch, worker):
    monkeypatch.setattr(worker, "open_issues", lambda: [])
    monkeypatch.setattr(
        worker, "statuses", lambda sha: {"software-factory/review": "failure"}
    )
    monkeypatch.setattr(
        worker,
        "gh",
        lambda *args: [
            {
                "number": 7,
                "head": {"sha": "a" * 40, "ref": "factory/issue-1"},
                "body": "Closes #1",
            }
        ],
    )
    worker.developer()


@pytest.mark.parametrize(
    "state,reason,ready",
    [
        ("open", None, False),
        ("closed", "not_planned", False),
        ("closed", "completed", True),
    ],
)
def test_dependencies_require_completed_issues(
    worker, monkeypatch, state, reason, ready
):
    def gh(method, path, body=None):
        assert (method, path) == ("GET", "/issues/1")
        return {"state": state, "state_reason": reason}

    monkeypatch.setattr(worker, "gh", gh)
    assert (
        worker.dependencies_complete({"body": "Small feature\nDepends on: #1\n"})
        is ready
    )


def test_developer_lanes_do_not_block_on_other_lane_pr(worker, monkeypatch):
    worker.CONFIG.update(developer_lane=0, developer_lanes=2)
    issues = [
        {
            "number": 1,
            "title": "API",
            "body": "",
            "labels": [{"name": "ready-for-dev"}],
        },
        {"number": 2, "title": "UI", "body": "", "labels": [{"name": "ready-for-dev"}]},
    ]
    monkeypatch.setattr(worker, "open_issues", lambda: issues)

    def gh(method, path, body=None):
        if path.startswith("/pulls?"):
            return [{"number": 9, "head": {"ref": "factory/issue-1", "sha": "a" * 40}}]
        assert path == "/factory/bootstrap"
        raise LookupError("selected own lane")

    monkeypatch.setattr(worker, "gh", gh)
    with pytest.raises(LookupError, match="selected own lane"):
        worker.developer()


def test_developer_lane_never_takes_another_lanes_issue(worker, monkeypatch):
    worker.CONFIG.update(developer_lane=0, developer_lanes=2)
    monkeypatch.setattr(
        worker,
        "open_issues",
        lambda: [{"number": 1, "labels": [{"name": "ready-for-dev"}]}],
    )

    def gh(method, path, body=None):
        assert path.startswith("/pulls?")
        return []

    monkeypatch.setattr(worker, "gh", gh)
    worker.developer()


def test_accepted_stale_pr_uses_native_branch_update(worker, monkeypatch):
    issue = {"number": 2, "labels": [{"name": "ready-for-dev"}]}
    monkeypatch.setattr(worker, "open_issues", lambda: [issue])
    monkeypatch.setattr(
        worker, "statuses", lambda sha: {"software-factory/review": "success"}
    )
    calls = []

    def gh(method, path, body=None):
        calls.append((method, path, body))
        if path.startswith("/pulls?"):
            return [{"number": 3, "head": {"sha": "a" * 40, "ref": "factory/issue-2"}}]
        if path == "/git/ref/heads/main":
            return {"object": {"sha": "b" * 40}}
        if path.startswith("/compare/"):
            return {"status": "diverged"}
        assert path == "/factory/update-branch"
        return {"message": "Updating branch"}

    monkeypatch.setattr(worker, "gh", gh)
    worker.developer()
    assert calls[-1] == (
        "POST",
        "/factory/update-branch",
        {"number": 3, "sha": "a" * 40},
    )
