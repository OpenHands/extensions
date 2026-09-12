"""Factory authorization and merge gates, without credentials or network access."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "skills/github-software-factory/scripts/broker.py"


@pytest.fixture
def broker():
    spec = importlib.util.spec_from_file_location("factory_broker", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("role", ["triage", "developer", "reviewer", "watchdog"])
def test_no_role_can_write_main_or_administer_repository(broker, role):
    for method, path, body in [
        ("PATCH", "/git/refs/heads/main", {"sha": "a" * 40}),
        ("POST", "/git/refs", {"ref": "refs/heads/main", "sha": "a" * 40}),
        ("PUT", "/contents/application.js", {"content": "AAAA"}),
        ("DELETE", "", {}),
        ("PUT", "/pulls/1/merge", {"sha": "a" * 40}),
        ("PATCH", "/issues/1", {"state": "closed"}),
    ]:
        assert not broker.permitted(role, method, path, body)


def test_writer_cannot_accept_and_reviewer_cannot_publish(broker):
    assert broker.permitted(
        "developer", "POST", "/git/refs", {"ref": "refs/heads/factory/issue-1"}
    )
    assert not broker.permitted(
        "developer",
        "POST",
        "/statuses/" + "a" * 40,
        {"context": "software-factory/review"},
    )
    assert not broker.permitted("reviewer", "POST", "/git/blobs", {})
    assert not broker.permitted(
        "reviewer",
        "POST",
        "/pulls/1/reviews",
        {"event": "APPROVE", "commit_id": "a" * 40},
    )
    assert not broker.permitted(
        "developer", "PATCH", "/git/refs/heads/factory/issue-1", {"force": True}
    )
    assert broker.permitted(
        "reviewer",
        "POST",
        "/statuses/" + "a" * 40,
        {"context": "software-factory/tests"},
    )


def install_merge_fixture(monkeypatch, broker):
    sha = "a" * 40
    pr = {
        "number": 1,
        "state": "open",
        "draft": False,
        "mergeable": True,
        "head": {"sha": sha, "ref": "factory/issue-1"},
        "base": {"sha": "b" * 40, "ref": "main"},
    }
    data = {
        "pr": pr,
        "statuses": [
            {"context": "software-factory/tests", "state": "success"},
            {"context": "software-factory/review", "state": "success"},
        ],
        "checks": {"total_count": 0, "check_runs": []},
        "comparison": {"status": "ahead"},
    }
    writes = []

    def github(method, path, body=None):
        if method == "PUT":
            writes.append((path, body))
            return {"merged": True}
        if path == "/pulls/1":
            return data["pr"]
        if "/statuses?" in path:
            return data["statuses"]
        if "/check-runs?" in path:
            return data["checks"]
        if path.startswith("/compare/"):
            return data["comparison"]
        raise AssertionError(path)

    monkeypatch.setattr(broker, "github", github)
    return sha, data, writes


def test_merge_requires_exact_reviewed_head(monkeypatch, broker):
    sha, data, writes = install_merge_fixture(monkeypatch, broker)
    assert broker.merge(1, sha)["merged"]
    assert writes == [("/pulls/1/merge", {"sha": sha, "merge_method": "squash"})]


@pytest.mark.parametrize(
    "failure",
    [
        "new_head",
        "missing_review",
        "new_failure",
        "pending_ci",
        "stale_base",
        "incomplete_checks",
        "draft",
        "conflict",
    ],
)
def test_merge_fails_closed(monkeypatch, broker, failure):
    sha, data, writes = install_merge_fixture(monkeypatch, broker)
    if failure == "new_head":
        data["pr"]["head"]["sha"] = "c" * 40
    elif failure == "missing_review":
        data["statuses"].pop()
    elif failure == "new_failure":
        data["statuses"].insert(
            0, {"context": "software-factory/tests", "state": "failure"}
        )
    elif failure == "pending_ci":
        data["checks"] = {"total_count": 1, "check_runs": [{"conclusion": None}]}
    elif failure == "stale_base":
        data["comparison"]["status"] = "diverged"
    elif failure == "incomplete_checks":
        data["checks"]["total_count"] = 101
    elif failure == "draft":
        data["pr"]["draft"] = True
    elif failure == "conflict":
        data["pr"]["mergeable"] = False
    with pytest.raises(ValueError):
        broker.merge(1, sha)
    assert not writes


@pytest.fixture
def worker(monkeypatch, tmp_path):
    import json

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
