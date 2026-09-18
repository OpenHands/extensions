"""Contract tests for independent triage delivery."""

from unittest.mock import Mock

from github_automation_helpers import worker


def _triage(tmp_path, monkeypatch, issues):
    module = worker("github-issue-triage", tmp_path, monkeypatch)
    cls = module.IssueTriage
    run = object.__new__(cls)
    run.repository = "owner/repo"
    run.token_name = "GITHUB_PERSONAL_ACCESS_TOKEN"
    run.dispatcher = Mock()
    run.open_issues = lambda: issues
    run.dependencies_complete = lambda issue: True
    run.gh = lambda method, path, body=None: {"id": 9876}
    run.gh_pages = lambda path: []
    return module, run


def test_triage_submits_each_changed_issue_as_agent_work(tmp_path, monkeypatch):
    issues = [
        {"number": 2, "title": "Second", "body": "B", "labels": []},
        {"number": 1, "title": "First", "body": "A", "labels": []},
    ]
    _module, run = _triage(tmp_path, monkeypatch, issues)
    submit = Mock(
        side_effect=lambda **kwargs: {
            "disposition": "created",
            "conversation_id": kwargs["subject"],
        }
    )
    run.dispatcher.deliver = submit

    run.run()

    assert [call.kwargs["subject"] for call in submit.call_args_list] == [
        "9876:issue:1",
        "9876:issue:2",
    ]
    assert "Do not implement code" in submit.call_args_list[0].kwargs["prompt"]
    assert "GITHUB_PERSONAL_ACCESS_TOKEN" in submit.call_args_list[0].kwargs["prompt"]
    assert (
        "The following comments and acceptance criteria were added by the "
        "OpenHands AI agent." in submit.call_args_list[0].kwargs["prompt"]
    )
    assert (
        "closest existing or adjacent implementation"
        in submit.call_args_list[0].kwargs["prompt"]
    )
    assert "Add `ready-for-dev` only after" in submit.call_args_list[0].kwargs["prompt"]


def test_triage_continues_after_one_submission_fails(tmp_path, monkeypatch):
    issues = [
        {"number": 1, "title": "First", "body": "A", "labels": []},
        {"number": 2, "title": "Second", "body": "B", "labels": []},
    ]
    _module, run = _triage(tmp_path, monkeypatch, issues)
    submit = Mock(
        side_effect=[
            RuntimeError("unavailable"),
            {"disposition": "created", "conversation_id": "second"},
        ]
    )
    run.dispatcher.deliver = submit

    run.run()

    assert [call.kwargs["subject"] for call in submit.call_args_list] == [
        "9876:issue:1",
        "9876:issue:2",
    ]


def test_triage_checks_ready_issue_but_skips_blocked_and_unchanged_issues(
    tmp_path, monkeypatch
):
    issues = [
        {
            "number": 1,
            "title": "Ready",
            "body": "",
            "labels": [{"name": "ready-for-dev"}],
        },
        {"number": 2, "title": "Blocked", "body": "", "labels": []},
        {"number": 3, "title": "Unchanged", "body": "", "labels": []},
    ]
    module, run = _triage(tmp_path, monkeypatch, issues)
    run.dependencies_complete = lambda issue: issue["number"] != 2
    unchanged_marker = module.hashlib.sha256(
        module.json.dumps(["Unchanged", "", []], sort_keys=True).encode()
    ).hexdigest()
    run.gh_pages = lambda path: (
        [
            {
                "id": 10,
                "body": f"<!-- triage-source:{unchanged_marker} -->",
            }
        ]
        if path == "/issues/3/comments"
        else []
    )
    submit = Mock(return_value={"disposition": "created", "conversation_id": "ready"})
    run.dispatcher.deliver = submit

    run.run()

    assert [call.kwargs["subject"] for call in submit.call_args_list] == [
        "9876:issue:1"
    ]


def test_triage_passes_human_discussion_and_stale_bot_comment(tmp_path, monkeypatch):
    issue = {
        "number": 7,
        "title": "Improve behavior",
        "body": "Original request",
        "labels": [{"name": "enhancement"}],
    }
    _module, run = _triage(tmp_path, monkeypatch, [issue])
    run.gh_pages = lambda path: [
        {
            "id": 101,
            "user": {"login": "maintainer"},
            "created_at": "2026-09-18T00:00:00Z",
            "updated_at": "2026-09-18T00:00:00Z",
            "body": "Keep compatibility with saved configurations.",
        },
        {
            "id": 102,
            "user": {"login": "all-hands-bot"},
            "created_at": "2026-09-18T00:01:00Z",
            "updated_at": "2026-09-18T00:01:00Z",
            "body": "Old triage\n<!-- triage-source:old -->",
        },
    ]
    run.dispatcher.deliver.return_value = {
        "disposition": "resumed",
        "conversation_id": "triage",
    }

    run.run()

    prompt = run.dispatcher.deliver.call_args.kwargs["prompt"]
    assert '"author": "maintainer"' in prompt
    assert "Keep compatibility with saved configurations." in prompt
    assert '"id": 102' in prompt
    assert "Old triage" not in prompt
    assert "Delete prior comments listed as automated triage comments" in prompt
