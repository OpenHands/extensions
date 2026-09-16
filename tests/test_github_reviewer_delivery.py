"""Contract tests for delegated GitHub PR review."""

from pathlib import Path
from unittest.mock import Mock

from github_automation_helpers import worker


def _reviewer(tmp_path, monkeypatch):
    module = worker("github-pr-reviewer", tmp_path, monkeypatch)
    run = object.__new__(module.PullRequestReviewer)
    run.config = {"trigger_label": "openhands-review"}
    run.repository = "owner/repo"
    run.token = "token"
    run.token_name = "FACTORY_GITHUB_REVIEWER_TOKEN"
    run.dispatcher = Mock()
    return module, run


def test_reviewer_submits_each_labeled_exact_head(tmp_path, monkeypatch):
    module, run = _reviewer(tmp_path, monkeypatch)
    prs = [
        {
            "number": 2,
            "head": {"sha": "head-2"},
            "labels": [{"name": "openhands-review"}],
        },
        {"number": 1, "head": {"sha": "head-1"}, "labels": []},
    ]
    run.gh_pages = lambda path: prs
    run.gh = Mock(side_effect=[{"id": 99}, prs[0]])
    monkeypatch.setattr(
        module.workflow,
        "_latest_trigger_label_event",
        lambda *args: {"id": 7, "created_at": "now"},
    )
    submit = Mock(
        return_value={"disposition": "created", "conversation_id": "conversation"}
    )
    run.dispatcher.deliver = submit

    run.run()

    assert submit.call_args.kwargs["subject"] == "99:pr:2"
    assert submit.call_args.kwargs["delivery"] == "7:head-2"
    prompt = submit.call_args.kwargs["prompt"]
    assert "publish the review directly to GitHub" in prompt
    assert "software-factory/review" in prompt
    assert "software-factory/tests" in prompt
    assert "FACTORY_GITHUB_REVIEWER_TOKEN" in prompt
    assert "gh auth setup-git" in prompt
    assert "GIT_TERMINAL_PROMPT=0" in prompt
    assert "Never paste JSON artifacts" in prompt


def test_reviewer_ignores_unlabeled_prs(tmp_path, monkeypatch):
    _module, run = _reviewer(tmp_path, monkeypatch)
    run.gh_pages = lambda path: [{"number": 1, "labels": [], "head": {"sha": "head"}}]
    run.gh = Mock(return_value={"id": 99})
    submit = Mock()
    run.dispatcher.deliver = submit

    run.run()

    submit.assert_not_called()


def test_reviewer_continues_after_one_submission_fails(tmp_path, monkeypatch):
    module, run = _reviewer(tmp_path, monkeypatch)
    prs = [
        {
            "number": number,
            "labels": [{"name": "openhands-review"}],
            "head": {"sha": f"head-{number}"},
        }
        for number in (1, 2)
    ]
    run.gh_pages = lambda path: prs
    run.gh = Mock(side_effect=[{"id": 99}, *prs])
    monkeypatch.setattr(
        module.workflow,
        "_latest_trigger_label_event",
        lambda *args: {"id": 7, "created_at": "now"},
    )
    submit = Mock(
        side_effect=[
            RuntimeError("temporary failure"),
            {"disposition": "created", "conversation_id": "conversation"},
        ]
    )
    run.dispatcher.deliver = submit

    run.run()

    assert submit.call_count == 2


def test_reviewer_scanner_has_no_conversation_or_runtime_code():
    source = (
        Path(__file__).resolve().parents[1]
        / "skills/github-pr-reviewer/scripts/worker.py"
    ).read_text()
    for forbidden in (
        "RemoteConversation",
        "RemoteWorkspace",
        "AGENT_SERVER_URL",
        "SESSION_API_KEY",
        "AUTOMATION_CONVERSATION_ID",
    ):
        assert forbidden not in source
