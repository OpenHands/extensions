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
    run.statuses = lambda sha: {}
    # Default to no required-check signal so the gate uses its conservative
    # all-run fallback, matching the pre-required-check behavior. Tests that
    # exercise required-only classification override this.
    run.required_check_contexts = lambda number: []
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
        # A draft is not eligible for the unrequested scan, so it is skipped
        # without a full read and only the labeled head is submitted.
        {"number": 1, "head": {"sha": "head-1"}, "labels": [], "draft": True},
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


def test_reviewer_ignores_a_draft_unlabeled_unrequested_pr(tmp_path, monkeypatch):
    """The unrequested scan skips a draft: it is not reviewable yet."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    run.gh_pages = lambda path: [
        {"number": 1, "labels": [], "head": {"sha": "head"}, "draft": True}
    ]
    run.gh = Mock(return_value={"id": 99})
    submit = Mock()
    run.dispatcher.deliver = submit

    run.run()

    submit.assert_not_called()
    # Skipped before the full PR read, so only the repository-id lookup ran.
    assert run.gh.call_count == 1


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


def test_reviewer_ignores_an_optional_zero_job_workflow_on_a_green_required_head(
    tmp_path, monkeypatch
):
    """The #17200 case: the only required check passes, an optional workflow does not.

    OpenHands/OpenHands#17200 passes `test-and-build (ubuntu)`, its only
    required check, while the optional `release ready` workflow has a zero-job
    `startup_failure`. Scheduled discovery must classify on the required check
    and dispatch, not block on the optional workflow.
    """
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.required_check_contexts = lambda number: [
        {"name": "test-and-build (ubuntu)", "kind": "CheckRun"}
    ]
    run.check_runs = lambda sha: _checks(
        ("test-and-build (ubuntu)", "completed", "success"), sha=sha
    )
    run.workflow_runs = lambda sha: [
        _workflow_run(
            "release ready",
            "completed",
            "startup_failure",
            run_id=1,
            suite_id=1001,
            workflow_id=305675242,
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


def test_reviewer_blocks_when_a_required_check_fails(tmp_path, monkeypatch):
    """A failed required check still blocks scheduled discovery."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.required_check_contexts = lambda number: [
        {"name": "test-and-build (ubuntu)", "kind": "CheckRun"}
    ]
    run.check_runs = lambda sha: _checks(
        ("test-and-build (ubuntu)", "completed", "failure"),
        ("optional", "completed", "startup_failure"),
        sha=sha,
    )

    run.run()

    run.dispatcher.deliver.assert_not_called()
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    body = posted[0].args[2]["body"]
    assert "<!-- openhands-review-gate:blocked:head-2 -->" in body
    assert "`test-and-build (ubuntu)`" in body
    assert "`optional`" not in body


def test_reviewer_waits_for_a_pending_required_check(tmp_path, monkeypatch):
    """A required check that has not finished makes scheduled discovery wait."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.required_check_contexts = lambda number: [
        {"name": "test-and-build (ubuntu)", "kind": "CheckRun"}
    ]
    run.check_runs = lambda sha: _checks(
        ("test-and-build (ubuntu)", "in_progress", None), sha=sha
    )

    run.run()

    run.dispatcher.deliver.assert_not_called()
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    body = posted[0].args[2]["body"]
    assert "<!-- openhands-review-gate:waiting:head-2 -->" in body
    assert "`test-and-build (ubuntu)`" in body


def test_reviewer_waits_for_a_required_context_with_no_current_head_run(
    tmp_path, monkeypatch
):
    """A required name that reported no check run is expected, so the head waits.

    A required context can appear without a matching current-head check run (a
    required commit status, or a re-run whose name now resolves elsewhere).
    Unfulfilled is never approval.
    """
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.required_check_contexts = lambda number: [
        {"name": "test", "kind": "CheckRun"},
    ]
    run.check_runs = lambda sha: []

    run.run()

    run.dispatcher.deliver.assert_not_called()
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    body = posted[0].args[2]["body"]
    assert "<!-- openhands-review-gate:waiting:head-2 -->" in body
    assert "`test`" in body


def test_reviewer_falls_back_to_all_checks_when_required_reported_nothing(
    tmp_path, monkeypatch
):
    """The #426 shape through the required path: required checks never reported.

    `isRequired` is a field on each context in the head's rollup, so a required
    check that failed before creating any check run has no node and the required
    set comes back empty. An empty set must fall back to the full current-head
    rollup rather than treating the head as green.
    """
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.required_check_contexts = lambda number: []
    run.check_runs = lambda sha: _checks(
        ("pr-title / Lint PR title (conventional)", "completed", "success"), sha=sha
    )
    run.workflow_runs = lambda sha: [
        _workflow_run(
            "Tests",
            "completed",
            "failure",
            run_id=1,
            suite_id=3001,
            workflow_id=236324519,
            sha=sha,
        )
    ]

    run.run()

    run.dispatcher.deliver.assert_not_called()
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    body = posted[0].args[2]["body"]
    assert "<!-- openhands-review-gate:blocked:head-2 -->" in body
    assert "`Tests`" in body


def test_reviewer_ignores_an_optional_failure_but_reads_required_statuses(
    tmp_path, monkeypatch
):
    """A required commit status is classified alongside required check runs."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])
    run.required_check_contexts = lambda number: [
        {"name": "test-and-build (ubuntu)", "kind": "CheckRun"},
        {"name": "ci/required", "kind": "StatusContext"},
    ]
    run.check_runs = lambda sha: _checks(
        ("test-and-build (ubuntu)", "completed", "success"), sha=sha
    )
    run.statuses = lambda sha: {"ci/required": "failure"}

    run.run()

    run.dispatcher.deliver.assert_not_called()
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    assert "`ci/required`" in posted[0].args[2]["body"]


def test_reviewer_falls_back_to_every_check_when_required_signal_is_unavailable(
    tmp_path, monkeypatch
):
    """A failed required-check read must not approve silently."""

    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    run.gh_pages = _gate_pages(pr, [])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {"id": 1234}])

    def unavailable(number):
        raise RuntimeError("GitHub required-check query failed")

    run.required_check_contexts = unavailable
    run.check_runs = lambda sha: _checks(("ci", "completed", "failure"), sha=sha)

    run.run()

    run.dispatcher.deliver.assert_not_called()
    posted = [call for call in _gate_comment_calls(run) if call.args[0] == "POST"]
    assert len(posted) == 1
    assert "<!-- openhands-review-gate:blocked:head-2 -->" in posted[0].args[2]["body"]


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
    """An identical explanation already on the PR is left untouched."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    existing = _comment(run._gate_body("head-2", "blocked", ["ci"], scheduled=True))
    run.gh_pages = _gate_pages(pr, [existing])
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.check_runs = lambda sha: _checks(("ci", "completed", "failure"), sha=sha)

    run.run()

    run.dispatcher.deliver.assert_not_called()
    assert _gate_comment_calls(run) == []
    assert [call for call in run.gh.call_args_list if call.args[0] == "PATCH"] == []


def test_reviewer_rewrites_a_stale_gate_comment_body_for_the_same_head(
    tmp_path, monkeypatch
):
    """Same head, changed wording: the managed comment is rewritten, not stacked."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _labeled_pr()
    stale = _comment(
        "old wording\n\n<!-- openhands-review-gate:blocked:head-2 -->"
    )
    run.gh_pages = _gate_pages(pr, [stale])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {}])
    run.check_runs = lambda sha: _checks(("ci", "completed", "failure"), sha=sha)

    run.run()

    assert [call for call in _gate_comment_calls(run) if call.args[0] == "POST"] == []
    patched = [call for call in run.gh.call_args_list if call.args[0] == "PATCH"]
    assert len(patched) == 1
    assert patched[0].args[1] == "/issues/comments/900"
    body = patched[0].args[2]["body"]
    assert "<!-- openhands-review-gate:blocked:head-2 -->" in body
    assert "old wording" not in body


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


def test_reviewer_explicit_request_bypasses_the_ci_gate(tmp_path, monkeypatch):
    """An explicit `all-hands-bot` request is the intake exception.

    The caller asked for this head by name, so a red or pending required check
    must not stop the dispatch - and the gate leaves no explanatory comment.
    """
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
    run.check_runs = lambda sha: _checks(
        ("Validate PR description", "completed", "failure"), sha=sha
    )
    run.required_check_contexts = lambda number: [
        {"name": "Validate PR description", "kind": "CheckRun"}
    ]
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "conversation",
    }

    run.run()

    run.dispatcher.deliver.assert_called_once()
    assert run.dispatcher.deliver.call_args.kwargs["delivery"] == "42:head-2"
    assert _gate_comment_calls(run) == []


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


def test_reviewer_scheduled_scan_reviews_an_unrequested_green_pr(
    tmp_path, monkeypatch
):
    """A green PR with no request and no label is still reviewed on a scan."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = {"number": 3, "head": {"sha": "head-3"}, "labels": [], "draft": False}
    run.gh_pages = lambda path: (
        [] if path.endswith("/reviews") else [pr]
    )
    run.gh = Mock(side_effect=[{"id": 99}, pr])
    run.check_runs = lambda sha: _checks(("ci", "completed", "success"), sha=sha)
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "conversation",
    }

    run.run()

    run.dispatcher.deliver.assert_called_once()
    call = run.dispatcher.deliver.call_args.kwargs
    assert call["subject"] == "99:pr:3"
    assert call["delivery"] == "scan:owner/repo:3:head-3"
    assert "scheduled scan of open, non-draft pull requests" in call["prompt"]


def test_reviewer_scheduled_scan_skips_a_pr_with_a_current_head_review(
    tmp_path, monkeypatch
):
    """An already-reviewed head is not re-reviewed by the unrequested scan."""
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = {"number": 3, "head": {"sha": "head-3"}, "labels": [], "draft": False}
    run.gh_pages = lambda path: (
        _reviews(sha="head-3") if path.endswith("/reviews") else [pr]
    )
    # The repository-id lookup, the full PR read, and the head re-read that the
    # completion path performs to confirm the reviewed head has not moved.
    run.gh = Mock(side_effect=[{"id": 99}, pr, pr])
    run.check_runs = lambda sha: _checks(("ci", "completed", "success"), sha=sha)

    run.run()

    run.dispatcher.deliver.assert_not_called()


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


def test_reviewer_event_body_names_the_request_retry_not_a_scan(
    tmp_path, monkeypatch
):
    """The event-only body names the retry it actually honors.

    Explicit `all-hands-bot` requests bypass the CI gate, so this body is not
    reached through `run()`; assert the wording contract directly.
    """
    _module, run = _reviewer(tmp_path, monkeypatch)
    body = run._gate_body("head-2", "waiting", ["slow-e2e"], scheduled=False)

    assert "remove the outstanding `all-hands-bot` request and request " in body
    assert "GitHub will not accept a second request" in body
    assert "scheduled" not in body.lower()


def test_reviewer_event_blocked_body_names_the_request_retry_not_a_scan(
    tmp_path, monkeypatch
):
    _module, run = _reviewer(tmp_path, monkeypatch)
    body = run._gate_body("head-2", "blocked", ["ci"], scheduled=False)

    assert "remove the outstanding `all-hands-bot` request and request " in body
    assert "GitHub will not accept a second request" in body
    assert "scheduled" not in body.lower()


def test_reviewer_rewords_the_managed_comment_when_an_event_deployment_becomes_scheduled(
    tmp_path, monkeypatch
):
    """An event-only gate comment is reworded once a cron scan exists.

    A PR first gated by the event-only deployment keeps a "remove and re-request"
    comment on the same head. When the automation is switched to a scheduled scan
    the comment must name the retry that is now actually deployed, in place,
    without creating a second comment.
    """
    _module, run = _reviewer(tmp_path, monkeypatch)
    pr = _requested_pr()
    request = _review_request_event()
    run.check_runs = lambda sha: _checks(("slow-e2e", "in_progress", None), sha=sha)

    # The comment an event-only deployment would have left on this head.
    event_body = run._gate_body("head-2", "waiting", ["slow-e2e"], scheduled=False)
    assert "remove the outstanding `all-hands-bot` request" in event_body
    managed = _comment(event_body)

    run.gh_pages = _request_pages(pr, request, [managed])
    run.gh = Mock(side_effect=[{"id": 99}, pr, {}])
    run.run()

    assert [call for call in _gate_comment_calls(run) if call.args[0] == "POST"] == []
    patched = [call for call in run.gh.call_args_list if call.args[0] == "PATCH"]
    assert len(patched) == 1
    assert patched[0].args[1] == "/issues/comments/900"
    scheduled_body = patched[0].args[2]["body"]
    assert "<!-- openhands-review-gate:waiting:head-2 -->" in scheduled_body
    assert "The scheduled scan retries" in scheduled_body
    assert "remove the outstanding" not in scheduled_body


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



# --------------------------------------------------------------------------- #
# Bounded intake: one scheduled scan starts a small, configurable number of new
# review conversations across every configured repository, oldest request first.
# --------------------------------------------------------------------------- #


class _DedupeDispatcher:
    """An in-memory stand-in for the shipped dispatcher's dedupe contract.

    The real AgentConversationDispatcher needs an agent server and SDK, so this
    reproduces only the contract the worker relies on: a delivery keyed by
    (subject, delivery) starts one conversation and reports `created` once, then
    reports `deduplicated` for the same key. That is what lets a repeat scan
    reuse a conversation without spending another intake slot.
    """

    def __init__(self):
        self.seen = {}
        self.calls = []
        self.prompts = []

    def deliver(self, *, subject, delivery, prompt):
        self.calls.append((subject, delivery))
        self.prompts.append(prompt)
        if self.seen.get(subject) == delivery:
            return {"disposition": "deduplicated", "conversation_id": subject}
        self.seen[subject] = delivery
        return {"disposition": "created", "conversation_id": subject}


def _scan_reviewers(tmp_path, monkeypatch, repositories, *, max_new=None):
    """One module and one reviewer per repository, as the shipped scan builds them."""
    module = worker("github-pr-reviewer", tmp_path, monkeypatch)
    monkeypatch.delenv("AUTOMATION_EVENT_PAYLOAD", raising=False)
    monkeypatch.setattr(
        module.workflow,
        "_latest_trigger_label_event",
        lambda *args: {"id": 7, "created_at": "2026-01-01T00:00:00Z"},
    )
    reviewers = []
    for repository in repositories:
        run = object.__new__(module.PullRequestReviewer)
        run.config = {"trigger_label": "openhands-review"}
        if max_new is not None:
            run.config["max_new_per_run"] = max_new
        run.repository = repository
        run.token = "token"
        run.token_name = "FACTORY_GITHUB_REVIEWER_TOKEN"
        run.github_login = "all-hands-bot"
        run.dispatcher = _DedupeDispatcher()
        run.check_runs = lambda sha: []
        run.workflow_runs = lambda sha: []
        reviewers.append(run)
    return module, reviewers


def _run_scan(module, reviewers):
    """Drive the shipped scheduled-scan control flow over the given reviewers.

    `module.run_scan` is the shipped entrypoint function, so the shared-intake
    and drain wiring under test is the one that runs in production. Only the
    repository objects it drives are supplied here: the GitHub transport is
    already stubbed on each reviewer, so `run_repositories` is replaced by a
    loop over them in the order a scan would visit the configured repositories.
    """
    dispatcher = reviewers[0].dispatcher if reviewers else None
    by_repository = {run.repository: run for run in reviewers}

    def fake_run_repositories(automation_type, conversation=None, dispatcher=None):
        for source in by_repository.values():
            run = object.__new__(automation_type)
            run.__dict__.update(source.__dict__)
            run.run()

    original = module.run_repositories
    module.run_repositories = fake_run_repositories
    try:
        module.run_scan(dispatcher)
    finally:
        module.run_repositories = original
        module.PullRequestReviewer.scan_intake = None


def _eligible_pr(number, sha, request_id, created_at, *, checks=()):
    """An open non-draft PR holding an outstanding all-hands-bot request."""
    return {
        "number": number,
        "head": {"sha": sha},
        "labels": [],
        "draft": False,
        "requested_reviewers": [{"login": "all-hands-bot"}],
        "_request": {
            "id": request_id,
            "event": "review_requested",
            "created_at": created_at,
            "requested_reviewer": {"login": "all-hands-bot"},
        },
        "_checks": list(checks),
    }


def _unrequested_pr(
    number,
    sha,
    *,
    created_at="2026-01-01T00:00:00Z",
    checks=(),
    workflows=(),
    reviews=(),
    author="someone",
):
    """An open non-draft PR nobody requested, as the unrequested scan sees it."""
    return {
        "number": number,
        "head": {"sha": sha},
        "labels": [],
        "draft": False,
        "created_at": created_at,
        "user": {"login": author},
        "requested_reviewers": [],
        "_checks": list(checks),
        "_workflows": list(workflows),
        "_reviews": list(reviews),
    }


def _wire_scan(run, prs, repository_id):
    """Point one reviewer at its PRs, requests, reviews, and runs."""
    by_number = {pr["number"]: pr for pr in prs}

    def gh(method, path, body=None):
        if path == "":
            return {"id": repository_id}
        if method == "GET" and path.startswith("/pulls/"):
            return by_number[int(path.split("/")[2])]
        if method == "POST" and path.endswith("/comments"):
            return {"id": 1234}
        return {}

    def gh_pages(path):
        if path.startswith("/pulls?"):
            return list(prs)
        if path.endswith("/reviews"):
            return list(by_number[int(path.split("/")[2])].get("_reviews", []))
        if path.endswith("/events"):
            request = by_number[int(path.split("/")[2])].get("_request")
            return [request] if request else []
        return []

    def check_runs(sha):
        for pr in by_number.values():
            if pr["head"]["sha"] == sha:
                return [
                    {
                        "name": name,
                        "status": status,
                        "conclusion": conclusion,
                        "head_sha": sha,
                    }
                    for name, status, conclusion in pr.get("_checks", [])
                ]
        return []

    def workflow_runs(sha):
        for pr in by_number.values():
            if pr["head"]["sha"] == sha:
                return [
                    {
                        "name": name,
                        "status": status,
                        "conclusion": conclusion,
                        "head_sha": sha,
                        "id": run_id,
                        "check_suite_id": suite_id,
                        "workflow_id": workflow_id,
                        "run_started_at": "",
                        "created_at": "",
                    }
                    for name, status, conclusion, run_id, suite_id, workflow_id in pr.get(
                        "_workflows", []
                    )
                ]
        return []

    run.gh = gh
    run.gh_pages = gh_pages
    run.check_runs = check_runs
    run.workflow_runs = workflow_runs


def test_one_scan_starts_at_most_the_maximum_and_a_later_scan_reaches_the_rest(
    tmp_path, monkeypatch
):
    """Three eligible PRs across two repositories, default maximum of two."""
    module, (one, two) = _scan_reviewers(
        tmp_path, monkeypatch, ["owner/one", "owner/two"]
    )
    # Oldest request first: #5 (Jan 1), then #2 (Jan 2), then #9 (Jan 3).
    _wire_scan(
        one,
        [
            _eligible_pr(5, "head-5", 500, "2026-01-01T00:00:00Z"),
            _eligible_pr(9, "head-9", 900, "2026-01-03T00:00:00Z"),
        ],
        101,
    )
    _wire_scan(two, [_eligible_pr(2, "head-2", 200, "2026-01-02T00:00:00Z")], 102)

    _run_scan(module, [one, two])

    started = set(one.dispatcher.calls) | set(two.dispatcher.calls)
    assert started == {("101:pr:5", "500:head-5"), ("102:pr:2", "200:head-2")}
    assert one.dispatcher.seen == {"101:pr:5": "500:head-5"}
    assert two.dispatcher.seen == {"102:pr:2": "200:head-2"}

    # A later scan sees the first two as already-running and reaches the rest.
    _run_scan(module, [one, two])

    assert one.dispatcher.seen == {
        "101:pr:5": "500:head-5",
        "101:pr:9": "900:head-9",
    }
    assert two.dispatcher.seen == {"102:pr:2": "200:head-2"}


def test_a_pending_check_candidate_consumes_no_slot_and_does_not_block_the_queue(
    tmp_path, monkeypatch
):
    """The oldest candidate is waiting on CI, so the next two drain instead."""
    module, (one, two) = _scan_reviewers(
        tmp_path, monkeypatch, ["owner/one", "owner/two"]
    )
    _wire_scan(
        one,
        [
            # Oldest request, but its exact head still has a queued check.
            _eligible_pr(
                5,
                "head-5",
                500,
                "2026-01-01T00:00:00Z",
                checks=[("slow-e2e", "queued", None)],
            ),
            _eligible_pr(9, "head-9", 900, "2026-01-03T00:00:00Z"),
        ],
        101,
    )
    _wire_scan(two, [_eligible_pr(2, "head-2", 200, "2026-01-02T00:00:00Z")], 102)

    _run_scan(module, [one, two])

    assert one.dispatcher.seen == {"101:pr:9": "900:head-9"}
    assert two.dispatcher.seen == {"102:pr:2": "200:head-2"}


def test_non_dispatching_work_still_runs_after_the_maximum_is_reached(
    tmp_path, monkeypatch
):
    """A blocked candidate past the maximum still gets its gate explanation."""
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"])
    _wire_scan(
        one,
        [
            _eligible_pr(5, "head-5", 500, "2026-01-01T00:00:00Z"),
            _eligible_pr(6, "head-6", 600, "2026-01-02T00:00:00Z"),
            _eligible_pr(
                7,
                "head-7",
                700,
                "2026-01-04T00:00:00Z",
                checks=[("ci", "completed", "failure")],
            ),
        ],
        101,
    )
    one.gh = Mock(side_effect=one.gh)

    _run_scan(module, [one])

    # Only the two oldest start; the blocked third consumes no slot.
    assert set(one.dispatcher.seen) == {"101:pr:5", "101:pr:6"}
    posted = [call for call in one.gh.call_args_list if call.args[0] == "POST"]
    assert len(posted) == 1
    assert "<!-- openhands-review-gate:blocked:head-7 -->" in posted[0].args[2]["body"]


def test_a_failing_dispatch_is_reported_without_consuming_a_slot_or_aborting(
    tmp_path, monkeypatch
):
    """The oldest dispatch raises; the next candidates still get their turn."""
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"])
    _wire_scan(
        one,
        [
            _eligible_pr(5, "head-5", 500, "2026-01-01T00:00:00Z"),
            _eligible_pr(6, "head-6", 600, "2026-01-02T00:00:00Z"),
            _eligible_pr(7, "head-7", 700, "2026-01-03T00:00:00Z"),
        ],
        101,
    )

    def deliver(*, subject, delivery, prompt):
        if subject == "101:pr:5":
            raise RuntimeError("agent server unavailable")
        one.dispatcher.seen[subject] = delivery
        return {"disposition": "created", "conversation_id": subject}

    one.dispatcher.deliver = deliver

    with pytest.raises(RuntimeError, match="#5"):
        _run_scan(module, [one])

    assert set(one.dispatcher.seen) == {"101:pr:6", "101:pr:7"}


def test_the_maximum_is_configurable_through_the_rendered_config(tmp_path, monkeypatch):
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"], max_new=1)
    _wire_scan(
        one,
        [
            _eligible_pr(5, "head-5", 500, "2026-01-01T00:00:00Z"),
            _eligible_pr(6, "head-6", 600, "2026-01-02T00:00:00Z"),
        ],
        101,
    )

    _run_scan(module, [one])

    assert set(one.dispatcher.seen) == {"101:pr:5"}


def test_the_rendered_config_defaults_the_maximum_to_two(tmp_path, monkeypatch):
    """An unset max_new_per_run still bounds a scheduled scan to two."""
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"])
    _wire_scan(
        one,
        [
            _eligible_pr(5, "head-5", 500, "2026-01-01T00:00:00Z"),
            _eligible_pr(6, "head-6", 600, "2026-01-02T00:00:00Z"),
            _eligible_pr(7, "head-7", 700, "2026-01-03T00:00:00Z"),
        ],
        101,
    )

    _run_scan(module, [one])

    assert module.workflow.MAX_NEW_PER_RUN == 2
    assert set(one.dispatcher.seen) == {"101:pr:5", "101:pr:6"}


def test_the_explicit_request_event_path_is_not_bounded(tmp_path, monkeypatch):
    """Only the scheduled scan's new conversations are bounded."""
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"])
    monkeypatch.setenv(
        "AUTOMATION_EVENT_PAYLOAD",
        json.dumps(
            {
                "automation_id": "automation",
                "event": {
                    "payload": {
                        "action": "review_requested",
                        "repository": {"full_name": "owner/one"},
                        "pull_request": {"number": 5},
                        "requested_reviewer": {"login": "all-hands-bot"},
                    }
                },
            }
        ),
    )
    pr = {"number": 5, "head": {"sha": "head-5"}, "labels": []}
    one.gh = Mock(side_effect=[{"id": 101}, pr])
    one.gh_pages = lambda path: (
        [
            {
                "id": 500,
                "event": "review_requested",
                "created_at": "2026-01-01T00:00:00Z",
                "requested_reviewer": {"login": "all-hands-bot"},
            }
        ]
        if path.endswith("/events")
        else []
    )
    one.workflow_runs = lambda sha: []

    one.run()

    assert one.dispatcher.seen == {"101:pr:5": "500:head-5"}


def test_the_rendered_config_reads_a_positive_max_new_per_run(tmp_path, monkeypatch):
    """The rendered config overrides the default, following the key the other
    automations already use."""
    module = worker("github-pr-reviewer", tmp_path, monkeypatch)
    (tmp_path / "github-pr-reviewer" / "config.json").write_text(
        json.dumps(
            {
                "repos": ["owner/one"],
                "max_new_per_run": 3,
                "github_token_secret": "GITHUB_TOKEN",
            }
        )
    )

    config = module.workflow.load_config(tmp_path / "github-pr-reviewer")

    assert config["max_new_per_run"] == 3


@pytest.mark.parametrize("bad", [0, -1, True, "2"])
def test_the_rendered_config_rejects_a_misbehaving_max_new_per_run(
    tmp_path, monkeypatch, bad
):
    """A non-positive or non-integer bound is a hard error, not a coercion: the
    alternative is a scan that either never starts or starts `True` conversations."""
    module = worker("github-pr-reviewer", tmp_path, monkeypatch)
    (tmp_path / "github-pr-reviewer" / "config.json").write_text(
        json.dumps({"repos": ["owner/one"], "max_new_per_run": bad})
    )

    with pytest.raises(SystemExit):
        module.workflow.load_config(tmp_path / "github-pr-reviewer")

# --------------------------------------------------------------------------- #
# Unrequested scheduled scan: an open, non-draft PR with a green current head and
# no all-hands-bot review is reviewed without any request or trigger label.
# --------------------------------------------------------------------------- #


def test_unrequested_scan_reviews_a_green_pr_with_no_request_or_label(
    tmp_path, monkeypatch
):
    """The core new behavior: a green PR nobody requested starts a review."""
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"])
    _wire_scan(one, [_unrequested_pr(5, "head-5")], 101)

    _run_scan(module, [one])

    assert one.dispatcher.seen == {"101:pr:5": "scan:owner/one:5:head-5"}


def test_unrequested_scan_blocks_a_failed_zero_job_workflow(tmp_path, monkeypatch):
    """A green check-run rollup with a failed zero-job workflow still blocks.

    The workflow failed before creating any check run, so the commit's rollup is
    green while the Actions run is `completed`/`failure`. The gate must read the
    workflow run and start nothing - and, because nobody requested this PR, it
    must do so without posting a managed gate comment.
    """
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"])
    _wire_scan(
        one,
        [
            _unrequested_pr(
                5,
                "head-5",
                checks=(("pr-title", "completed", "success"),),
                workflows=(("Tests", "completed", "failure", 3, 3003, 236324519),),
            )
        ],
        101,
    )
    one.gh = Mock(side_effect=one.gh)

    _run_scan(module, [one])

    assert one.dispatcher.seen == {}
    assert [call for call in one.gh.call_args_list if call.args[0] == "POST"] == []


def test_unrequested_scan_waits_on_a_pending_workflow(tmp_path, monkeypatch):
    """A current-head workflow still in progress makes the unrequested head wait.

    The unrequested head starts no conversation and, being unrequested, gets no
    managed gate comment either.
    """
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"])
    _wire_scan(
        one,
        [
            _unrequested_pr(
                5,
                "head-5",
                workflows=(("Tests", "in_progress", None, 4, 4004, 236324519),),
            )
        ],
        101,
    )
    one.gh = Mock(side_effect=one.gh)

    _run_scan(module, [one])

    assert one.dispatcher.seen == {}
    assert [call for call in one.gh.call_args_list if call.args[0] == "POST"] == []


def test_unrequested_scan_does_not_duplicate_across_repeated_scans(
    tmp_path, monkeypatch
):
    """The stable repository/PR/head key makes a repeat scan a no-op."""
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"])
    _wire_scan(one, [_unrequested_pr(5, "head-5")], 101)

    _run_scan(module, [one])
    _run_scan(module, [one])

    assert one.dispatcher.calls == [
        ("101:pr:5", "scan:owner/one:5:head-5"),
        ("101:pr:5", "scan:owner/one:5:head-5"),
    ]
    assert one.dispatcher.seen == {"101:pr:5": "scan:owner/one:5:head-5"}


def test_unrequested_scan_reviews_a_changed_head_again_under_a_new_key(
    tmp_path, monkeypatch
):
    """A new head is eligible again and reviewed once under its own key."""
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"])
    _wire_scan(one, [_unrequested_pr(5, "head-5")], 101)
    _run_scan(module, [one])

    # The PR is pushed to a new head, so the old key no longer matches.
    _wire_scan(one, [_unrequested_pr(5, "head-6")], 101)
    _run_scan(module, [one])

    assert one.dispatcher.seen == {"101:pr:5": "scan:owner/one:5:head-6"}
    assert one.dispatcher.calls[-1] == ("101:pr:5", "scan:owner/one:5:head-6")


def test_unrequested_scan_bound_spans_repositories_with_explicit_priority(
    tmp_path, monkeypatch
):
    """The cap is global; an explicit request outranks unrequested candidates.

    Repository `owner/one` holds an unrequested PR older than `owner/two`'s
    explicit request. The request must win the single slot even though it is
    younger, because explicit requests are ordered first.
    """
    module, (one, two) = _scan_reviewers(
        tmp_path, monkeypatch, ["owner/one", "owner/two"], max_new=1
    )
    _wire_scan(
        one, [_unrequested_pr(5, "head-5", created_at="2026-01-01T00:00:00Z")], 101
    )
    _wire_scan(two, [_eligible_pr(2, "head-2", 200, "2026-01-05T00:00:00Z")], 102)

    _run_scan(module, [one, two])

    assert one.dispatcher.seen == {}
    assert two.dispatcher.seen == {"102:pr:2": "200:head-2"}


def test_unrequested_scan_reviews_the_oldest_eligible_prs_under_the_cap(
    tmp_path, monkeypatch
):
    """With no requests, the cap starts the oldest unrequested PRs first."""
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"])
    _wire_scan(
        one,
        [
            _unrequested_pr(9, "head-9", created_at="2026-01-03T00:00:00Z"),
            _unrequested_pr(5, "head-5", created_at="2026-01-01T00:00:00Z"),
            _unrequested_pr(7, "head-7", created_at="2026-01-02T00:00:00Z"),
        ],
        101,
    )

    _run_scan(module, [one])

    assert one.dispatcher.seen == {
        "101:pr:5": "scan:owner/one:5:head-5",
        "101:pr:7": "scan:owner/one:7:head-7",
    }


def test_unrequested_scan_reconciles_a_completed_review_and_hands_off(
    tmp_path, monkeypatch
):
    """A head that already carries a completed review is not re-dispatched.

    The review is found on the current head, so the scan reconciles it and runs
    the existing maintainer handoff instead of starting a second conversation.
    """
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"])
    _wire_scan(
        one,
        [
            _unrequested_pr(
                5,
                "head-5",
                reviews=[
                    {
                        "body": "Review body\n\n✅ APPROVED",
                        "commit_id": "head-5",
                        "submitted_at": "2026-01-02T00:00:00Z",
                        "user": {"login": "all-hands-bot"},
                    }
                ],
            )
        ],
        101,
    )
    one.config["maintainers"] = "neubig"
    handoff = Mock(return_value="neubig")
    monkeypatch.setattr(module, "request_maintainer_review", handoff)

    _run_scan(module, [one])

    assert one.dispatcher.seen == {}
    handoff.assert_called_once()


def test_unrequested_scan_still_gates_a_blocked_pr_past_the_cap(
    tmp_path, monkeypatch
):
    """An ineligible unrequested PR past the cap consumes no slot and stays silent.

    Two green unrequested PRs fill the cap, and a third blocked one - older than
    them - is skipped without consuming a slot, without aborting the scan, and
    without a managed gate comment, because nobody requested it.
    """
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"])
    _wire_scan(
        one,
        [
            _unrequested_pr(
                5,
                "head-5",
                created_at="2026-01-01T00:00:00Z",
                checks=(("ci", "completed", "failure"),),
            ),
            _unrequested_pr(6, "head-6", created_at="2026-01-02T00:00:00Z"),
            _unrequested_pr(7, "head-7", created_at="2026-01-03T00:00:00Z"),
        ],
        101,
    )
    one.gh = Mock(side_effect=one.gh)

    _run_scan(module, [one])

    assert set(one.dispatcher.seen) == {"101:pr:6", "101:pr:7"}
    assert [call for call in one.gh.call_args_list if call.args[0] == "POST"] == []


def test_an_explicit_request_still_gets_its_managed_gate_comment(
    tmp_path, monkeypatch
):
    """The managed comment answers an explicit request, red or pending.

    Suppressing the unrequested comment must not silence the explanation for the
    request a caller actually made: an outstanding request whose head is failing
    still gets its blocked gate comment.
    """
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"])
    _wire_scan(
        one,
        [
            _eligible_pr(
                5,
                "head-5",
                500,
                "2026-01-01T00:00:00Z",
                checks=(("ci", "completed", "failure"),),
            )
        ],
        101,
    )
    one.gh = Mock(side_effect=one.gh)

    _run_scan(module, [one])

    assert one.dispatcher.seen == {}
    posted = [call for call in one.gh.call_args_list if call.args[0] == "POST"]
    assert len(posted) == 1
    assert "<!-- openhands-review-gate:blocked:head-5 -->" in posted[0].args[2]["body"]


def test_unrequested_scan_marks_a_self_authored_pr_for_the_comment_verdict(
    tmp_path, monkeypatch
):
    """A bot-authored PR is told to use the non-approval verdict path.

    GitHub ignores a self-review request, so the reviewer must publish the clean
    review as a `COMMENT` event that keeps the approved verdict instead of being
    skipped.
    """
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"])
    _wire_scan(one, [_unrequested_pr(5, "head-5", author="all-hands-bot")], 101)

    _run_scan(module, [one])

    assert one.dispatcher.seen == {"101:pr:5": "scan:owner/one:5:head-5"}
    prompt = one.dispatcher.prompts[-1]
    assert "authored by the configured reviewer account" in prompt
    assert "keep the approved verdict" in prompt


# --------------------------------------------------------------------------- #
# Bounded rotating scan window: each scheduled scan examines a bounded slice of
# the unrequested backlog, remembers its position in the Automation KV store, and
# resumes there on the next scan. Explicit requests are never subject to it.
# --------------------------------------------------------------------------- #


def _kv_store(module, monkeypatch):
    """Back the scan cursor with an in-memory stand-in for the Automation KV store.

    The real store is an HTTP service; this reproduces the contract the cursor
    relies on - a per-key `GET` that misses with None and a `PUT` that replaces
    the value - so the shipped `ScanCursor` persists and reloads through it.
    """
    values = {}
    monkeypatch.setattr(module.workflow, "_kv_available", lambda: True)
    monkeypatch.setattr(
        module.workflow, "_kv_get", lambda key: values.get(key)
    )

    def put(key, value):
        values[key] = value

    monkeypatch.setattr(module.workflow, "_kv_set", put)
    return values


def _many_unrequested(count, *, checks=()):
    """`count` open, non-draft PRs nobody requested, numbered 1..count."""
    return [
        _unrequested_pr(
            number,
            f"head-{number}",
            created_at=f"2026-01-{number:02d}T00:00:00Z",
            checks=checks,
        )
        for number in range(1, count + 1)
    ]


def _examined(run):
    """The PR numbers a scan actually dispatched, in call order."""
    return [int(subject.split(":")[-1]) for subject, _ in run.dispatcher.calls]


def test_scan_examines_a_bounded_rotating_window_of_unrequested_prs(
    tmp_path, monkeypatch
):
    """Each scan covers the next slice, so the whole backlog is reached in turn."""
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"], max_new=5)
    monkeypatch.setattr(module, "SCAN_WINDOW", 2)
    _kv_store(module, monkeypatch)
    _wire_scan(one, _many_unrequested(5), 101)

    _run_scan(module, [one])
    assert _examined(one) == [1, 2]

    _run_scan(module, [one])
    assert _examined(one)[-2:] == [3, 4]

    _run_scan(module, [one])
    assert _examined(one)[-1:] == [5]

    # Past the end the window wraps, so the backlog keeps rotating.
    _run_scan(module, [one])
    assert _examined(one)[-2:] == [1, 2]


def test_the_scan_position_is_persisted_per_repository_in_the_kv_store(
    tmp_path, monkeypatch
):
    """The cursor is written under a per-repository key, so a later run resumes.

    A cron run is a fresh process, so the only way the window survives is the
    Automation KV store; this pins the key and the value the next scan reads.
    """
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"], max_new=5)
    monkeypatch.setattr(module, "SCAN_WINDOW", 2)
    values = _kv_store(module, monkeypatch)
    _wire_scan(one, _many_unrequested(5), 101)

    _run_scan(module, [one])

    assert values == {"review-scan:owner__one": {"cursor": 2}}


def test_explicit_requests_are_examined_regardless_of_the_rotation_window(
    tmp_path, monkeypatch
):
    """An explicit request is never skipped because the window sits elsewhere.

    The cursor points at the last unrequested PR, but the explicit request on
    PR #1 is still examined and dispatched, because a caller asked for it.
    """
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"], max_new=5)
    monkeypatch.setattr(module, "SCAN_WINDOW", 1)
    values = _kv_store(module, monkeypatch)
    # Only PR #1 holds a request; the rest are unrequested and the window sits on
    # the last of them, so the request must still be examined.
    _wire_scan(
        one,
        [_eligible_pr(1, "head-1", 100, "2026-01-01T00:00:00Z")]
        + _many_unrequested(4)[1:],
        101,
    )
    values["review-scan:owner__one"] = {"cursor": 2}

    _run_scan(module, [one])

    assert one.dispatcher.seen == {
        "101:pr:1": "100:head-1",
        "101:pr:4": "scan:owner/one:4:head-4",
    }


def test_unrequested_red_and_pending_prs_post_no_gate_comments(
    tmp_path, monkeypatch
):
    """A scan over a large unrequested backlog posts no managed gate comments.

    This is the storm the canary exposed: every red or pending head used to get a
    comment. Unrequested heads now stay silent; only an explicit request gets the
    managed explanation.
    """
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"], max_new=5)
    monkeypatch.setattr(module, "SCAN_WINDOW", 20)
    _wire_scan(
        one,
        [
            _unrequested_pr(
                5, "head-5", checks=(("ci", "completed", "failure"),)
            ),
            _unrequested_pr(
                6, "head-6", checks=(("slow-e2e", "in_progress", None),)
            ),
            _unrequested_pr(
                7, "head-7", checks=(("ci", "completed", "success"),)
            ),
        ],
        101,
    )
    one.gh = Mock(side_effect=one.gh)

    _run_scan(module, [one])

    assert [call for call in one.gh.call_args_list if call.args[0] == "POST"] == []
    # The green unrequested head still reaches the bounded dispatch queue.
    assert one.dispatcher.seen == {"101:pr:7": "scan:owner/one:7:head-7"}


def test_scan_reads_a_bounded_number_of_pull_requests_per_repository(
    tmp_path, monkeypatch
):
    """A scan reads one list page plus at most one head per examined candidate.

    A full scan would issue one full pull read per open PR - the API cost that
    made the canary time out. With a window of 10 over 40 PRs, only the 10 in the
    window are read.
    """
    module, (one,) = _scan_reviewers(tmp_path, monkeypatch, ["owner/one"], max_new=5)
    monkeypatch.setattr(module, "SCAN_WINDOW", 10)
    _kv_store(module, monkeypatch)
    _wire_scan(one, _many_unrequested(40), 101)

    list_reads = []
    original_pages = one.gh_pages

    def counting_pages(path):
        if path.startswith("/pulls?"):
            list_reads.append(path)
        return original_pages(path)

    one.gh_pages = counting_pages
    one.gh = Mock(side_effect=one.gh)

    _run_scan(module, [one])

    full_reads = [
        call for call in one.gh.call_args_list
        if call.args[0] == "GET" and str(call.args[1]).startswith("/pulls/")
    ]
    assert len(list_reads) == 1
    assert len(full_reads) == 10
