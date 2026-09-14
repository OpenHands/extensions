"""Contract tests for independent triage delivery."""

import json
from unittest.mock import Mock

import pytest
from github_automation_helpers import worker


@pytest.mark.parametrize(
    "ready,criteria",
    [(True, ["One observable result"]), (False, ["Clarify account ownership"])],
)
def test_triage_preserves_labels_and_only_readies_clear_work(
    tmp_path, monkeypatch, ready, criteria
):
    cls = worker("github-issue-triage", tmp_path, monkeypatch).IssueTriage
    run = object.__new__(cls)
    issue = {
        "number": 1,
        "title": "A small feature",
        "body": "",
        "labels": [{"name": "enhancement"}],
    }
    run.open_issues = lambda: [issue]
    run.gh_pages = lambda path: []
    run.dependencies_complete = lambda issue: True
    result = {
        "ready": ready,
        "priority": "normal",
        "acceptance_criteria": criteria,
        "rationale": "Small independent change",
    }
    run.evidence = tmp_path
    run.conversation = Mock()
    run.conversation.run.side_effect = lambda **kwargs: (
        tmp_path / "triage.json"
    ).write_text(json.dumps(result))
    calls = []
    run.gh = lambda *args: calls.append(args)
    run.comment = lambda *args: calls.append(("comment", *args))

    run.run()

    updates = [call for call in calls if call[0] == "PATCH"]
    assert bool(updates) is ready
    if ready:
        assert set(updates[0][2]["labels"]) == {
            "enhancement",
            "priority:normal",
            "ready-for-dev",
        }
    assert criteria[0] in next(call[2] for call in calls if call[0] == "comment")
