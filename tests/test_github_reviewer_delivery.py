"""Contract tests for delegated GitHub PR review."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from github_automation_helpers import worker


def _reviews(
    verdict="✅ APPROVED",
    submitted_at="2026-01-02T00:00:00Z",
    sha="head-2",
    login="all-hands-bot",
):
    return [
        {
            "body": f"Review body\n\n{verdict}",
            "commit_id": sha,
            "submitted_at": submitted_at,
            "user": {"login": login},
        }
    ]


def _reviewer(tmp_path, monkeypatch):
    module = worker("github-pr-reviewer", tmp_path, monkeypatch)
    run = object.__new__(module.PullRequestReviewer)
    run.config = {"trigger_label": "openhands-review"}
    run.repository = "owner/repo"
    run.token = "token"
    run.token_name = "FACTORY_GITHUB_REVIEWER_TOKEN"
    run.github_login = "all-hands-bot"
    run.dispatcher = Mock()
    monkeypatch.delenv("AUTOMATION_EVENT_PAYLOAD", raising=False)
    monkeypatch.setattr(
        module.workflow,
        "_latest_trigger_label_event",
        lambda *args: {"id": 7, "created_at": "2026-01-01T00:00:00Z"},
    )
    return module, run


def _event(monkeypatch, *, action="review_requested", login="all-hands-bot"):
    payload = {
        "action": action,
        "repository": {"full_name": "owner/repo"},
        "pull_request": {"number": 2},
    }
    if action == "review_requested":
        payload["requested_reviewer"] = {"login": login}
    else:
        payload["review"] = {"user": {"login": login}}
    monkeypatch.setenv(
        "AUTOMATION_EVENT_PAYLOAD",
        json.dumps({"automation_id": "automation", "event": {"payload": payload}}),
    )


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
    assert "Do not create commit statuses or Checks" in prompt
    assert "FACTORY_GITHUB_REVIEWER_TOKEN" in prompt
    assert "gh auth setup-git" in prompt
    assert "GIT_TERMINAL_PROMPT=0" in prompt
    assert "Never paste JSON artifacts" in prompt
    assert "stop immediately" in prompt


def test_reviewer_submits_requested_exact_head(tmp_path, monkeypatch):
    _module, run = _reviewer(tmp_path, monkeypatch)
    _event(monkeypatch)
    pr = {"number": 2, "head": {"sha": "head-2"}, "labels": []}
    request = {
        "id": 42,
        "event": "review_requested",
        "created_at": "2026-01-01T00:00:00Z",
        "requested_reviewer": {"login": "all-hands-bot"},
    }
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.gh_pages = lambda path: [request] if path.endswith("/events") else []
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "conversation",
    }

    run.run()

    call = run.dispatcher.deliver.call_args.kwargs
    assert call["subject"] == "99:pr:2"
    assert call["delivery"] == "42:head-2"
    assert "latest review request for `all-hands-bot` event 42" in call["prompt"]
    assert "new head requires another reviewer request" in call["prompt"]


def test_reviewer_ignores_request_for_another_reviewer(tmp_path, monkeypatch):
    _module, run = _reviewer(tmp_path, monkeypatch)
    _event(monkeypatch, login="human")
    run.gh = Mock(return_value={"id": 99})

    run.run()

    run.dispatcher.deliver.assert_not_called()


def test_reviewer_event_hands_positive_review_to_maintainer(tmp_path, monkeypatch):
    module, run = _reviewer(tmp_path, monkeypatch)
    _event(monkeypatch, action="submitted")
    run.config["maintainers"] = "neubig, VascoSch92"
    pr = {"number": 2, "head": {"sha": "head-2"}, "labels": []}
    request = {
        "id": 42,
        "event": "review_requested",
        "created_at": "2026-01-01T00:00:00Z",
        "requested_reviewer": {"login": "all-hands-bot"},
    }
    run.gh = Mock(side_effect=[{"id": 99}, pr, pr])
    run.gh_pages = lambda path: [request] if path.endswith("/events") else _reviews()
    handoff = Mock(return_value="VascoSch92")
    monkeypatch.setattr(module, "request_maintainer_review", handoff)

    run.run()

    handoff.assert_called_once_with(run, pr, ["neubig", "VascoSch92"])
    assert all(call.args[0] != "DELETE" for call in run.gh.call_args_list)
    run.dispatcher.deliver.assert_not_called()


def test_reviewer_submitted_non_decisive_review_does_not_dispatch(
    tmp_path, monkeypatch
):
    module, run = _reviewer(tmp_path, monkeypatch)
    _event(monkeypatch, action="submitted")
    run.config["maintainers"] = "neubig"
    pr = {"number": 2, "head": {"sha": "head-2"}, "labels": []}
    request = {
        "id": 42,
        "event": "review_requested",
        "created_at": "2026-01-01T00:00:00Z",
        "requested_reviewer": {"login": "all-hands-bot"},
    }
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.gh_pages = lambda path: (
        [request] if path.endswith("/events") else _reviews(verdict="LGTM")
    )
    handoff = Mock()
    monkeypatch.setattr(module, "request_maintainer_review", handoff)

    run.run()

    run.dispatcher.deliver.assert_not_called()
    handoff.assert_not_called()


def test_reviewer_submitted_review_on_superseded_head_does_not_dispatch(
    tmp_path, monkeypatch
):
    module, run = _reviewer(tmp_path, monkeypatch)
    _event(monkeypatch, action="submitted")
    run.config["maintainers"] = "neubig"
    pr = {"number": 2, "head": {"sha": "head-3"}, "labels": []}
    request = {
        "id": 42,
        "event": "review_requested",
        "created_at": "2026-01-01T00:00:00Z",
        "requested_reviewer": {"login": "all-hands-bot"},
    }
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.gh_pages = lambda path: (
        [request] if path.endswith("/events") else _reviews(sha="head-2")
    )
    handoff = Mock()
    monkeypatch.setattr(module, "request_maintainer_review", handoff)

    run.run()

    run.dispatcher.deliver.assert_not_called()
    handoff.assert_not_called()


def test_reviewer_redelivers_when_review_predates_latest_label(tmp_path, monkeypatch):
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = {
        "number": 2,
        "head": {"sha": "head-2"},
        "labels": [{"name": "openhands-review"}],
    }
    run.gh_pages = lambda path: (
        [pr]
        if path.startswith("/pulls?")
        else _reviews(submitted_at="2025-12-31T00:00:00Z")
    )
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.dispatcher.deliver.return_value = {
        "disposition": "continued",
        "conversation_id": "conversation",
    }

    run.run()

    run.dispatcher.deliver.assert_called_once()
    assert run.dispatcher.deliver.call_args.kwargs["delivery"] == "7:head-2"


def test_reviewer_does_not_trust_another_reviewers_verdict(tmp_path, monkeypatch):
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = {
        "number": 2,
        "head": {"sha": "head-2"},
        "labels": [{"name": "openhands-review"}],
    }
    run.gh_pages = lambda path: (
        [pr] if path.startswith("/pulls?") else _reviews(login="other-reviewer")
    )
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.dispatcher.deliver.return_value = {
        "disposition": "continued",
        "conversation_id": "conversation",
    }

    run.run()

    run.dispatcher.deliver.assert_called_once()


def test_reviewer_ignores_unlabeled_prs(tmp_path, monkeypatch):
    _module, run = _reviewer(tmp_path, monkeypatch)
    run.gh_pages = lambda path: [{"number": 1, "labels": [], "head": {"sha": "head"}}]
    run.gh = Mock(return_value={"id": 99})
    submit = Mock()
    run.dispatcher.deliver = submit

    run.run()

    submit.assert_not_called()


def test_reviewer_continues_after_one_submission_fails_then_reports_run_failure(
    tmp_path, monkeypatch
):
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

    with pytest.raises(RuntimeError, match="Reviewer scan failed for PRs: #1"):
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


def test_reviewer_hands_positive_exact_head_to_maintainer(tmp_path, monkeypatch):
    module, run = _reviewer(tmp_path, monkeypatch)
    run.config["maintainers"] = "neubig, VascoSch92"
    pr = {
        "number": 2,
        "head": {"sha": "head-2"},
        "labels": [{"name": "openhands-review"}],
    }
    run.gh_pages = lambda path: [pr] if path.startswith("/pulls?") else _reviews()
    run.gh = Mock(side_effect=[{"id": 99}, pr, pr, {}])
    handoff = Mock(return_value="VascoSch92")
    monkeypatch.setattr(module, "request_maintainer_review", handoff)

    run.run()

    handoff.assert_called_once_with(run, pr, ["neubig", "VascoSch92"])
    assert run.gh.call_args_list[-1].args == (
        "DELETE",
        "/issues/2/labels/openhands-review",
    )
    run.dispatcher.deliver.assert_not_called()


def test_reviewer_retries_failed_handoff_without_clearing_label(tmp_path, monkeypatch):
    module, run = _reviewer(tmp_path, monkeypatch)
    run.config["maintainers"] = "neubig"
    pr = {
        "number": 2,
        "head": {"sha": "head-2"},
        "labels": [{"name": "openhands-review"}],
    }
    run.gh_pages = lambda path: [pr] if path.startswith("/pulls?") else _reviews()
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    monkeypatch.setattr(
        module,
        "request_maintainer_review",
        Mock(side_effect=RuntimeError("temporary GitHub failure")),
    )

    with pytest.raises(RuntimeError, match="Reviewer scan failed for PRs: #2"):
        run.run()

    assert all(call.args[0] != "DELETE" for call in run.gh.call_args_list)
    run.dispatcher.deliver.assert_not_called()


def test_reviewer_reports_permanent_handoff_error_once(tmp_path, monkeypatch):
    module, run = _reviewer(tmp_path, monkeypatch)
    run.config["maintainers"] = "author"
    pr = {
        "number": 2,
        "head": {"sha": "head-2"},
        "labels": [{"name": "openhands-review"}],
    }
    run.gh_pages = lambda path: [pr] if path.startswith("/pulls?") else _reviews()
    run.gh = Mock(side_effect=[{"id": 99}, pr, {}, pr, {}])
    monkeypatch.setattr(
        module,
        "request_maintainer_review",
        Mock(
            side_effect=module.HandoffConfigurationError(
                "No eligible maintainer remains"
            )
        ),
    )

    run.run()

    assert "configuration check" in run.gh.call_args_list[2].args[2]["body"]
    assert run.gh.call_args_list[-1].args == (
        "DELETE",
        "/issues/2/labels/openhands-review",
    )


def test_reviewer_keeps_label_when_head_moves_before_cleanup(tmp_path, monkeypatch):
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = {
        "number": 2,
        "head": {"sha": "head-2"},
        "labels": [{"name": "openhands-review"}],
    }
    moved = {**pr, "head": {"sha": "head-3"}}
    run.gh_pages = lambda path: (
        [pr] if path.startswith("/pulls?") else _reviews(verdict="🔄 CHANGES REQUESTED")
    )
    run.gh = Mock(side_effect=[{"id": 99}, pr, moved])

    run.run()

    assert all(call.args[0] != "DELETE" for call in run.gh.call_args_list)
    run.dispatcher.deliver.assert_not_called()


def test_reviewer_does_not_handoff_failed_review(tmp_path, monkeypatch):
    module, run = _reviewer(tmp_path, monkeypatch)
    run.config["maintainers"] = "neubig"
    pr = {
        "number": 2,
        "head": {"sha": "head-2"},
        "labels": [{"name": "openhands-review"}],
    }
    run.gh_pages = lambda path: (
        [pr] if path.startswith("/pulls?") else _reviews(verdict="🔄 CHANGES REQUESTED")
    )
    run.gh = Mock(side_effect=[{"id": 99}, pr, pr, {}])
    handoff = Mock()
    monkeypatch.setattr(module, "request_maintainer_review", handoff)

    run.run()

    handoff.assert_not_called()
    run.dispatcher.deliver.assert_not_called()
