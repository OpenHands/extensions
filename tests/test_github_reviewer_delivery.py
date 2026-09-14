"""Contract tests for independent reviewer delivery."""

import pytest
from github_automation_helpers import worker


@pytest.mark.parametrize(
    "body,stage,expected",
    [
        ("✅ APPROVED", "review", True),
        ("🔄 CHANGES REQUESTED", "review", False),
        ("## QA Report: PASS", "qa", True),
        ("## ✅ QA Report: **PASS**", "qa", True),
        ("## ⚠️ QA Report: PASS WITH ISSUES", "qa", False),
        ("## QA Report: PARTIAL", "qa", False),
        ("PASS", "qa", False),
    ],
)
def test_reviewer_acceptance_uses_published_readable_verdict(
    tmp_path, monkeypatch, body, stage, expected
):
    cls = worker("github-pr-reviewer", tmp_path, monkeypatch).PullRequestReviewer
    assert cls.report_passed({"body": body}, stage) is expected


def test_reviewer_rejects_new_source_but_allows_ignored_build_output(
    tmp_path, monkeypatch
):
    module = worker("github-pr-reviewer", tmp_path, monkeypatch)
    run = object.__new__(module.PullRequestReviewer)
    run.project = tmp_path / "checkout"
    run.project.mkdir()
    run.token = "not-a-real-token"
    (run.project / ".gitignore").write_text("dist/\n")
    (run.project / "app.py").write_text("original")
    run.shell(["git", "init", "--quiet"])
    run.shell(["git", "add", "--force", "."])
    run.source_tree = run.shell(["git", "write-tree"])
    (run.project / "dist").mkdir()
    (run.project / "dist" / "app.js").write_text("generated")
    assert run.tracked_files_unchanged()
    extra = run.project / "test_helper.py"
    extra.write_text("unreviewed")
    assert not run.tracked_files_unchanged()
    extra.unlink()
    (run.project / "app.py").write_text("changed")
    assert not run.tracked_files_unchanged()
    (run.project / "app.py").write_text("original")
    (run.project / "app.py").chmod(0o755)
    assert not run.tracked_files_unchanged()


def test_test_status_failure_still_preserves_acceptance_evidence(tmp_path, monkeypatch):
    import json

    module = worker("github-pr-reviewer", tmp_path, monkeypatch)
    run = object.__new__(module.PullRequestReviewer)
    run.project = tmp_path / "checkout"
    run.project.mkdir()
    (run.project / "app.py").write_text("original")
    run.evidence = tmp_path / "evidence"
    run.evidence.mkdir()
    run.token, run.repository, run.conversation_id = "dummy", "owner/repo", "run"
    run.config = {"test_commands": [["test"]], "branch_prefix": "openhands/issue"}
    pr = {
        "number": 1,
        "head": {"sha": "a" * 40, "ref": "openhands/issue-1"},
        "body": "",
    }
    run.gh_pages = lambda path: [pr]
    run.gh = lambda *args: pr
    run.statuses = lambda sha: {}
    run.comment = lambda *args: None
    run.independent_tests = lambda: ([{"passed": True}], True)

    def unavailable(*args):
        raise TimeoutError("GitHub unavailable")

    run.status = unavailable
    monkeypatch.setattr(
        module.workflow, "_prepare_repository", lambda *args: run.project
    )
    with pytest.raises(TimeoutError, match="unavailable"):
        run.run()
    evidence = json.loads((run.evidence / "acceptance.json").read_text())
    assert evidence["tests"] == [{"passed": True}]
    assert evidence["failure"] == "TimeoutError"
    assert evidence["accepted"] is False


@pytest.mark.parametrize(
    "second_verdict,expected_id", [("✅ APPROVED", 1), ("🔄 CHANGES REQUESTED", 2)]
)
def test_split_summary_and_inline_reviews_must_agree(
    tmp_path, monkeypatch, second_verdict, expected_id
):
    module = worker("github-pr-reviewer", tmp_path, monkeypatch)
    run = object.__new__(module.PullRequestReviewer)
    run.conversation_id = "run"
    marker = "<!-- factory-run:run:review -->"
    run.gh_pages = lambda path: [
        {
            "id": 1,
            "commit_id": "sha",
            "state": "COMMENTED",
            "body": marker
            + "\nDetailed review with findings and validation.\n✅ APPROVED",
        },
        {
            "id": 2,
            "commit_id": "sha",
            "state": "COMMENTED",
            "body": marker + "\n" + second_verdict,
        },
    ]
    assert run.posted_report(set(), "sha", "review", 1)["id"] == expected_id


def test_pending_reviews_follow_github_update_order(tmp_path, monkeypatch):
    module = worker("github-pr-reviewer", tmp_path, monkeypatch)
    run = object.__new__(module.PullRequestReviewer)
    run.config = {}
    older = {
        "number": 9,
        "head": {"sha": "old"},
        "labels": [{"name": "openhands-review"}],
    }
    newer = {
        "number": 1,
        "head": {"sha": "new"},
        "labels": [{"name": "openhands-review"}],
    }

    def pages(path):
        assert "sort=updated&direction=asc" in path
        return [older, newer]

    run.gh_pages = pages
    run.statuses = lambda sha: {}

    def selected(method, path):
        assert path == "/pulls/9"
        raise TimeoutError("Selected oldest pending review")

    run.gh = selected
    with pytest.raises(TimeoutError, match="Selected oldest pending review"):
        run.run()


@pytest.mark.parametrize("initial_state", ["PENDING", "COMMENTED"])
def test_submitting_a_pending_review_counts_as_new_publication(
    tmp_path, monkeypatch, initial_state
):
    from unittest.mock import Mock

    module = worker("github-pr-reviewer", tmp_path, monkeypatch)
    run = object.__new__(module.PullRequestReviewer)
    run.project = run.evidence = tmp_path
    run.token, run.repository, run.conversation_id = "dummy", "owner/repo", "run"
    run.config = {}
    pr = {
        "number": 1,
        "head": {"sha": "sha"},
        "body": "Example:\n```\nCloses #999\n```",
        "labels": [{"name": "openhands-review"}],
    }
    review = {
        "id": 10,
        "state": initial_state,
        "commit_id": "sha",
        "html_url": "review-url",
    }
    run.gh_pages = lambda path: [pr] if path.startswith("/pulls?") else [dict(review)]
    run.gh = Mock(return_value=pr)
    run.statuses = lambda sha: {}
    run.status, run.comment = Mock(), Mock()
    run.shell = lambda *args: ""
    run.tracked_files_unchanged = lambda: True
    run.review_prompt = lambda pr: "Review this PR"
    run.conversation = Mock()
    run.conversation.run.side_effect = lambda **kwargs: review.update(
        state="COMMENTED", body="<!-- factory-run:run:review -->\n✅ APPROVED"
    )
    monkeypatch.setattr(module.workflow, "_prepare_repository", lambda *args: tmp_path)
    if initial_state == "PENDING":
        run.run()
        assert run.status.call_args.args[:3] == ("sha", "review", True)
    else:
        with pytest.raises(RuntimeError, match="newly published"):
            run.run()
        run.status.assert_not_called()
    assert not any(
        call.args[0] == "GET" and call.args[1].startswith("/issues/")
        for call in run.gh.call_args_list
    )


@pytest.mark.parametrize(
    "commands",
    [
        'npm ci\n\npython -m pytest "tests/unit suite"',
        [["npm", "ci"], ["python", "-m", "pytest", "tests/unit suite"]],
    ],
)
def test_independent_commands_from_setup_form(tmp_path, monkeypatch, commands):
    module = worker("github-pr-reviewer", tmp_path, monkeypatch)
    run = object.__new__(module.PullRequestReviewer)
    run.config = {"test_commands": commands}
    run.token = "synthetic-review-token"
    run.evidence = tmp_path
    calls = []
    run.shell = lambda command, **kwargs: calls.append(command) or "passed"
    run.tracked_files_unchanged = lambda: True
    results, passed = run.independent_tests()
    assert passed
    assert calls == [["npm", "ci"], ["python", "-m", "pytest", "tests/unit suite"]]
    assert len(results) == 2


@pytest.mark.parametrize("exit_code", [0, 1])
def test_independent_test_evidence_redacts_token_on_success_and_failure(
    tmp_path, monkeypatch, exit_code
):
    import json
    import sys

    module = worker("github-pr-reviewer", tmp_path, monkeypatch)
    run = object.__new__(module.PullRequestReviewer)
    run.project = tmp_path / "checkout"
    run.project.mkdir()
    run.evidence = tmp_path / "evidence"
    run.evidence.mkdir()
    run.token = "synthetic-review-token"
    monkeypatch.setenv("REVIEW_FIXTURE_SECRET", run.token)
    run.config = {
        "test_commands": [
            [
                sys.executable,
                "-c",
                (
                    "import os; print(os.environ['REVIEW_FIXTURE_SECRET']); "
                    f"raise SystemExit({exit_code})"
                ),
            ]
        ]
    }
    run.tracked_files_unchanged = lambda: True

    results, passed = run.independent_tests()

    assert passed is (exit_code == 0)
    assert "[REDACTED]" in results[0]["output"]
    assert run.token not in json.dumps(results)
    saved = (run.evidence / "tests.json").read_text()
    assert json.loads(saved) == results
    assert run.token not in saved
