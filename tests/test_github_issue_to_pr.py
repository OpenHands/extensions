"""Unit tests for the github-issue-to-pr automation script.

The focus is what the script owns rather than the agent: the credential never
reaching the workspace, the secrets the conversation is handed, the branch it
picks, the commits it counts, and the clone it removes.
"""

import importlib.util
import json
import subprocess
import urllib.error
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).parent.parent / "skills" / "github-issue-to-pr" / "scripts" / "main.py"
)


def _load_module(monkeypatch, workspace_base: Path):
    """Import main.py under its own module name, with a scratch workspace."""
    monkeypatch.setenv("WORKSPACE_BASE", str(workspace_base))
    monkeypatch.delenv("AUTOMATION_KV_TOKEN", raising=False)
    monkeypatch.delenv("AUTOMATION_API_URL", raising=False)
    spec = importlib.util.spec_from_file_location("github_issue_to_pr_main", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def main(monkeypatch, tmp_path):
    return _load_module(monkeypatch, tmp_path / "workspace")


def _http_error(code: int, body: bytes = b"{}") -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://api.github.com", code, "err", {}, None)


# ── Configuration ─────────────────────────────────────────────────────────────


def test_config_json_overrides_the_constants(main, tmp_path):
    """The catalog path ships an unmodified script plus a rendered config.json,
    because a declarative host cannot rewrite Python."""
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "repos": ["acme/one", "acme/two"],
                "trigger_label": "ship-it",
                "branch_prefix": "bot/issue",
                "pull_request_mode": "ready",
                "max_new_per_run": 5,
                "agent_secret_names": ["NPM_TOKEN"],
                "openhands_url": "https://app.example.com",
                "unknown_key": "ignored",
            }
        )
    )

    config = main.load_config(tmp_path)

    assert config == {
        "repos": ["acme/one", "acme/two"],
        "trigger_label": "ship-it",
        "branch_prefix": "bot/issue",
        "pull_request_mode": "ready",
        "max_new_per_run": 5,
        "agent_secret_names": ["NPM_TOKEN"],
        "openhands_url": "https://app.example.com",
    }


def test_a_missing_config_leaves_the_constants_alone(main, tmp_path):
    assert main.load_config(tmp_path) == {}


@pytest.mark.parametrize(
    "config",
    [
        {"repos": "acme/one"},
        {"repos": []},
        {"repos": ["acme/one", ""]},
        {"trigger_label": ["openhands"]},
        {"pull_request_mode": "maybe"},
        {"max_new_per_run": 0},
        {"max_new_per_run": True},
        {"agent_secret_names": [1]},
    ],
)
def test_a_config_that_would_misbehave_fails_the_run(main, tmp_path, config):
    """Polling the string "owner/repo" one character at a time is worse than
    stopping, so a wrong type is a hard error rather than a coercion."""
    (tmp_path / "config.json").write_text(json.dumps(config))

    with pytest.raises(SystemExit):
        main.load_config(tmp_path)


def test_a_config_that_is_not_json_fails_the_run(main, tmp_path):
    (tmp_path / "config.json").write_text("{not json")

    with pytest.raises(SystemExit):
        main.load_config(tmp_path)


@pytest.mark.parametrize(
    ("written", "expected"),
    [
        ("owner/repo", "owner/repo"),
        ("  owner/repo  ", "owner/repo"),
        ("https://github.com/owner/repo", "owner/repo"),
        ("https://github.com/owner/repo.git", "owner/repo"),
        ("git@github.com:owner/repo.git", "owner/repo"),
    ],
)
def test_repositories_are_normalized_to_owner_repo(main, written, expected):
    """A clone URL is what a repository page offers to copy, so it is what ends
    up pasted into the form. Left alone it becomes a 404 blamed on the token."""
    assert main.normalize_repo(written) == expected


@pytest.mark.parametrize("written", ["", "owner", "https://github.com/owner", "owner/repo/extra"])
def test_a_value_that_is_not_a_repository_is_named(main, written):
    with pytest.raises(ValueError):
        main.normalize_repo(written)


# ── The credential never reaches the workspace ────────────────────────────────


def test_git_passes_the_token_as_a_header_in_the_environment(main, monkeypatch):
    """A token on the command line shows up in `ps`; one in the clone's config
    is readable by the agent. It travels in the environment instead."""
    captured = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(main.subprocess, "run", fake_run)
    main._git(["clone", "https://github.com/owner/repo.git", "/tmp/x"], token="ghp_secret")

    assert "ghp_secret" not in " ".join(captured["argv"])
    assert captured["env"]["GIT_CONFIG_KEY_0"] == "http.extraHeader"
    assert captured["env"]["GIT_CONFIG_VALUE_0"].startswith("Authorization: Basic ")
    assert "ghp_secret" not in captured["env"]["GIT_CONFIG_VALUE_0"]
    assert captured["env"]["GIT_TERMINAL_PROMPT"] == "0"


def test_git_failures_do_not_echo_the_token(main, monkeypatch):
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 128, "", "fatal: bad credentials ghp_secret")

    monkeypatch.setattr(main.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as excinfo:
        main._git(["push", "origin", "HEAD"], token="ghp_secret")

    assert "ghp_secret" not in str(excinfo.value)
    assert "***" in str(excinfo.value)


# ── Secrets handed to the conversation ────────────────────────────────────────


def test_only_the_github_token_is_forwarded_by_default(main, monkeypatch):
    """The agent reads the issue itself, so it needs the GitHub token - and
    nothing else in the deployment's secret store."""
    monkeypatch.setattr(
        main,
        "_list_secret_names",
        lambda agent_url, api_key: [
            {"name": "GITHUB_PERSONAL_ACCESS_TOKEN"},
            {"name": "NPM_TOKEN"},
            {"name": "AWS_SECRET_ACCESS_KEY"},
        ],
    )

    assert main.AGENT_SECRET_NAMES == ["GITHUB_PERSONAL_ACCESS_TOKEN"]
    assert list(main._build_secrets_payload("http://agent", "key")) == [
        "GITHUB_PERSONAL_ACCESS_TOKEN"
    ]


def test_an_empty_allow_list_forwards_nothing(main, monkeypatch):
    monkeypatch.setattr(main, "AGENT_SECRET_NAMES", [])
    called = False

    def fake_list(agent_url, api_key):
        nonlocal called
        called = True
        return [{"name": "GITHUB_PERSONAL_ACCESS_TOKEN"}]

    monkeypatch.setattr(main, "_list_secret_names", fake_list)

    assert main._build_secrets_payload("http://agent", "key") == {}
    assert called is False


def test_only_declared_secrets_are_forwarded(main, monkeypatch):
    monkeypatch.setattr(main, "AGENT_SECRET_NAMES", ["NPM_TOKEN", "ABSENT_TOKEN"])
    monkeypatch.setattr(
        main,
        "_list_secret_names",
        lambda agent_url, api_key: [
            {"name": "GITHUB_PERSONAL_ACCESS_TOKEN"},
            {"name": "NPM_TOKEN"},
        ],
    )

    payload = main._build_secrets_payload("http://agent", "key")

    assert list(payload) == ["NPM_TOKEN"]
    assert payload["NPM_TOKEN"]["url"] == "/api/settings/secrets/NPM_TOKEN"
    assert payload["NPM_TOKEN"]["headers"] == {"X-Session-API-Key": "key"}


def test_the_conversation_payload_carries_no_secrets_block_when_there_are_none(
    main, monkeypatch, tmp_path
):
    sent = {}

    monkeypatch.setattr(main, "_get_agent_dict", lambda url, key: {"kind": "Agent"})
    monkeypatch.setattr(main, "_build_secrets_payload", lambda url, key: {})

    def fake_request(agent_url, api_key, method, path, body=None):
        sent["body"] = body
        return {"id": "conv-1"}

    monkeypatch.setattr(main, "_oh_request", fake_request)

    conv_id = main.create_conversation("http://agent", "key", "do the thing", tmp_path)

    assert conv_id == "conv-1"
    assert "secrets" not in sent["body"]
    assert sent["body"]["workspace"] == {"working_dir": str(tmp_path)}


# ── Issue discovery ───────────────────────────────────────────────────────────


def test_pull_requests_are_not_treated_as_issues(main, monkeypatch):
    """The issues endpoint returns pull requests too; labelling a PR must not
    queue an implementation run."""
    monkeypatch.setattr(
        main,
        "_github_paginate",
        lambda token, path, params=None: [
            {"number": 1, "title": "an issue"},
            {"number": 2, "title": "a pull request", "pull_request": {"url": "..."}},
        ],
    )

    issues = main._list_labeled_issues("token", "owner/repo")

    assert [issue["number"] for issue in issues] == [1]


def test_latest_matching_label_event_wins(main, monkeypatch):
    events = [
        {"event": "labeled", "id": 1, "created_at": "2026-01-01T00:00:00Z", "label": {"name": "openhands"}},
        {"event": "labeled", "id": 2, "created_at": "2026-01-03T00:00:00Z", "label": {"name": "other"}},
        {"event": "unlabeled", "id": 3, "created_at": "2026-01-04T00:00:00Z", "label": {"name": "openhands"}},
        {"event": "labeled", "id": 4, "created_at": "2026-01-02T00:00:00Z", "label": {"name": "OpenHands"}},
    ]
    monkeypatch.setattr(main, "_github_paginate", lambda token, path, params=None: events)

    event = main._latest_trigger_label_event("token", "owner/repo", 42)

    assert event["id"] == 4


def test_no_matching_label_event_returns_none(main, monkeypatch):
    monkeypatch.setattr(
        main,
        "_github_paginate",
        lambda token, path, params=None: [{"event": "closed", "id": 9, "created_at": "2026-01-01T00:00:00Z"}],
    )

    assert main._latest_trigger_label_event("token", "owner/repo", 42) is None


# ── Branch naming ─────────────────────────────────────────────────────────────


def test_branch_name_is_the_first_free_one(main, monkeypatch):
    """Re-applying the label must not force-push over the previous attempt."""
    taken = {"openhands/issue-42", "openhands/issue-42-2"}

    def fake_request(token, method, path, params=None, body=None):
        branch = path.split("/git/ref/heads/", 1)[1]
        if branch in taken:
            return {"ref": f"refs/heads/{branch}"}, {}
        raise _http_error(404)

    monkeypatch.setattr(main, "_github_request", fake_request)

    assert main._branch_name("token", "owner/repo", 42) == "openhands/issue-42-3"


def test_branch_lookup_does_not_swallow_other_errors(main, monkeypatch):
    def fake_request(token, method, path, params=None, body=None):
        raise _http_error(500)

    monkeypatch.setattr(main, "_github_request", fake_request)

    with pytest.raises(urllib.error.HTTPError):
        main._branch_name("token", "owner/repo", 42)


# ── Commits the agent left behind ─────────────────────────────────────────────


def _init_repo(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    run = lambda *args: subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)
    run("init", "-q", "-b", "main")
    run("config", "user.name", "Test")
    run("config", "user.email", "test@example.com")
    (path / "README.md").write_text("base\n")
    run("add", "-A")
    run("commit", "-q", "-m", "base")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_uncommitted_work_is_committed_and_counted(main, tmp_path):
    checkout = tmp_path / "clone"
    base_sha = _init_repo(checkout)
    (checkout / "fix.py").write_text("print('fixed')\n")

    commits = main._commit_agent_work(checkout, 42, "Retry uploads on a 502", base_sha)

    assert commits == 1
    assert main._git(["status", "--porcelain"], cwd=checkout).stdout.strip() == ""


def test_commits_the_agent_made_itself_are_kept(main, tmp_path):
    checkout = tmp_path / "clone"
    base_sha = _init_repo(checkout)
    (checkout / "fix.py").write_text("print('fixed')\n")
    subprocess.run(["git", "add", "-A"], cwd=checkout, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "agent commit"], cwd=checkout, check=True, capture_output=True)
    (checkout / "extra.py").write_text("print('extra')\n")

    commits = main._commit_agent_work(checkout, 42, "title", base_sha)

    assert commits == 2


def test_an_untouched_clone_produces_no_commits(main, tmp_path):
    """No commits is how an agent reports an issue it could not implement, so it
    must not become an empty pull request."""
    checkout = tmp_path / "clone"
    base_sha = _init_repo(checkout)

    assert main._commit_agent_work(checkout, 42, "title", base_sha) == 0


# ── Releasing the clone ───────────────────────────────────────────────────────


def test_a_running_conversation_keeps_its_clone(main, monkeypatch, tmp_path):
    checkout = main._checkouts_root() / "owner__repo" / "issue-42-1"
    checkout.mkdir(parents=True)
    rec = {"workspace_dir": str(checkout), "conversation_id": "conv-1"}
    monkeypatch.setattr(main, "conversation_status", lambda *a: "running")

    assert main._release_checkout(rec, "http://agent", "key") is False
    assert checkout.exists()
    assert rec["workspace_dir"] == str(checkout)


def test_a_stopped_conversation_releases_its_clone(main, monkeypatch, tmp_path):
    checkout = main._checkouts_root() / "owner__repo" / "issue-42-1"
    checkout.mkdir(parents=True)
    rec = {"workspace_dir": str(checkout), "conversation_id": "conv-1"}
    monkeypatch.setattr(main, "conversation_status", lambda *a: "finished")

    assert main._release_checkout(rec, "http://agent", "key") is True
    assert not checkout.exists()
    assert "workspace_dir" not in rec


def test_a_path_outside_the_checkout_root_is_never_removed(main, monkeypatch, tmp_path):
    outside = tmp_path / "precious"
    outside.mkdir()
    rec = {"workspace_dir": str(outside), "conversation_id": "conv-1"}
    monkeypatch.setattr(main, "conversation_status", lambda *a: "finished")

    assert main._release_checkout(rec, "http://agent", "key") is True
    assert outside.exists()
    assert "workspace_dir" not in rec


def test_an_unconfirmable_conversation_keeps_its_clone(main, monkeypatch):
    checkout = main._checkouts_root() / "owner__repo" / "issue-42-1"
    checkout.mkdir(parents=True)
    rec = {"workspace_dir": str(checkout), "conversation_id": "conv-1"}

    def boom(*args):
        raise RuntimeError("agent server unreachable")

    monkeypatch.setattr(main, "conversation_status", boom)

    assert main._release_checkout(rec, "http://agent", "key") is False
    assert checkout.exists()


# ── Pull request body ─────────────────────────────────────────────────────────


def test_pull_request_body_links_the_issue_and_discloses_the_agent(main):
    body = main._pull_request_body(42, "Adds a retry.", "http://oh/conversations/c1")

    assert "Adds a retry." in body
    assert "Closes #42" in body
    assert "http://oh/conversations/c1" in body
    assert "_This pull request was opened by an AI agent (OpenHands)._" in body


def test_pull_request_body_is_truncated(main):
    body = main._pull_request_body(42, "x" * (main.MAX_PR_BODY_CHARS + 100), "url")

    assert len(body) < main.MAX_PR_BODY_CHARS + 400
    assert "(summary truncated)" in body


# ── Prompt ────────────────────────────────────────────────────────────────────


def _prompt(main):
    return main._build_implementation_prompt(
        "owner/repo",
        {
            "number": 42,
            "title": "Retry uploads",
            "body": "It 502s, see the log in the linked run.",
            "user": {"login": "alice"},
            "labels": [{"name": "openhands"}],
            "html_url": "https://github.com/owner/repo/issues/42",
        },
        {"id": 1, "created_at": "2026-01-02T00:00:00Z"},
        "openhands/issue-42",
        "main",
        "abc123",
    )


def test_the_prompt_names_the_issue_and_sends_the_agent_to_read_it(main):
    """A copy of the description pasted at dispatch is stale as soon as someone
    comments, and it stops where the issue's own text stops."""
    prompt = _prompt(main)

    assert "#42" in prompt
    assert "https://github.com/owner/repo/issues/42" in prompt
    assert "gh issue view 42 --repo owner/repo --comments" in prompt
    assert "/repos/owner/repo/issues/42/comments" in prompt
    assert "GITHUB_PERSONAL_ACCESS_TOKEN" in prompt


def test_the_prompt_does_not_embed_the_issue_text(main):
    prompt = _prompt(main)

    assert "It 502s" not in prompt


def test_the_prompt_states_what_the_agent_must_not_do(main):
    prompt = _prompt(main)

    assert "openhands/issue-42" in prompt
    assert "Do not push, open a pull request, or comment on GitHub" in prompt
    assert "untrusted input" in prompt
    assert "Never print the token" in prompt


# ── State ─────────────────────────────────────────────────────────────────────


def test_state_is_kept_per_repository(main, tmp_path):
    main.save_state("owner/one", {"version": 1, "repo": "owner/one", "tasks": {"1:label:1": {}}})
    main.save_state("owner/two", {"version": 1, "repo": "owner/two", "tasks": {}})

    assert list(main.load_state("owner/one")["tasks"]) == ["1:label:1"]
    assert main.load_state("owner/two")["tasks"] == {}
    assert main.load_state("owner/three") == {
        "version": 1,
        "repo": "owner/three",
        "trigger_label": main.TRIGGER_LABEL,
        "tasks": {},
    }


def test_unreadable_state_starts_fresh_rather_than_failing_the_run(main):
    path = Path(main._state_file_path("owner/repo"))
    path.write_text("{not json")

    assert main.load_state("owner/repo")["tasks"] == {}


def test_state_is_written_atomically(main):
    state = {"version": 1, "repo": "owner/repo", "tasks": {"1:label:1": {"status": "active"}}}
    main.save_state("owner/repo", state)

    path = Path(main._state_file_path("owner/repo"))
    assert json.loads(path.read_text()) == state
    assert not Path(f"{path}.tmp").exists()
