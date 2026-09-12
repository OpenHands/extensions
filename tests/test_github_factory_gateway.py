"""Factory authorization and merge gates, without credentials or network access."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).parents[1]
    / "skills/openhands-automation/scripts/github_factory_gateway.py"
)


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
    assert broker.permitted("reviewer", "GET", "/pulls/7/files", {})
    assert broker.permitted("developer", "GET", "/pulls/7/files", {})
    assert not broker.permitted("triage", "GET", "/pulls/7/files", {})
    assert not broker.permitted("watchdog", "GET", "/pulls/7/files", {})
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


def test_merge_rejects_invalid_identity_before_network(broker, monkeypatch):
    def unexpected(*args):
        raise AssertionError("Invalid identity reached GitHub")

    monkeypatch.setattr(broker, "github", unexpected)
    for number, sha in [(0, "a" * 40), (1, "../other-repo"), (1, "main")]:
        with pytest.raises(ValueError):
            broker.merge(number, sha)


def test_reads_are_limited_to_role_inputs(broker):
    assert broker.permitted("triage", "GET", "/issues?state=open", {})
    assert not broker.permitted("triage", "GET", "/git/ref/heads/main", {})
    assert not broker.permitted("triage", "GET", "/pulls", {})
    assert broker.permitted("watchdog", "GET", "/commits/" + "a" * 40 + "/statuses", {})
    assert not broker.permitted("watchdog", "GET", "/git/blobs/" + "a" * 40, {})
    assert not broker.permitted("watchdog", "GET", "/issues", {})
    assert broker.permitted("reviewer", "GET", "/git/ref/heads/factory/issue-1", {})
    assert not broker.permitted("reviewer", "GET", "/git/ref/heads/private-work", {})


def test_watchdog_cannot_post_comments(broker):
    for role in ("triage", "developer", "reviewer"):
        assert broker.permitted(role, "POST", "/issues/1/comments", {"body": "report"})
    assert not broker.permitted(
        "watchdog", "POST", "/issues/1/comments", {"body": "report"}
    )
