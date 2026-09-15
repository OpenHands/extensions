"""Contract tests for independent triage delivery."""

from unittest.mock import Mock

from github_automation_helpers import worker


def _triage(tmp_path, monkeypatch, issues):
    module = worker("github-issue-triage", tmp_path, monkeypatch)
    cls = module.IssueTriage
    run = object.__new__(cls)
    run.repository = "owner/repo"
    run.token_name = "GITHUB_PERSONAL_ACCESS_TOKEN"
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
    module, run = _triage(tmp_path, monkeypatch, issues)
    submit = Mock(
        side_effect=lambda **kwargs: {
            "disposition": "created",
            "conversation_id": kwargs["subject_key"],
        }
    )
    monkeypatch.setattr(module, "submit_subject_turn", submit)

    run.run()

    assert [call.kwargs["subject_key"] for call in submit.call_args_list] == [
        "9876:issue:1",
        "9876:issue:2",
    ]
    assert all(
        call.kwargs["source"] == "github-issue-triage" for call in submit.call_args_list
    )
    assert "Do not implement code" in submit.call_args_list[0].kwargs["turn"]
    assert "GITHUB_PERSONAL_ACCESS_TOKEN" in submit.call_args_list[0].kwargs["turn"]


def test_triage_continues_after_one_submission_fails(tmp_path, monkeypatch):
    issues = [
        {"number": 1, "title": "First", "body": "A", "labels": []},
        {"number": 2, "title": "Second", "body": "B", "labels": []},
    ]
    module, run = _triage(tmp_path, monkeypatch, issues)
    submit = Mock(
        side_effect=[
            RuntimeError("unavailable"),
            {"disposition": "created", "conversation_id": "second"},
        ]
    )
    monkeypatch.setattr(module, "submit_subject_turn", submit)

    run.run()

    assert [call.kwargs["subject_key"] for call in submit.call_args_list] == [
        "9876:issue:1",
        "9876:issue:2",
    ]


def test_triage_skips_ready_blocked_and_unchanged_issues(tmp_path, monkeypatch):
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
    marker = module.hashlib.sha256(
        module.json.dumps(["Unchanged", "", []], sort_keys=True).encode()
    ).hexdigest()
    run.gh_pages = lambda path: [{"id": 10, "body": f"<!-- triage-source:{marker} -->"}]
    submit = Mock()
    monkeypatch.setattr(module, "submit_subject_turn", submit)

    run.run()

    submit.assert_not_called()


def test_subject_turn_uses_run_scoped_capability(tmp_path, monkeypatch):
    module, _ = _triage(tmp_path, monkeypatch, [])
    monkeypatch.setenv("AUTOMATION_SUBJECT_TURN_URL", "http://automation/turns")
    monkeypatch.setenv("AUTOMATION_RUN_TOKEN", "run-token")
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read.return_value = b'{"disposition":"created"}'
    opened = Mock(return_value=response)
    monkeypatch.setattr(module, "urlopen", opened)

    result = module.submit_subject_turn(
        source="triage", subject_key="1:issue:2", turn="work", idempotency_key="3"
    )

    request = opened.call_args.args[0]
    assert request.get_header("Authorization") == "Bearer run-token"
    assert result == {"disposition": "created"}
