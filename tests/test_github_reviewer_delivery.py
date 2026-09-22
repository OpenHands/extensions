"""Contract tests for delegated GitHub PR review."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock
from uuid import NAMESPACE_URL, uuid5

import pytest
from openhands.sdk.conversation.state import ConversationExecutionStatus

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
    # Default to a head with no reported check runs or workflow runs, which the
    # gate reads as green. Gate-specific tests override these.
    run.check_runs = lambda sha: []
    run.workflow_runs = lambda sha: []
    monkeypatch.delenv("AUTOMATION_EVENT_PAYLOAD", raising=False)
    monkeypatch.setattr(
        module.workflow,
        "_latest_trigger_label_event",
        lambda *args: {"id": 7, "created_at": "2026-01-01T00:00:00Z"},
    )
    return module, run


def _checks(*runs, sha="head-2"):
    """Check runs as the API reports them: name, status, and conclusion."""
    return [{"name": name, "status": status, "conclusion": conclusion, "head_sha": sha}
            for name, status, conclusion in runs]


def _run(
    name,
    status,
    conclusion,
    *,
    app="github-actions",
    started_at="",
    run_id=0,
    sha="head-2",
    suite_id=0,
):
    """One check run with the app identity and ordering fields the API sends."""
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "head_sha": sha,
        "app": {"slug": app},
        "started_at": started_at,
        "id": run_id,
        "check_suite": {"id": suite_id},
    }


def _workflow_run(
    name,
    status,
    conclusion,
    *,
    run_id=0,
    suite_id=0,
    workflow_id=0,
    sha="head-2",
    started_at="",
):
    """One Actions workflow run, as the runs endpoint reports it.

    `check_suite_id` links the run to its check runs; a suite whose workflows
    failed before any job reported has no check runs under it.
    """
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "head_sha": sha,
        "id": run_id,
        "check_suite_id": suite_id,
        "workflow_id": workflow_id,
        "run_started_at": started_at,
        "created_at": started_at,
    }


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


def _real_dispatcher(dispatcher_class, monkeypatch, conversation):
    """The shipped dispatcher with its SDK and KV boundaries stubbed."""
    state: dict = {}
    module = sys.modules[dispatcher_class.__module__]

    def kv(key, method, value=None):
        if method == "GET":
            return state.get(key)
        state[key] = value
        return {"key": key, "value": value}

    monkeypatch.setattr(module, "_kv_request", kv)
    monkeypatch.setattr(module, "_register_tools", lambda: None)
    monkeypatch.setenv("AGENT_SERVER_URL", "http://agent")
    monkeypatch.setenv("SESSION_API_KEY", "session")
    monkeypatch.setenv(
        "AUTOMATION_AGENT_PROFILE_ID", "11111111-1111-4111-8111-111111111111"
    )
    monkeypatch.setenv(
        "AUTOMATION_EVENT_PAYLOAD", json.dumps({"automation_id": "automation"})
    )
    workspace = MagicMock()
    workspace.__enter__.return_value = workspace
    workspace.get_secrets.return_value = {}
    monkeypatch.setattr(module, "RemoteWorkspace", lambda **_: workspace)
    attach = MagicMock(return_value=conversation)
    monkeypatch.setattr(module.RemoteConversation, "attach", attach)
    monkeypatch.setattr(
        module.RemoteConversation, "create", MagicMock(return_value=conversation)
    )
    return dispatcher_class(), attach


def test_same_head_re_review_resumes_keyed_conversation_with_refreshed_state(
    tmp_path, monkeypatch
):
    """A first review completes, the linked issue and head checks then change,
    and an explicit re-review at the same head must resume the same conversation
    with a prompt that re-establishes current GitHub state."""
    module, run = _reviewer(tmp_path, monkeypatch)
    conversation = MagicMock()
    conversation.state.execution_status = ConversationExecutionStatus.IDLE
    dispatcher, attach = _real_dispatcher(
        module.AgentConversationDispatcher, monkeypatch, conversation
    )
    run.dispatcher = dispatcher

    first_pr = {
        "number": 2,
        "title": "Add widget",
        "body": "First body",
        "head": {"sha": "head-2"},
        "labels": [{"name": "openhands-review"}],
    }
    # The linked issue was not ready and the head's checks were pending when the
    # first review ran; both moved before the re-review, at the same head.
    refreshed_pr = {
        **first_pr,
        "body": "First body\n\nNow links #5038, which is ready-for-dev.",
        "labels": [{"name": "openhands-review"}, {"name": "reviewed"}],
    }

    def review(label_event_id, pr):
        monkeypatch.setattr(
            module.workflow,
            "_latest_trigger_label_event",
            lambda *args: {"id": label_event_id, "created_at": "now"},
        )
        run.gh_pages = lambda path: [pr]
        run.gh = Mock(side_effect=[{"id": 99}, pr])
        run.run()

    with dispatcher:
        review(7, first_pr)
        review(8, refreshed_pr)

    keyed_id = str(uuid5(NAMESPACE_URL, "automation:99:pr:2"))
    # Both deliveries attach the same keyed conversation and send exactly one
    # new turn each, so reuse and context retention are intact.
    assert str(attach.call_args.args[1]) == keyed_id
    assert {str(call.args[1]) for call in attach.call_args_list} == {keyed_id}
    assert conversation.send_message.call_count == 2
    first, second = (call.args[0] for call in conversation.send_message.call_args_list)

    assert "event 7" in first and "event 8" in second
    # The refreshed PR state reaches the resumed turn, and that turn requires a
    # live re-read of every mutable surface rather than an earlier observation.
    assert "First body" in first
    assert "ready-for-dev" in second
    assert "CURRENT STATE" in second
    assert "body and labels of every linked issue" in second
    assert "GitHub Actions check results" in second
    assert "never repeat an earlier finding" in second


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


def test_reviewer_hands_scope_stop_to_maintainer(tmp_path, monkeypatch):
    """A scope stop is not an approval but still reaches the maintainer."""
    module, run = _reviewer(tmp_path, monkeypatch)
    run.config["maintainers"] = "neubig, VascoSch92"
    pr = {
        "number": 2,
        "head": {"sha": "head-2"},
        "labels": [{"name": "openhands-review"}],
    }
    run.gh_pages = lambda path: (
        [pr]
        if path.startswith("/pulls?")
        else _reviews(verdict="🛑 MAINTAINER DECISION REQUIRED")
    )
    run.gh = Mock(side_effect=[{"id": 99}, pr, pr, {}])
    handoff = Mock(return_value="VascoSch92")
    monkeypatch.setattr(module, "request_maintainer_review", handoff)

    run.run()

    handoff.assert_called_once_with(run, pr, ["neubig", "VascoSch92"])
    assert all(call.args[0] != "PUT" for call in run.gh.call_args_list)
    assert run.gh.call_args_list[-1].args == (
        "DELETE",
        "/issues/2/labels/openhands-review",
    )
    run.dispatcher.deliver.assert_not_called()


# --------------------------------------------------------------------------- #
# Head-eligibility gate: a deterministically blocked head spends no agent work.
# --------------------------------------------------------------------------- #


def _labeled_pr(number=2, sha="head-2"):
    return {
        "number": number,
        "head": {"sha": sha},
        "labels": [{"name": "openhands-review"}],
    }


def _comment(body, login="all-hands-bot", comment_id=900):
    return {
        "id": comment_id,
        "body": body,
        "user": {"login": login},
    }


def _gate_pages(pr, comments):
    return lambda path: (
        [pr] if path.startswith("/pulls?") else comments
    )


def _gate_comment_calls(run, number=2):
    return [
        call
        for call in run.gh.call_args_list
        if call.args[1] == f"/issues/{number}/comments"
    ]


def test_reviewer_blocking_current_head_check_creates_no_conversation(
    tmp_path, monkeypatch
):
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.check_runs = lambda sha: _checks(
        ("Validate PR description", "completed", "failure"), sha=sha
    )

    run.run()

    run.dispatcher.deliver.assert_not_called()
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    body = posted[0].args[2]["body"]
    assert "<!-- openhands-review-gate:blocked:head-2 -->" in body
    assert "`Validate PR description`" in body
    assert "no AI was used to generate this comment" in body


def test_reviewer_green_current_head_creates_exactly_one_conversation(
    tmp_path, monkeypatch
):
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.check_runs = lambda sha: _checks(
        ("Validate PR description", "completed", "success"),
        ("lint", "completed", "skipped"),
        ("optional", "completed", "neutral"),
        sha=sha,
    )
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "conversation",
    }

    run.run()

    run.dispatcher.deliver.assert_called_once()
    assert run.dispatcher.deliver.call_args.kwargs["delivery"] == "7:head-2"


def test_reviewer_pending_current_head_check_waits_without_a_conversation(
    tmp_path, monkeypatch
):
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.check_runs = lambda sha: _checks(
        ("ci", "completed", "success"),
        ("slow-e2e", "in_progress", None),
        sha=sha,
    )

    run.run()

    run.dispatcher.deliver.assert_not_called()
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    body = posted[0].args[2]["body"]
    assert "<!-- openhands-review-gate:waiting:head-2 -->" in body
    assert "`slow-e2e`" in body
    assert "waiting on checks" in body


def test_reviewer_ignores_checks_from_an_obsolete_head(tmp_path, monkeypatch):
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.check_runs = lambda sha: _checks(
        ("Validate PR description", "completed", "failure"), sha="head-1"
    )
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "conversation",
    }

    run.run()

    run.dispatcher.deliver.assert_called_once()
    assert _gate_comment_calls(run) == []


def test_reviewer_blocks_a_workflow_that_failed_with_no_check_runs(
    tmp_path, monkeypatch
):
    """The #426 case: green check-run rollup, but a workflow failed before jobs.

    `Tests`, `Check Extensions`, and `Deprecation deadlines` failed with zero
    jobs, so they contributed no check runs and the commit's rollup was a green
    `pr-title`. Reading only check runs launched the reviewer for red CI.
    """
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.check_runs = lambda sha: _checks(
        ("pr-title / Lint PR title (conventional)", "completed", "success"), sha=sha
    )
    run.workflow_runs = lambda sha: [
        _workflow_run(
            "Tests",
            "completed",
            "failure",
            run_id=3,
            suite_id=3003,
            workflow_id=236324519,
            sha=sha,
        ),
        _workflow_run(
            "Check Extensions",
            "completed",
            "failure",
            run_id=2,
            suite_id=3002,
            workflow_id=260888338,
            sha=sha,
        ),
        _workflow_run(
            "Deprecation deadlines",
            "completed",
            "failure",
            run_id=1,
            suite_id=3001,
            workflow_id=311570275,
            sha=sha,
        ),
    ]

    run.run()

    run.dispatcher.deliver.assert_not_called()
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    body = posted[0].args[2]["body"]
    assert "<!-- openhands-review-gate:blocked:head-2 -->" in body
    assert "`Tests`" in body
    assert "`Check Extensions`" in body
    assert "`Deprecation deadlines`" in body


def test_reviewer_does_not_double_report_a_workflow_that_has_check_runs(
    tmp_path, monkeypatch
):
    """A workflow whose suite already has check runs is not reported twice."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    # The suite the workflow run points at is the one that reported the check,
    # so the workflow run is redundant and must not be reported a second time.
    run.check_runs = lambda sha: [
        _run(
            "Validate PR description",
            "completed",
            "success",
            started_at="2026-09-22T13:00:00Z",
            run_id=1,
            sha=sha,
            suite_id=900,
        )
    ]
    run.workflow_runs = lambda sha: [
        _workflow_run(
            "PR Description Check",
            "completed",
            "success",
            run_id=5,
            suite_id=900,
            workflow_id=341671185,
            sha=sha,
        )
    ]
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "conversation",
    }

    run.run()

    run.dispatcher.deliver.assert_called_once()
    assert _gate_comment_calls(run) == []


def test_reviewer_waits_for_a_workflow_run_that_has_not_finished(
    tmp_path, monkeypatch
):
    """A current-head workflow run still in progress makes the head wait."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.workflow_runs = lambda sha: [
        _workflow_run(
            "Tests",
            "in_progress",
            None,
            run_id=4,
            suite_id=4004,
            workflow_id=236324519,
            sha=sha,
        )
    ]

    run.run()

    run.dispatcher.deliver.assert_not_called()
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    body = posted[0].args[2]["body"]
    assert "<!-- openhands-review-gate:waiting:head-2 -->" in body
    assert "`Tests`" in body


def test_reviewer_ignores_workflow_runs_from_an_obsolete_head(
    tmp_path, monkeypatch
):
    """A failed workflow on an earlier head must not block the push that fixed it."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.workflow_runs = lambda sha: [
        _workflow_run(
            "Tests",
            "completed",
            "failure",
            run_id=1,
            suite_id=3001,
            workflow_id=236324519,
            sha="head-1",
        )
    ]
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "conversation",
    }

    run.run()

    run.dispatcher.deliver.assert_called_once()
    assert _gate_comment_calls(run) == []


def test_reviewer_lets_a_green_workflow_rerun_supersede_a_failed_one(
    tmp_path, monkeypatch
):
    """The latest run of a workflow decides, so a successful re-run clears it."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.workflow_runs = lambda sha: [
        _workflow_run(
            "Tests",
            "completed",
            "failure",
            run_id=1,
            suite_id=3001,
            workflow_id=236324519,
            sha=sha,
            started_at="2026-09-22T13:00:00Z",
        ),
        _workflow_run(
            "Tests",
            "completed",
            "success",
            run_id=2,
            suite_id=3002,
            workflow_id=236324519,
            sha=sha,
            started_at="2026-09-22T13:10:00Z",
        ),
    ]
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "conversation",
    }

    run.run()

    run.dispatcher.deliver.assert_called_once()
    assert _gate_comment_calls(run) == []


def test_reviewer_fails_closed_on_an_unknown_conclusion(tmp_path, monkeypatch):
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.check_runs = lambda sha: _checks(("mystery", "completed", "action_required"), sha=sha)

    run.run()

    run.dispatcher.deliver.assert_not_called()
    body = [
        call.args[2]["body"]
        for call in _gate_comment_calls(run)
        if call.args[0] == "POST"
    ][0]
    assert "<!-- openhands-review-gate:blocked:head-2 -->" in body


def test_reviewer_does_not_duplicate_the_gate_comment_for_the_same_head(
    tmp_path, monkeypatch
):
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    existing = _comment(
        "already explained\n\n<!-- openhands-review-gate:blocked:head-2 -->"
    )
    run.gh_pages = _gate_pages(pr, [existing])
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.check_runs = lambda sha: _checks(("ci", "completed", "failure"), sha=sha)

    run.run()

    run.dispatcher.deliver.assert_not_called()
    assert _gate_comment_calls(run) == []


def test_reviewer_updates_its_gate_comment_when_the_head_moves(
    tmp_path, monkeypatch
):
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    stale = _comment("stale head\n\n<!-- openhands-review-gate:blocked:head-1 -->")
    run.gh_pages = _gate_pages(pr, [stale])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {}])
    run.check_runs = lambda sha: _checks(("ci", "completed", "failure"), sha=sha)

    run.run()

    patched = [call for call in run.gh.call_args_list if call.args[0] == "PATCH"]
    assert len(patched) == 1
    assert patched[0].args[1] == "/issues/comments/900"
    assert "<!-- openhands-review-gate:blocked:head-2 -->" in patched[0].args[2]["body"]
    assert run.dispatcher.deliver.call_count == 0


def test_reviewer_defers_to_an_equivalent_workflow_remediation_comment(
    tmp_path, monkeypatch
):
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    workflow = _comment(
        "The `Validate PR description` check still fails: the PR description's "
        "`HUMAN:` section needs at least 20 characters of what you tested.\n\n"
        "_This is an automated check - no AI was used to generate this comment._"
    )
    run.gh_pages = _gate_pages(pr, [workflow])
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.check_runs = lambda sha: _checks(
        ("Validate PR description", "completed", "failure"), sha=sha
    )

    run.run()

    run.dispatcher.deliver.assert_not_called()
    assert _gate_comment_calls(run) == []


def test_reviewer_ignores_a_marked_comment_a_pr_author_wrote(
    tmp_path, monkeypatch
):
    """A forged marker is untrusted: it neither suppresses nor gets PATCHed."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    forged = _comment(
        "I already handled this\n\n<!-- openhands-review-gate:blocked:head-2 -->",
        login="neubig",
    )
    run.gh_pages = _gate_pages(pr, [forged])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.check_runs = lambda sha: _checks(("ci", "completed", "failure"), sha=sha)

    run.run()

    run.dispatcher.deliver.assert_not_called()
    assert [call for call in run.gh.call_args_list if call.args[0] == "PATCH"] == []
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    assert "<!-- openhands-review-gate:blocked:head-2 -->" in posted[0].args[2]["body"]


def test_reviewer_does_not_defer_to_a_workflow_comment_about_another_check(
    tmp_path, monkeypatch
):
    """A disclosure for a different check must not suppress this head's gate."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    unrelated = _comment(
        "The `Validate PR description` check still fails.\n\n"
        "_This is an automated check - no AI was used to generate this comment._"
    )
    run.gh_pages = _gate_pages(pr, [unrelated])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.check_runs = lambda sha: _checks(("lint", "completed", "failure"), sha=sha)

    run.run()

    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    assert "`lint`" in posted[0].args[2]["body"]
    assert "<!-- openhands-review-gate:blocked:head-2 -->" in posted[0].args[2]["body"]


def test_reviewer_event_path_also_respects_the_gate(tmp_path, monkeypatch):
    _module, run = _reviewer(tmp_path, monkeypatch)
    _event(monkeypatch)
    pr = {"number": 2, "head": {"sha": "head-2"}, "labels": []}
    request = {
        "id": 42,
        "event": "review_requested",
        "created_at": "2026-01-01T00:00:00Z",
        "requested_reviewer": {"login": "all-hands-bot"},
    }
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.gh_pages = lambda path: [request] if path.endswith("/events") else []
    run.check_runs = lambda sha: _checks(
        ("Validate PR description", "completed", "failure"), sha=sha
    )

    run.run()

    run.dispatcher.deliver.assert_not_called()
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1


def test_reviewer_waiting_head_does_not_consume_a_later_green_request(
    tmp_path, monkeypatch
):
    """The trigger survives a waiting run, so the head is reviewed once green."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    pending = _checks(("slow-e2e", "queued", None), sha="head-2")
    state = {"runs": pending}
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}, pr])
    run.check_runs = lambda sha: state["runs"]
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "conversation",
    }

    run.run()
    assert run.dispatcher.deliver.call_count == 0

    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    state["runs"] = _checks(("slow-e2e", "completed", "success"), sha="head-2")
    run.run()
    assert run.dispatcher.deliver.call_count == 1



def test_reviewer_ignores_a_superseded_failure_for_the_same_check(
    tmp_path, monkeypatch
):
    """The live #647/#649 case: an early failure and a later success, one SHA.

    GitHub lists both `Validate PR description` runs on a single commit when the
    PR body is fixed without a code push, so only the latest run may count.
    """
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.check_runs = lambda sha: [
        _run(
            "Validate PR description",
            "completed",
            "success",
            started_at="2026-09-22T13:18:41Z",
            run_id=106761769135,
        ),
        _run(
            "Validate PR description",
            "completed",
            "failure",
            started_at="2026-09-22T13:04:07Z",
            run_id=106756418507,
        ),
    ]
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "conversation",
    }

    run.run()

    run.dispatcher.deliver.assert_called_once()
    assert _gate_comment_calls(run) == []


def test_reviewer_prefers_run_id_to_break_a_start_time_tie(tmp_path, monkeypatch):
    """Two runs sharing a start time are ordered by run ID, not list order."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.check_runs = lambda sha: [
        _run(
            "ci",
            "completed",
            "failure",
            started_at="2026-09-22T13:04:07Z",
            run_id=106756418507,
        ),
        _run(
            "ci",
            "completed",
            "success",
            started_at="2026-09-22T13:04:07Z",
            run_id=106761769135,
        ),
    ]
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "conversation",
    }

    run.run()

    run.dispatcher.deliver.assert_called_once()
    assert _gate_comment_calls(run) == []


def test_reviewer_waits_for_a_newer_rerun_that_superseded_a_success(
    tmp_path, monkeypatch
):
    """A later queued re-run of the same check makes the head wait, not pass."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.check_runs = lambda sha: [
        _run("ci", "completed", "success", started_at="2026-09-22T13:00:00Z", run_id=1),
        _run("ci", "queued", None, started_at="2026-09-22T13:10:00Z", run_id=2),
    ]

    run.run()

    run.dispatcher.deliver.assert_not_called()
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    body = posted[0].args[2]["body"]
    assert "<!-- openhands-review-gate:waiting:head-2 -->" in body
    assert "`ci`" in body


def test_reviewer_treats_same_name_from_different_apps_as_distinct_checks(
    tmp_path, monkeypatch
):
    """Grouping by name and app identity keeps two apps' checks independent."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.check_runs = lambda sha: [
        _run(
            "ci",
            "completed",
            "success",
            app="github-actions",
            started_at="2026-09-22T13:10:00Z",
            run_id=2,
        ),
        _run(
            "ci",
            "completed",
            "failure",
            app="custom-ci",
            started_at="2026-09-22T13:00:00Z",
            run_id=1,
        ),
    ]

    run.run()

    run.dispatcher.deliver.assert_not_called()
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    assert "<!-- openhands-review-gate:blocked:head-2 -->" in posted[0].args[2]["body"]


def test_reviewer_waits_for_a_newer_queued_run_without_a_start_time(
    tmp_path, monkeypatch
):
    """A queued re-run with `started_at: null` still supersedes an earlier run.

    GitHub allows a queued or requested check run before it has a start
    timestamp, so ordering must not treat the absent start time as earlier than
    a completed run's timestamp and let the stale success launch the review.
    """
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.check_runs = lambda sha: [
        _run(
            "ci",
            "completed",
            "success",
            started_at="2026-09-22T13:00:00Z",
            run_id=1,
        ),
        _run("ci", "queued", None, started_at=None, run_id=2),
    ]

    run.run()

    run.dispatcher.deliver.assert_not_called()
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    body = posted[0].args[2]["body"]
    assert "<!-- openhands-review-gate:waiting:head-2 -->" in body
    assert "`ci`" in body


# Scheduled retry: a five-minute scan resumes an outstanding review request.
# --------------------------------------------------------------------------- #


def _requested_pr(number=2, sha="head-2", draft=False):
    return {
        "number": number,
        "head": {"sha": sha},
        "labels": [],
        "draft": draft,
        "requested_reviewers": [{"login": "all-hands-bot"}],
    }


def _review_request_event(request_id=42):
    return {
        "id": request_id,
        "event": "review_requested",
        "created_at": "2026-01-01T00:00:00Z",
        "requested_reviewer": {"login": "all-hands-bot"},
    }


def _request_pages(pr, request, comments):
    return lambda path: (
        [pr]
        if path.startswith("/pulls?")
        else ([request] if path.endswith("/events") else comments)
    )


def test_reviewer_scheduled_scan_reviews_an_outstanding_request(tmp_path, monkeypatch):
    """A request made before CI finished is reviewed once the head is green."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _requested_pr()
    state = {"runs": _checks(("slow-e2e", "queued", None), sha="head-2")}
    run.check_runs = lambda sha: state["runs"]
    run.gh_pages = _request_pages(pr, _review_request_event(), [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}, pr])
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "conversation",
    }

    run.run()
    assert run.dispatcher.deliver.call_count == 0
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    waiting = posted[0].args[2]["body"]
    assert "<!-- openhands-review-gate:waiting:head-2 -->" in waiting
    assert "The scheduled scan retries" in waiting

    run.gh_pages = _request_pages(pr, _review_request_event(), [])
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    state["runs"] = _checks(("slow-e2e", "completed", "success"), sha="head-2")
    run.run()

    run.dispatcher.deliver.assert_called_once()
    call = run.dispatcher.deliver.call_args.kwargs
    assert call["delivery"] == "42:head-2"
    assert "latest review request for `all-hands-bot` event 42" in call["prompt"]


def test_reviewer_repeated_scans_do_not_duplicate_a_requested_review(
    tmp_path, monkeypatch
):
    """Two scans over one outstanding request produce one stable delivery key."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _requested_pr()
    run.check_runs = lambda sha: _checks(("ci", "completed", "success"), sha=sha)
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "conversation",
    }

    for _ in range(2):
        run.gh_pages = _request_pages(pr, _review_request_event(), [])
        run.gh = Mock(side_effect=[{"id": 99}, pr])
        run.run()

    assert run.dispatcher.deliver.call_count == 2
    deliveries = {
        call.kwargs["delivery"] for call in run.dispatcher.deliver.call_args_list
    }
    assert deliveries == {"42:head-2"}


def test_reviewer_scheduled_scan_ignores_a_draft_with_a_request(
    tmp_path, monkeypatch
):
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _requested_pr(draft=True)
    run.gh_pages = lambda path: [pr]
    run.gh = Mock(return_value={"id": 99})

    run.run()

    run.dispatcher.deliver.assert_not_called()


def test_reviewer_scheduled_scan_ignores_an_unlabeled_unrequested_pr(
    tmp_path, monkeypatch
):
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = {"number": 3, "head": {"sha": "head-3"}, "labels": [], "draft": False}
    run.gh_pages = lambda path: [pr]
    run.gh = Mock(return_value={"id": 99})

    run.run()

    run.dispatcher.deliver.assert_not_called()
    assert run.gh.call_count == 1


def test_reviewer_scheduled_scan_keeps_the_label_path_unchanged(
    tmp_path, monkeypatch
):
    """A labeled PR is still driven by its label event, not by a request."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.check_runs = lambda sha: _checks(("ci", "completed", "success"), sha=sha)
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "conversation",
    }

    run.run()

    run.dispatcher.deliver.assert_called_once()
    assert run.dispatcher.deliver.call_args.kwargs["delivery"] == "7:head-2"


def test_reviewer_event_gate_comment_does_not_promise_a_scan(
    tmp_path, monkeypatch
):
    """An event-only deployment names the retry it actually honors."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    _event(monkeypatch)
    pr = {"number": 2, "head": {"sha": "head-2"}, "labels": []}
    request = _review_request_event()
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.gh_pages = lambda path: [request] if path.endswith("/events") else []
    run.check_runs = lambda sha: _checks(("slow-e2e", "in_progress", None), sha=sha)

    run.run()

    run.dispatcher.deliver.assert_not_called()
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    body = posted[0].args[2]["body"]
    assert "a new `all-hands-bot` review request starts the review" in body
    assert "scheduled" not in body.lower()


def test_reviewer_event_blocked_gate_comment_does_not_promise_a_scan(
    tmp_path, monkeypatch
):
    _module, run = _reviewer(tmp_path, monkeypatch)
    _event(monkeypatch)
    pr = {"number": 2, "head": {"sha": "head-2"}, "labels": []}
    request = _review_request_event()
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.gh_pages = lambda path: [request] if path.endswith("/events") else []
    run.check_runs = lambda sha: _checks(("ci", "completed", "failure"), sha=sha)

    run.run()

    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    body = posted[0].args[2]["body"]
    assert "request `all-hands-bot` again" in body
    assert "scheduled" not in body.lower()


def test_reviewer_scheduled_scan_blocked_comment_names_the_scan(
    tmp_path, monkeypatch
):
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _requested_pr()
    run.gh_pages = _request_pages(pr, _review_request_event(), [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.check_runs = lambda sha: _checks(("ci", "completed", "failure"), sha=sha)

    run.run()

    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    body = posted[0].args[2]["body"]
    assert "The scheduled scan then starts the review" in body

