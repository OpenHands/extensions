from __future__ import annotations

import importlib.util
from pathlib import Path


def load_watch_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "skills"
        / "babysit-pr"
        / "scripts"
        / "gh_pr_watch.py"
    )
    spec = importlib.util.spec_from_file_location("gh_pr_watch", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_summarize_checks_counts():
    m = load_watch_module()
    checks = [
        {"bucket": "pass", "state": "COMPLETED"},
        {"bucket": "fail", "state": "COMPLETED"},
        {"bucket": "pending", "state": "QUEUED"},
        {"bucket": "", "state": "IN_PROGRESS"},
    ]
    summary = m.summarize_checks(checks)
    assert summary == {
        "pending_count": 2,
        "failed_count": 1,
        "passed_count": 1,
        "all_terminal": False,
    }


def test_failed_runs_from_workflow_runs_filters_head_sha_and_conclusion():
    m = load_watch_module()
    runs = [
        {
            "id": 1,
            "head_sha": "abc",
            "conclusion": "success",
            "name": "Tests",
            "status": "completed",
            "html_url": "https://example.invalid/1",
        },
        {
            "id": 2,
            "head_sha": "abc",
            "conclusion": "failure",
            "name": "Lint",
            "status": "completed",
            "html_url": "https://example.invalid/2",
        },
        {
            "id": 3,
            "head_sha": "def",
            "conclusion": "failure",
            "name": "Other",
            "status": "completed",
            "html_url": "https://example.invalid/3",
        },
    ]

    failed = m.failed_runs_from_workflow_runs(runs, head_sha="abc")
    assert failed == [
        {
            "conclusion": "failure",
            "html_url": "https://example.invalid/2",
            "run_id": 2,
            "status": "completed",
            "workflow_name": "Lint",
        }
    ]


def test_recommend_actions_ready_to_merge():
    m = load_watch_module()
    pr = {
        "closed": False,
        "merged": False,
        "mergeable": "MERGEABLE",
        "merge_state_status": "CLEAN",
        "review_decision": "",
    }
    checks_summary = {
        "all_terminal": True,
        "failed_count": 0,
        "pending_count": 0,
        "passed_count": 2,
    }
    actions = m.recommend_actions(
        pr,
        checks_summary,
        failed_runs=[],
        new_review_items=[],
        retries_used=0,
        max_retries=3,
    )
    assert actions == ["stop_ready_to_merge"]


def test_snapshot_change_key_changes_with_review_item_ids():
    m = load_watch_module()
    snapshot = {
        "pr": {
            "head_sha": "abc",
            "state": "OPEN",
            "mergeable": "MERGEABLE",
            "merge_state_status": "CLEAN",
            "review_decision": "",
        },
        "checks": {"passed_count": 1, "failed_count": 0, "pending_count": 0},
        "new_review_items": [{"kind": "review_comment", "id": "1"}],
        "actions": ["process_review_comment"],
    }
    key1 = m.snapshot_change_key(snapshot)

    snapshot["new_review_items"] = [{"kind": "review_comment", "id": "2"}]
    key2 = m.snapshot_change_key(snapshot)
    assert key1 != key2


def test_is_actionable_review_bot_login_accepts_all_hands_bot():
    m = load_watch_module()
    assert m.is_actionable_review_bot_login("all-hands-bot") is True
    assert m.is_actionable_review_bot_login("openhands-ai[bot]") is True
    assert m.is_actionable_review_bot_login("dependabot[bot]") is False


def test_normalize_review_bot_keyword_strips_bot_suffix():
    m = load_watch_module()
    assert m.normalize_review_bot_keyword("my-bot[bot]") == "my_bot"

