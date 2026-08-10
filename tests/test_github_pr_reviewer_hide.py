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


# ── Pagination of the list helpers ───────────────────────────────────────────
#
# These exercise the real _list_issue_comments / _list_pr_reviews pagination
# by faking _github_graphql at the transport layer, so the newest-first,
# stop-early, and multi-page behaviour is covered rather than mocked away.


def _issue_comments_page(nodes, has_next, cursor=None):
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "comments": {
                        "nodes": nodes,
                        "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
                    }
                }
            }
        }
    }


def _reviews_page(nodes, has_next, cursor=None):
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "reviews": {
                        "nodes": nodes,
                        "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
                    }
                }
            }
        }
    }


def test_list_issue_comments_stops_after_automation_cluster():
    """Newest-first scan walks into the automation cluster, then stops on the
    first clean page below it — it must not fetch the whole comment history."""
    pages = [
        _issue_comments_page(
            [_issue_comment("ack_2", ACK_BODY), _issue_comment("result_2", RESULT_BODY)],
            has_next=True, cursor="c1",
        ),
        _issue_comments_page(
            [_issue_comment("ack_1", ACK_BODY)],
            has_next=True, cursor="c2",
        ),
        # First page with no automation content after we've seen some → stop here.
        _issue_comments_page(
            [_issue_comment("human_old", NON_AUTOMATION)],
            has_next=True, cursor="c3",
        ),
        # Should never be fetched.
        _issue_comments_page(
            [_issue_comment("should_not_fetch", ACK_BODY)],
            has_next=True, cursor="c4",
        ),
    ]
    calls = {"n": 0}

    def _fake_graphql(token, query, variables=None):
        page = pages[calls["n"]]
        calls["n"] += 1
        return page

    with patch.object(main, "_github_graphql", side_effect=_fake_graphql):
        result = main._list_issue_comments("tok", "owner/repo", 1)

    ids = [c["id"] for c in result]
    assert calls["n"] == 3  # stopped on the clean page, did not fetch page 4
    assert "should_not_fetch" not in ids
    assert {"ack_2", "result_2", "ack_1"}.issubset(set(ids))


def test_list_issue_comments_single_page_no_next():
    """The normal PR: one small page, hasNextPage false → exactly one request."""
    pages = [
        _issue_comments_page(
            [_issue_comment("ack_2", ACK_BODY), _issue_comment("result_2", RESULT_BODY)],
            has_next=False,
        ),
    ]
    calls = {"n": 0}

    def _fake_graphql(token, query, variables=None):
        page = pages[calls["n"]]
        calls["n"] += 1
        return page

    with patch.object(main, "_github_graphql", side_effect=_fake_graphql):
        result = main._list_issue_comments("tok", "owner/repo", 1)

    assert calls["n"] == 1
    assert [c["id"] for c in result] == ["ack_2", "result_2"]


def test_list_issue_comments_graphql_error_returns_collected():
    """A GraphQL error stops the walk and returns whatever was gathered so far."""
    pages = [
        _issue_comments_page([_issue_comment("ack_2", ACK_BODY)], has_next=True, cursor="c1"),
        {"errors": [{"message": "boom"}]},
    ]
    calls = {"n": 0}

    def _fake_graphql(token, query, variables=None):
        page = pages[calls["n"]]
        calls["n"] += 1
        return page

    with patch.object(main, "_github_graphql", side_effect=_fake_graphql):
        result = main._list_issue_comments("tok", "owner/repo", 1)

    assert [c["id"] for c in result] == ["ack_2"]


def test_list_pr_reviews_paginates_all_pages():
    """Reviews have no orderBy, so the helper walks every page and lets the
    caller sort; both pages' reviews must come back."""
    pages = [
        _reviews_page(
            [_review("rev_1", RESULT_BODY, "2026-01-01T00:00:00Z")],
            has_next=True, cursor="r1",
        ),
        _reviews_page(
            [_review("rev_2", RESULT_BODY, "2026-02-01T00:00:00Z")],
            has_next=False,
        ),
    ]
    calls = {"n": 0}

    def _fake_graphql(token, query, variables=None):
        page = pages[calls["n"]]
        calls["n"] += 1
        return page

    with patch.object(main, "_github_graphql", side_effect=_fake_graphql):
        result = main._list_pr_reviews("tok", "owner/repo", 1)

    assert calls["n"] == 2
    assert {r["id"] for r in result} == {"rev_1", "rev_2"}


def test_hide_end_to_end_with_paginated_lists():
    """Full path: real _list_* pagination feeding _hide_previous_automation_comments,
    only _github_graphql and _minimize_comment faked. Previous pair hidden,
    current pair (excluded) + newest review kept."""
    minimized_ids: list[str] = []
    comment_pages = [
        _issue_comments_page(
            [
                _issue_comment("result_cur", RESULT_BODY),
                _issue_comment("ack_cur", ACK_BODY),
                _issue_comment("result_old", RESULT_BODY),
                _issue_comment("ack_old", ACK_BODY),
            ],
            has_next=False,
        ),
    ]
    review_pages = [
        _reviews_page(
            [
                _review("rev_old", RESULT_BODY, "2026-01-01T00:00:00Z",
                        comments=[_review_comment("rc_old", RESULT_BODY)]),
                _review("rev_cur", RESULT_BODY, "2026-02-01T00:00:00Z",
                        comments=[_review_comment("rc_cur", RESULT_BODY)]),
            ],
            has_next=False,
        ),
    ]

    def _fake_graphql(token, query, variables=None):
        if "reviews(" in query:
            return review_pages.pop(0)
        return comment_pages.pop(0)

    with patch.object(main, "_github_graphql", side_effect=_fake_graphql):
        with patch.object(
            main, "_minimize_comment",
            side_effect=lambda t, n, r="OUTDATED": minimized_ids.append(n) or True,
        ):
            main._hide_previous_automation_comments(
                "tok", "owner/repo", 1,
                exclude_node_ids={"result_cur", "ack_cur"},
            )

    assert set(minimized_ids) == {"ack_old", "result_old", "rev_old", "rc_old"}
    for kept in ("ack_cur", "result_cur", "rev_cur", "rc_cur"):
        assert kept not in minimized_ids
