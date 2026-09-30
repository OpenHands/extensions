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
    prompt = submit.call_args_list[0].kwargs["prompt"]
    assert "Add `ready-for-dev` only after" in prompt
    assert "Default to `priority:low`" in prompt
    assert "clear user pain" in prompt
    assert "Technical possibility, code inspection, or a synthetic/unit reproduction" in prompt
    assert "Do not invent acceptance criteria around an arbitrary choice" in prompt
    assert (
        "ask only the focused follow-up questions needed to resolve it"
        in submit.call_args_list[0].kwargs["prompt"]
    )
    prompt = submit.call_args_list[0].kwargs["prompt"]
    assert "<!-- openhands-ai-triage:start -->" in prompt
    assert "<!-- openhands-ai-triage:end -->" in prompt
    assert "Do not post a triage comment" in prompt
    assert "DECISION NEEDED" in prompt
    assert "Leave the human-owned issue body unchanged" in prompt


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


def test_triage_event_submits_only_the_named_issue(tmp_path, monkeypatch):
    issues = [
        {"number": 1, "title": "First", "body": "A", "labels": []},
        {"number": 2, "title": "Second", "body": "B", "labels": []},
    ]
    _module, run = _triage(tmp_path, monkeypatch, issues)
    monkeypatch.setenv(
        "AUTOMATION_EVENT_PAYLOAD",
        '{"event":{"payload":{"repository":{"full_name":"owner/repo"},'
        '"issue":{"number":2}}}}',
    )
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "second",
    }

    run.run()

    assert run.dispatcher.deliver.call_args.kwargs["subject"] == "9876:issue:2"


def test_triage_event_skips_other_repositories(tmp_path, monkeypatch):
    issues = [{"number": 1, "title": "First", "body": "A", "labels": []}]
    _module, run = _triage(tmp_path, monkeypatch, issues)
    monkeypatch.setenv(
        "AUTOMATION_EVENT_PAYLOAD",
        '{"event":{"payload":{"repository":{"full_name":"other/repo"},'
        '"issue":{"number":1}}}}',
    )

    run.run()

    run.dispatcher.deliver.assert_not_called()


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
        module.json.dumps(
            [module.TRIAGE_FORMAT_VERSION, "Unchanged", "", []], sort_keys=True
        ).encode()
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


def test_triage_ignores_managed_body_when_computing_delivery(tmp_path, monkeypatch):
    original = "Human request\n\n### Desired Behavior\nKeep the API stable."
    issue = {
        "number": 7,
        "title": "Improve behavior",
        "body": original,
        "labels": [{"name": "enhancement"}],
    }
    module, run = _triage(tmp_path, monkeypatch, [issue])
    digest = module.hashlib.sha256(
        module.json.dumps(
            [module.TRIAGE_FORMAT_VERSION, "Improve behavior", original, []],
            sort_keys=True,
        ).encode()
    ).hexdigest()
    issue["body"] += (
        "\n\n<!-- openhands-ai-triage:start -->\n"
        "---\n## OpenHands AI triage\n"
        "### Acceptance Criteria\n- [ ] Preserve behavior\n"
        f"<!-- triage-source:{digest} -->\n"
        "<!-- openhands-ai-triage:end -->"
    )

    run.run()

    run.dispatcher.deliver.assert_not_called()
    assert module.author_body(issue["body"]) == original


def test_triage_reprocesses_legacy_comment_digest(tmp_path, monkeypatch):
    issue = {"number": 7, "title": "Improve behavior", "body": "Request", "labels": []}
    module, run = _triage(tmp_path, monkeypatch, [issue])
    legacy_digest = module.hashlib.sha256(
        module.json.dumps(["Improve behavior", "Request", []], sort_keys=True).encode()
    ).hexdigest()
    run.gh_pages = lambda path: [
        {"id": 10, "body": f"<!-- triage-source:{legacy_digest} -->"}
    ]
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "triage",
    }

    run.run()

    run.dispatcher.deliver.assert_called_once()


def test_triage_passes_only_human_owned_body_to_agent(tmp_path, monkeypatch):
    issue = {
        "number": 8,
        "title": "Clarify behavior",
        "body": (
            "Original description\n\n"
            "<!-- openhands-ai-triage:start -->\n"
            "Old generated criteria\n"
            "<!-- triage-source:old -->\n"
            "<!-- openhands-ai-triage:end -->"
        ),
        "labels": [{"name": "enhancement"}],
    }
    _module, run = _triage(tmp_path, monkeypatch, [issue])
    run.dispatcher.deliver.return_value = {
        "disposition": "resumed",
        "conversation_id": "triage",
    }

    run.run()

    prompt = run.dispatcher.deliver.call_args.kwargs["prompt"]
    assert '"author_body": "Original description"' in prompt
    assert '"managed_triage_section_present": true' in prompt
    assert "Old generated criteria" not in prompt


def test_incomplete_marker_pair_remains_human_owned(tmp_path, monkeypatch):
    module, _run = _triage(tmp_path, monkeypatch, [])
    body = "Human text\n<!-- openhands-ai-triage:start -->\nUnclosed text"

    assert module.author_body(body) == body
