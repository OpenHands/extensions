"""Contract tests for independent developer delivery."""

from unittest.mock import Mock

from github_automation_helpers import worker


def _developer(tmp_path, monkeypatch):
    module = worker("github-issue-to-pr", tmp_path, monkeypatch)
    run = object.__new__(module.IssueToPR)
    run.config = {
        "trigger_label": "ready-for-dev",
        "branch_prefix": "openhands/issue",
        "review_label": "openhands-review",
    }
    run.repository = "owner/repo"
    run.token_name = "FACTORY_GITHUB_DEVELOPER_TOKEN"
    run.dependencies_complete = lambda issue: True
    run.statuses = lambda sha: {}
    return module, run


def test_developer_fans_out_ready_issues_by_priority(tmp_path, monkeypatch):
    module, run = _developer(tmp_path, monkeypatch)
    issues = [
        {
            "number": 2,
            "title": "Normal",
            "updated_at": "u2",
            "labels": [{"name": "ready-for-dev"}],
        },
        {
            "number": 1,
            "title": "High",
            "updated_at": "u1",
            "labels": [{"name": "ready-for-dev"}, {"name": "priority:high"}],
        },
    ]
    run.open_issues = lambda: issues
    run.gh_pages = lambda path: []
    run.gh = Mock(
        side_effect=[{"id": 55, "default_branch": "main"}, {"object": {"sha": "base"}}]
    )
    submit = Mock(
        side_effect=lambda **kwargs: {
            "disposition": "created",
            "conversation_id": kwargs["subject_key"],
        }
    )
    monkeypatch.setattr(module, "submit_subject_turn", submit)

    run.run()

    assert [call.kwargs["subject_key"] for call in submit.call_args_list] == [
        "55:issue:1",
        "55:issue:2",
    ]
    prompt = submit.call_args_list[0].kwargs["turn"]
    assert "workspace starts empty" in prompt
    assert "FACTORY_GITHUB_DEVELOPER_TOKEN" in prompt
    assert "gh repo clone owner/repo ." in prompt


def test_developer_submits_failed_review_as_same_subject(tmp_path, monkeypatch):
    module, run = _developer(tmp_path, monkeypatch)
    issue = {"number": 4, "title": "Feature", "updated_at": "u4", "labels": []}
    pr = {
        "number": 8,
        "head": {"ref": "openhands/issue-4", "sha": "head"},
        "base": {"ref": "main"},
        "labels": [],
    }
    run.open_issues = lambda: [issue]
    run.gh_pages = lambda path: [pr]
    run.statuses = lambda sha: {"software-factory/review": "failure"}
    run.gh = Mock(
        side_effect=[{"id": 55, "default_branch": "main"}, {"object": {"sha": "base"}}]
    )
    submit = Mock(
        return_value={"disposition": "created", "conversation_id": "conversation"}
    )
    monkeypatch.setattr(module, "submit_subject_turn", submit)

    run.run()

    assert submit.call_args.kwargs["subject_key"] == "55:issue:4"
    assert submit.call_args.kwargs["idempotency_key"] == "4:head"
    prompt = submit.call_args.kwargs["turn"]
    assert "Revise existing PR #8 at exact head `head`" in prompt
    assert "check out the existing remote branch `openhands/issue-4`" in prompt
    assert "do not open another pull request" in prompt


def test_developer_continues_after_one_submission_fails(tmp_path, monkeypatch):
    module, run = _developer(tmp_path, monkeypatch)
    issues = [
        {
            "number": 1,
            "title": "First",
            "updated_at": "u1",
            "labels": [{"name": "ready-for-dev"}],
        },
        {
            "number": 2,
            "title": "Second",
            "updated_at": "u2",
            "labels": [{"name": "ready-for-dev"}],
        },
    ]
    run.open_issues = lambda: issues
    run.gh_pages = lambda path: []
    run.gh = Mock(
        side_effect=[{"id": 55, "default_branch": "main"}, {"object": {"sha": "base"}}]
    )
    submit = Mock(
        side_effect=[
            RuntimeError("unavailable"),
            {"disposition": "created", "conversation_id": "second"},
        ]
    )
    monkeypatch.setattr(module, "submit_subject_turn", submit)

    run.run()

    assert [call.kwargs["subject_key"] for call in submit.call_args_list] == [
        "55:issue:1",
        "55:issue:2",
    ]


def test_developer_skips_open_pr_awaiting_review(tmp_path, monkeypatch):
    module, run = _developer(tmp_path, monkeypatch)
    issue = {"number": 4, "title": "Feature", "labels": [{"name": "ready-for-dev"}]}
    pr = {
        "number": 8,
        "head": {"ref": "openhands/issue-4", "sha": "head"},
        "labels": [{"name": "openhands-review"}],
    }
    run.open_issues = lambda: [issue]
    run.gh_pages = lambda path: [pr]
    run.gh = Mock(
        side_effect=[{"id": 55, "default_branch": "main"}, {"object": {"sha": "base"}}]
    )
    submit = Mock()
    monkeypatch.setattr(module, "submit_subject_turn", submit)

    run.run()

    submit.assert_not_called()
