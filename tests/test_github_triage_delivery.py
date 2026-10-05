"""Exercise shipped triage parsing, rendering, guards and delivery contracts."""

import copy
import importlib
import sys
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import unquote

import pytest
from github_automation_helpers import worker

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/github-issue-triage/scripts"


@pytest.fixture
def triage(tmp_path, monkeypatch):
    # Until the parent updates the bundle manifest, load the same source helper.
    monkeypatch.syspath_prepend(str(SCRIPTS))
    monkeypatch.delitem(sys.modules, "triage_publication", raising=False)
    module = worker("github-issue-triage", tmp_path, monkeypatch)
    publication = importlib.import_module("triage_publication")
    run = object.__new__(module.IssueTriage)
    run.repository = "owner/repo"
    run.config = {}
    run.token_name = "GITHUB_PERSONAL_ACCESS_TOKEN"
    run.dispatcher = Mock()  # Conversation service transport boundary.
    run.dispatcher.deliver.return_value = {
        "disposition": "created",
        "conversation_id": "test",
    }
    run.api = lambda *args: {"login": "triage-bot"}
    run.gh = lambda *args: {"id": 9876}
    run.gh_pages = lambda *args: []
    run.dependencies_complete = lambda issue: True
    return module, publication, run


def issue():
    return {
        "number": 7,
        "title": "Improve behavior",
        "body": "Human request",
        "state": "open",
        "labels": [],
    }


def ready():
    return {
        "decision": "ready",
        "priority": "low",
        "scope": "Preserve API",
        "non_goals": "No new backend",
        "criteria": ["Saved settings still load"],
        "questions": [],
    }


def decision():
    return {
        **ready(),
        "decision": "decision_needed",
        "criteria": [],
        "questions": ["Which retention limit?"],
    }


def test_delivery_and_prompt(triage):
    _, _, run = triage
    run.open_issues = lambda: [{**issue(), "number": 2}, {**issue(), "number": 1}]
    run.run()
    calls = run.dispatcher.deliver.call_args_list
    assert [c.kwargs["subject"] for c in calls] == ["9876:issue:1", "9876:issue:2"]
    prompt = calls[0].kwargs["prompt"]
    for text in (
        "do not implement code",
        "custom-codereview-guide.md",
        "affected version",
        "software-agent-sdk",
        "current decisions override stale",
        "ask only unanswered questions",
        "Issue readiness is separate",
        "Legacy direct mode",
        "Direct publication",
    ):
        assert text in prompt


def test_event_scope_and_failure_isolation(triage, monkeypatch):
    _, _, run = triage
    run.open_issues = lambda: [{**issue(), "number": 1}, {**issue(), "number": 2}]
    run.dispatcher.deliver.side_effect = [
        RuntimeError("offline"),
        {"disposition": "created", "conversation_id": "2"},
    ]
    run.run()
    assert run.dispatcher.deliver.call_count == 2
    run.dispatcher.deliver.reset_mock(side_effect=True)
    monkeypatch.setenv(
        "AUTOMATION_EVENT_PAYLOAD",
        '{"event":{"payload":{"repository":{"full_name":"owner/repo"},"issue":{"number":2}}}}',
    )
    run.run()
    assert run.dispatcher.deliver.call_args.kwargs["subject"] == "9876:issue:2"


def test_self_owned_output_no_loop_human_marker_not_ignored(triage):
    _, p, run = triage
    i = issue()
    digest = p.fingerprint(i, [], "triage-bot")
    i["body"], _ = p.render(i["body"], ready(), digest)
    run.open_issues = lambda: [i]
    run.run()
    run.dispatcher.deliver.assert_not_called()
    human = {
        "id": 8,
        "user": {"login": "human"},
        "body": f"No, revise scope. <!-- triage-source:{digest} -->",
    }
    run.gh_pages = lambda path: [human]
    run.run()
    assert "No, revise scope" in run.dispatcher.deliver.call_args.kwargs["prompt"]


@pytest.mark.parametrize(
    "body",
    [
        "<!-- openhands-ai-triage:start -->",
        "<!-- openhands-ai-triage:end -->",
        "<!-- openhands-ai-triage:end --><!-- openhands-ai-triage:start -->",
        "<!-- openhands-ai-triage:start --><!-- openhands-ai-triage:start --><!-- openhands-ai-triage:end -->",
    ],
)
def test_ambiguous_markers_fail_closed(triage, body):
    _, p, _ = triage
    with pytest.raises(ValueError):
        p.render(body, ready(), "a" * 64)


def test_render_preserves_outside_bytes_and_is_idempotent(triage):
    _, p, _ = triage
    before, after = "Human  \n\n", "\n\nHuman conclusion  \n"
    original = before + p.START + "stale" + p.END + after
    body, comment = p.render(original, ready(), "a" * 64)
    assert body.startswith(before) and body.endswith(after) and comment is None
    assert p.render(body, ready(), "a" * 64)[0] == body
    removed, comment = p.render(body, decision(), "a" * 64)
    assert removed == before + after
    assert "Acceptance Criteria" not in comment
    assert "on behalf of" in comment


@pytest.mark.parametrize(
    "changes",
    [
        {"decision": "other"},
        {"criteria": []},
        {"questions": ["already answered"]},
        {"scope": ""},
        {"non_goals": "<!-- spoof -->"},
        {"criteria": [3]},
        {"extra": True},
    ],
)
def test_parser_rejects_invalid_recommendations(triage, changes):
    _, p, _ = triage
    with pytest.raises(ValueError):
        p.parse_recommendation({**ready(), **changes})


class GitHubTransport:
    """In-memory HTTP boundary; all triage algorithms above are real."""

    repository = "owner/repo"

    def __init__(self):
        self.config = {}
        self.issue = issue()
        self.comments = []
        self.writes = []
        self.permission = "write"
        self.sha = "a" * 40
        self.reads = 0
        self.change_on_read = None

    def api(self, *args):
        return {"login": "triage-bot"}

    def gh_pages(self, path):
        return copy.deepcopy(self.comments) if path.endswith("/comments") else []

    def gh(self, method, path, body=None):
        if method == "GET":
            if path.startswith("/contents/"):
                return {"sha": self.sha}
            if path.endswith("/permission"):
                return {"permission": self.permission}
            self.reads += 1
            if self.reads == self.change_on_read:
                self.issue["body"] += " Human changed scope"
            return copy.deepcopy(self.issue)
        self.writes.append((method, path, body))
        if path == "/issues/7" and method == "PATCH":
            self.issue.update(body)
        elif path == "/issues/7/labels":
            self.issue["labels"] += [{"name": name} for name in body["labels"]]
        elif "/labels/" in path and method == "DELETE":
            self.issue["labels"] = [
                l
                for l in self.issue["labels"]
                if l["name"] != unquote(path.split("/labels/")[1])
            ]
        elif path == "/issues/7/comments":
            self.comments.append({"id": 100, "user": {"login": "triage-bot"}, **body})
        elif path.startswith("/issues/comments/"):
            number = int(path.rsplit("/", 1)[1])
            if method == "DELETE":
                self.comments = [c for c in self.comments if c["id"] != number]
            else:
                next(c for c in self.comments if c["id"] == number).update(body)
        return {}


def test_publish_ready_policy_and_noop(triage):
    _, p, _ = triage
    transport = GitHubTransport()
    transport.config = {
        "triage_readiness_policies": {
            "owner/repo": {
                "mode": "authorized-writers",
                "files": {".github/workflows/issue-readiness-check.yml": transport.sha},
            }
        }
    }
    digest = p.fingerprint(
        transport.issue,
        [],
        "triage-bot",
        policy=transport.config.get("triage_readiness_policies"),
    )
    assert p.publish(transport, 7, digest, ready())["readiness_policy_allowed"]
    assert {l["name"] for l in transport.issue["labels"]} == {
        "ready-for-dev",
        "priority:low",
    }
    assert p.publish(transport, 7, digest, ready())["writes"] == 0


@pytest.mark.parametrize("mode", ["unknown", "policy_changed", "unauthorized"])
def test_readiness_fail_closed_without_media_rules(triage, mode):
    _, p, _ = triage
    t = GitHubTransport()
    t.issue["labels"] = [{"name": "ready-for-dev"}, {"name": "human-label"}]
    if mode != "unknown":
        t.config = {
            "triage_readiness_policies": {
                t.repository: {
                    "mode": "authorized-writers",
                    "files": {"policy.yml": "a" * 40},
                }
            }
        }
    if mode == "policy_changed":
        t.sha = "b" * 40
    if mode == "unauthorized":
        t.permission = "read"
    digest = p.fingerprint(
        t.issue, [], "triage-bot", policy=t.config.get("triage_readiness_policies")
    )
    assert not p.publish(t, 7, digest, ready())["readiness_policy_allowed"]
    assert {l["name"] for l in t.issue["labels"]} == {
        "human-label",
        "priority:low",
        "ready-for-dev",
    }


@pytest.mark.parametrize("when", [1, 2])
def test_reject_changed_inputs_before_any_write(triage, when):
    _, p, _ = triage
    t = GitHubTransport()
    digest = p.fingerprint(
        t.issue, [], "triage-bot", policy=t.config.get("triage_readiness_policies")
    )
    t.change_on_read = when
    with pytest.raises(ValueError, match="changed"):
        p.publish(t, 7, digest, ready())
    assert not t.writes


def test_decision_updates_only_owned_comments_and_noop(triage):
    _, p, _ = triage
    t = GitHubTransport()
    human = {
        "id": 1,
        "user": {"login": "human"},
        "body": "My decision <!-- triage-source:" + "b" * 64 + " -->",
    }
    t.comments = [
        human,
        {
            "id": 2,
            "user": {"login": "triage-bot"},
            "body": "Old <!-- triage-source:" + "a" * 64 + " -->",
        },
    ]
    digest = p.fingerprint(t.issue, t.comments, "triage-bot")
    p.publish(t, 7, digest, decision())
    assert t.comments[0] == human
    assert len(t.comments) == 2 and "Decision needed" in t.comments[1]["body"]
    assert p.publish(t, 7, digest, decision())["writes"] == 0


def test_human_label_transitions_but_not_self_churn(triage):
    _, p, run = triage
    event = {
        "id": 1,
        "event": "unlabeled",
        "label": {"name": "ready-for-dev"},
        "actor": {"login": "human"},
    }
    run.gh_pages = lambda path: [event]
    assert p.readiness_transitions(run, 7, "triage-bot")
    event["actor"]["login"] = "triage-bot"
    assert not p.readiness_transitions(run, 7, "triage-bot")
    assert p.fingerprint(
        issue(), [], "triage-bot", policy={"version": 1}
    ) != p.fingerprint(issue(), [], "triage-bot", policy={"version": 2})


def test_opt_in_configuration_fails_before_dispatch(triage, tmp_path):
    _, _, run = triage
    run.config = {"triage_publisher_path": "/missing"}
    with pytest.raises(ValueError):
        run.run()
    run.dispatcher.deliver.assert_not_called()
    publisher = tmp_path / "triage_publication.py"
    publisher.write_text("# trusted helper")
    config = tmp_path / "config.json"
    config.write_text('{"repos": ["owner/repo"]}')
    run.config = {
        "triage_publisher_path": str(publisher),
        "triage_publisher_config_path": str(config),
    }
    with pytest.raises(ValueError, match="remote unsupported"):
        run.run()
    run.config["triage_publisher_workspace"] = "shared-host"
    run.open_issues = lambda: [issue()]
    run.run()
    prompt = run.dispatcher.deliver.call_args.kwargs["prompt"]
    assert str(publisher) in prompt
    assert "Direct publication (legacy" not in prompt


def test_checker_self_updates_do_not_change_human_fingerprint(triage):
    _, p, _ = triage
    c = {
        "id": 9,
        "user": {"login": "github-actions[bot]"},
        "body": "<!-- issue-readiness-check --> Old rule",
        "updated_at": "one",
    }
    digest = p.fingerprint(issue(), [c], "triage-bot")
    c["updated_at"] = "two"
    c["body"] += " more output"
    assert p.fingerprint(issue(), [c], "triage-bot") == digest
    c["user"]["login"] = "human"
    assert p.fingerprint(issue(), [c], "triage-bot") != digest


def test_closed_issue_and_mid_publication_change_abort(triage):
    _, p, _ = triage
    t = GitHubTransport()
    digest = p.fingerprint(t.issue, [], "triage-bot")
    t.issue["state"] = "closed"
    with pytest.raises(ValueError, match="eligible"):
        p.publish(t, 7, digest, ready())
    assert not t.writes
    t.issue["state"] = "open"
    t.reads = 0
    t.change_on_read = 3
    with pytest.raises(ValueError, match="changed"):
        p.publish(t, 7, digest, ready())
    assert len(t.writes) == 1
    assert "Human changed scope" in t.issue["body"]


def test_partial_write_has_no_receipt_and_retry_finishes(triage):
    _, p, run = triage
    t = GitHubTransport()
    digest = p.fingerprint(t.issue, [], "triage-bot")
    original = t.gh

    def fail_labels(method, path, body=None):
        if method == "POST" and path.endswith("/labels"):
            raise RuntimeError("transport interrupted")
        return original(method, path, body)

    t.gh = fail_labels
    with pytest.raises(RuntimeError):
        p.publish(t, 7, digest, ready())
    assert "triage-source:" in t.issue["body"]
    assert "triage-complete:" not in t.issue["body"]
    run.config = {
        "triage_publisher_path": "/trusted/publisher.py",
        "triage_publisher_config_path": "/trusted/config.json",
    }
    run.gh_pages = t.gh_pages
    run._submit(9876, t.issue, [t.issue])
    run.dispatcher.deliver.assert_called_once()
    t.gh = original
    p.publish(t, 7, digest, ready())
    assert "triage-complete:" in t.issue["body"]
    assert p.publish(t, 7, digest, ready())["writes"] == 0


def test_concurrent_labels_abort_before_write(triage):
    _, p, _ = triage
    t = GitHubTransport()
    digest = p.fingerprint(t.issue, [], "triage-bot")
    original = t.gh

    def changed(method, path, body=None):
        if method == "GET" and path == "/issues/7" and t.reads == 1:
            t.issue["labels"].append({"name": "ready-for-dev"})
        return original(method, path, body)

    t.gh = changed
    with pytest.raises(ValueError, match="changed"):
        p.publish(t, 7, digest, ready())
    assert not t.writes
