"""Contract tests for independent watchdog delivery."""

import json
import subprocess
import sys
from urllib.error import HTTPError

import pytest
from github_automation_helpers import ROOT, worker
from openhands.sdk.skills import install_skill


def test_installed_watchdog_skill_imports_worker(tmp_path):
    name = "github-delivery-watchdog"
    install_skill(source=str(ROOT / "skills" / name), installed_dir=tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", "import worker"],
        cwd=tmp_path / name / "scripts",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "changes",
    [
        {"head": {"sha": "b" * 40, "ref": "openhands/issue-1"}},
        {"draft": True},
        {"mergeable": None},
        {"state": "closed"},
        {"base": {"sha": "c" * 40, "ref": "release"}},
    ],
)
def test_watchdog_rejects_ineligible_pr_before_merge(tmp_path, monkeypatch, changes):
    cls = worker("github-delivery-watchdog", tmp_path, monkeypatch).DeliveryWatchdog
    run = object.__new__(cls)
    run.config = {"base_branch": "main"}
    pr = {
        "state": "open",
        "draft": False,
        "mergeable": True,
        "head": {"sha": "a" * 40, "ref": "openhands/issue-1"},
        "base": {"ref": "main", "sha": "c" * 40},
        **changes,
    }
    calls = []
    run.gh = lambda *args: calls.append(args) or pr
    assert run.merge(1, "a" * 40) is None
    assert calls == [("GET", "/pulls/1")]


@pytest.mark.parametrize("base_branch", ["main", "release"])
@pytest.mark.parametrize(
    "review,ci,comparison,merged",
    [
        ("success", True, "ahead", True),
        ("failure", True, "ahead", False),
        ("success", False, "ahead", False),
        ("success", True, "behind", False),
    ],
)
def test_watchdog_requires_exact_acceptance_ci_and_current_base(
    tmp_path, monkeypatch, review, ci, comparison, merged, base_branch
):
    cls = worker("github-delivery-watchdog", tmp_path, monkeypatch).DeliveryWatchdog
    run = object.__new__(cls)
    run.config = {}
    sha = "a" * 40
    calls = []

    def gh(method, path, body=None):
        calls.append((method, path, body))
        if path == "":
            return {"default_branch": base_branch}
        if path == "/pulls/1":
            return {
                "state": "open",
                "draft": False,
                "mergeable": True,
                "head": {"sha": sha, "ref": "openhands/issue-1"},
                "base": {"ref": base_branch, "sha": "c" * 40},
            }
        if "/compare/" in path:
            return {"status": comparison}
        return {"merged": True}

    run.gh = gh
    run.statuses = lambda sha: {
        "software-factory/tests": "success",
        "software-factory/review": review,
    }
    run.ci_passed = lambda sha: ci
    assert bool(run.merge(1, sha)) is merged
    if merged:
        assert calls[-1] == (
            "PUT",
            "/pulls/1/merge",
            {"sha": sha, "merge_method": "squash"},
        )
    else:
        assert not any(c[0] == "PUT" for c in calls)


@pytest.mark.parametrize(
    "error",
    [
        HTTPError("https://api.github.com", 409, "Conflict", {}, None),
        TimeoutError("GitHub unavailable"),
        json.JSONDecodeError("Invalid response", "", 0),
        KeyError("head"),
    ],
)
def test_watchdog_continues_after_a_pr_api_failure(tmp_path, monkeypatch, error):
    module = worker("github-delivery-watchdog", tmp_path, monkeypatch)
    run = object.__new__(module.DeliveryWatchdog)
    run.gh_pages = lambda path: [
        {"number": 1, "head": {"sha": "a"}},
        {"number": 2, "head": {"sha": "b"}},
    ]
    visited = []

    def merge(number, sha):
        visited.append(number)
        if number == 1:
            raise error
        return {"merged": True}

    run.merge = merge
    run.run()
    assert visited == [1, 2]


@pytest.mark.parametrize("required,expected", [([], True), ([123], False)])
def test_actions_are_optional_but_configured_workflows_are_required(
    tmp_path, monkeypatch, required, expected
):
    module = worker("github-delivery-watchdog", tmp_path, monkeypatch)
    run = object.__new__(module.DeliveryWatchdog)
    run.config = {"required_workflow_ids": required}
    run.gh = lambda *args: {"workflow_runs": [], "total_count": 0}
    assert run.ci_passed("a" * 40) is expected


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({}, True),
        ({"conclusion": "failure"}, False),
        ({"status": "in_progress"}, False),
        ({"workflow_id": 2}, False),
        ({"event": "push"}, False),
        ({"head_branch": "other-branch"}, False),
        ({"head_sha": "other-commit"}, False),
    ],
)
def test_new_actions_execution_supersedes_only_its_own_trigger(
    tmp_path, monkeypatch, changes, expected
):
    module = worker("github-delivery-watchdog", tmp_path, monkeypatch)
    run = object.__new__(module.DeliveryWatchdog)
    run.config = {"required_workflow_ids": [1]}
    old = {
        "id": 10,
        "run_number": 1,
        "workflow_id": 1,
        "head_sha": "sha",
        "event": "pull_request",
        "head_branch": "feature",
        "status": "completed",
        "conclusion": "failure",
    }
    new = {**old, "id": 11, "run_number": 2, "conclusion": "success", **changes}
    # Deliberately unsorted: correctness must not depend on API response order.
    run.gh = lambda *args: {"workflow_runs": [old, new], "total_count": 2}
    assert run.ci_passed("sha") is expected


def test_native_actions_rerun_keeps_its_run_identity(tmp_path, monkeypatch):
    module = worker("github-delivery-watchdog", tmp_path, monkeypatch)
    run = object.__new__(module.DeliveryWatchdog)
    run.config = {"required_workflow_ids": [1]}
    result = {
        "id": 10,
        "run_number": 1,
        "run_attempt": 2,
        "workflow_id": 1,
        "head_sha": "sha",
        "event": "pull_request",
        "head_branch": "feature",
        "status": "completed",
        "conclusion": "success",
    }
    run.gh = lambda *args: {"workflow_runs": [result], "total_count": 1}
    assert run.ci_passed("sha")
