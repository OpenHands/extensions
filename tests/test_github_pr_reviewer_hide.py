"""Tests for the hide-previous-automation-comments behaviour.

Each review cycle posts a *pair*: an acknowledgement issue comment ("OpenHands
is reviewing this PR") and a review result — an issue comment and/or a PR review
object. When a new review completes, only *previous* pairs must be hidden; the
current cycle's pair stays visible.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


def _load_main_module():
    script_path = (
        Path(__file__).parent.parent
        / "skills"
        / "github-pr-reviewer"
        / "scripts"
        / "main.py"
    )
    spec = importlib.util.spec_from_file_location("ghpr_main", script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["ghpr_main"] = module
    spec.loader.exec_module(module)
    return module


main = _load_main_module()

DISCLOSURE = main._AI_DISCLOSURE
ACK_BODY = (
    "🤖 **OpenHands is reviewing this PR.**\n\n"
    "Trigger label: `openhands-review`\n"
    "Head commit: `abc123`\n"
    "View the conversation: http://example/conv\n\n"
    + DISCLOSURE
)
RESULT_BODY = "Looks good overall.\n\n✅ APPROVED\n\n" + DISCLOSURE
NON_AUTOMATION = "Great PR, ship it!"


def _issue_comment(node_id, body, minimized=False):
    return {"id": node_id, "body": body, "isMinimized": minimized}


def _review(node_id, body, created_at, comments=None, minimized=False):
    return {
        "id": node_id,
        "body": body,
        "isMinimized": minimized,
        "state": "COMMENTED",
        "createdAt": created_at,
        "comments": {"nodes": comments or []},
    }


def _review_comment(node_id, body, minimized=False):
    return {"id": node_id, "body": body, "isMinimized": minimized}


@pytest.fixture
def minimized_ids():
    """Records the node IDs passed to _minimize_comment."""
    ids: list[str] = []

    def _fake_minimize(token, node_id, reason="OUTDATED"):
        ids.append(node_id)
        return True

    with patch.object(main, "_minimize_comment", side_effect=_fake_minimize):
        with patch.object(main, "_list_issue_comments", return_value=[]):
            with patch.object(main, "_list_pr_reviews", return_value=[]):
                yield ids


def _run_hide(minimized_ids, issue_comments, reviews, exclude):
    with patch.object(main, "_list_issue_comments", return_value=issue_comments):
        with patch.object(main, "_list_pr_reviews", return_value=reviews):
            with patch.object(
                main, "_minimize_comment", side_effect=lambda t, n, r="OUTDATED": minimized_ids.append(n) or True
            ):
                main._hide_previous_automation_comments(
                    "tok", "owner/repo", 1, exclude_node_ids=exclude
                )


def test_hides_previous_ack_and_result_comments_but_keeps_current_pair(minimized_ids):
    """Two cycles: hide cycle 1's ack + result; keep cycle 2's ack + result."""
    comments = [
        _issue_comment("ack_1", ACK_BODY),
        _issue_comment("result_1", RESULT_BODY),
        _issue_comment("ack_2", ACK_BODY),
        _issue_comment("result_2", RESULT_BODY),
    ]
    _run_hide(minimized_ids, comments, [], exclude={"ack_2", "result_2"})

    assert sorted(minimized_ids) == ["ack_1", "result_1"]
    assert "ack_2" not in minimized_ids
    assert "result_2" not in minimized_ids


def test_keeps_current_review_object_hides_previous_review_objects(minimized_ids):
    """The most recent automation review object is kept; older ones are hidden."""
    reviews = [
        _review("rev_1", RESULT_BODY, "2026-01-01T00:00:00Z",
                comments=[_review_comment("rc_1", RESULT_BODY)]),
        _review("rev_2", RESULT_BODY, "2026-02-01T00:00:00Z",
                comments=[_review_comment("rc_2", RESULT_BODY)]),
    ]
    _run_hide(minimized_ids, [], reviews, exclude=set())

    # rev_2 is the most recent → kept; rev_1 + its inline comment → hidden
    assert "rev_1" in minimized_ids
    assert "rc_1" in minimized_ids
    assert "rev_2" not in minimized_ids
    assert "rc_2" not in minimized_ids


def test_single_review_object_is_never_hidden(minimized_ids):
    """If there's only one automation review object, it is the current one."""
    reviews = [
        _review("rev_only", RESULT_BODY, "2026-03-01T00:00:00Z",
                comments=[_review_comment("rc_only", RESULT_BODY)]),
    ]
    _run_hide(minimized_ids, [], reviews, exclude=set())

    assert minimized_ids == []


def test_current_ack_comment_is_not_hidden(minimized_ids):
    """The current cycle's acknowledgement comment must survive."""
    comments = [
        _issue_comment("ack_old", ACK_BODY),
        _issue_comment("ack_current", ACK_BODY),
        _issue_comment("result_current", RESULT_BODY),
    ]
    _run_hide(minimized_ids, comments, [], exclude={"ack_current", "result_current"})

    assert minimized_ids == ["ack_old"]
    assert "ack_current" not in minimized_ids
    assert "result_current" not in minimized_ids


def test_already_minimized_content_is_skipped(minimized_ids):
    comments = [
        _issue_comment("ack_1", ACK_BODY, minimized=True),
        _issue_comment("ack_2", ACK_BODY),
        _issue_comment("result_2", RESULT_BODY),
    ]
    _run_hide(minimized_ids, comments, [], exclude={"ack_2", "result_2"})

    assert minimized_ids == []


def test_non_automation_comments_are_never_hidden(minimized_ids):
    comments = [
        _issue_comment("human_1", NON_AUTOMATION),
        _issue_comment("ack_2", ACK_BODY),
        _issue_comment("result_2", RESULT_BODY),
    ]
    _run_hide(minimized_ids, comments, [], exclude={"ack_2", "result_2"})

    assert minimized_ids == []


def test_no_exclude_keeps_latest_review_object(minimized_ids):
    """With no tracked issue-comment excludes, the latest review object is
    still preserved (it's assumed to be the current cycle's)."""
    reviews = [
        _review("rev_1", RESULT_BODY, "2026-01-01T00:00:00Z"),
        _review("rev_2", RESULT_BODY, "2026-02-01T00:00:00Z"),
    ]
    _run_hide(minimized_ids, [], reviews, exclude=None)

    assert "rev_1" in minimized_ids
    assert "rev_2" not in minimized_ids
