"""Unit tests for the gitlab-issue-to-mr automation script.

The focus is what the script owns rather than the agent: the credential never
reaching the workspace, the secrets the conversation is handed, the project path
it builds every API call from, the branch it picks, the commits it counts, and
the clone it removes.
"""

import importlib.util
import json
import subprocess
import urllib.error
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).parent.parent / "skills" / "gitlab-issue-to-mr" / "scripts" / "main.py"
)


def _load_module(monkeypatch, workspace_base: Path):
    """Import main.py under its own module name, with a scratch workspace."""
    monkeypatch.setenv("WORKSPACE_BASE", str(workspace_base))
    monkeypatch.delenv("AUTOMATION_KV_TOKEN", raising=False)
    monkeypatch.delenv("AUTOMATION_API_URL", raising=False)
    spec = importlib.util.spec_from_file_location("gitlab_issue_to_mr_main", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def main(monkeypatch, tmp_path):
    return _load_module(monkeypatch, tmp_path / "workspace")


def _http_error(code: int, body: bytes = b"{}") -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://gitlab.com/api/v4", code, "err", {}, None)


# ── Configuration ─────────────────────────────────────────────────────────────


def test_config_json_overrides_the_constants(main, tmp_path):
    """The catalog path ships an unmodified script plus a rendered config.json,
    because a declarative host cannot rewrite Python."""
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "projects": ["acme/one", "acme/two"],
                "trigger_label": "ship-it",
                "branch_prefix": "bot/issue",
                "merge_request_mode": "ready",
                "max_new_per_run": 5,
                "gitlab_api_url": "https://gitlab.example.com/api/v4",
                "agent_secret_names": ["NPM_TOKEN"],
                "openhands_url": "https://app.example.com",
                "unknown_key": "ignored",
            }
        )
    )

    config = main.load_config(tmp_path)

    assert config == {
        "projects": ["acme/one", "acme/two"],
        "trigger_label": "ship-it",
        "branch_prefix": "bot/issue",
        "merge_request_mode": "ready",
        "max_new_per_run": 5,
        "gitlab_api_url": "https://gitlab.example.com/api/v4",
        "agent_secret_names": ["NPM_TOKEN"],
        "openhands_url": "https://app.example.com",
    }


def test_a_missing_config_leaves_the_constants_alone(main, tmp_path):
    assert main.load_config(tmp_path) == {}


@pytest.mark.parametrize(
    "config",
    [
        {"projects": "acme/one"},
        {"projects": []},
        {"projects": ["acme/one", ""]},
        {"trigger_label": ["openhands"]},
        {"merge_request_mode": "maybe"},
        {"max_new_per_run": 0},
        {"max_new_per_run": True},
        {"gitlab_api_url": "gitlab.example.com"},
        {"agent_secret_names": [1]},
    ],
)
def test_a_config_that_would_misbehave_fails_the_run(main, tmp_path, config):
    """Polling the string "group/project" one character at a time is worse than
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
        ("group/project", "group/project"),
        ("  group/project  ", "group/project"),
        ("https://gitlab.com/group/project", "group/project"),
        ("https://gitlab.com/group/project.git", "group/project"),
        ("git@gitlab.com:group/project.git", "group/project"),
        ("https://gitlab.example.com/group/project", "group/project"),
        ("https://gitlab.com/group/team/service", "group/team/service"),
        ("https://gitlab.com/group/project/-/issues/42", "group/project"),
    ],
)
def test_projects_are_normalized_to_a_project_path(main, written, expected):
    """A clone URL is what a project page offers to copy, so it is what ends up
    pasted into the form. Left alone it becomes a 404 blamed on the token."""
    assert main.normalize_project(written) == expected


@pytest.mark.parametrize("written", ["", "project", "https://gitlab.com/group"])
def test_a_value_that_is_not_a_project_is_named(main, written):
    with pytest.raises(ValueError):
        main.normalize_project(written)


def test_a_subgroup_path_survives_normalization(main):
    """Truncating group/team/service to the last two segments would point at a
    project that does not exist."""
    assert main.normalize_project("group/team/service") == "group/team/service"


# ── Project paths in API calls ────────────────────────────────────────────────


def test_the_project_path_is_url_encoded_for_every_call(main):
    """GitLab takes the path where an ID is expected, so every separator has to
    be encoded or the segments become routes of their own."""
    assert main._project_id("group/project") == "group%2Fproject"
    assert main._project_id("group/team/service") == "group%2Fteam%2Fservice"


def test_the_instance_url_is_the_api_root_without_its_suffix(main, monkeypatch):
    assert main._instance_url() == "https://gitlab.com"

    monkeypatch.setattr(main, "GITLAB_API_URL", "https://gitlab.example.com/gl/api/v4")
    assert main._instance_url() == "https://gitlab.example.com/gl"


def test_the_clone_url_comes_from_gitlab_when_it_states_one(main):
    """A self-managed instance may serve git over a host that is not the API
    host, and it is the only party that knows."""
    stated = main._clone_url(
        "group/project", {"http_url_to_repo": "https://git.example.com/group/project.git"}
    )

    assert stated == "https://git.example.com/group/project.git"
    assert main._clone_url("group/project", {}) == "https://gitlab.com/group/project.git"


# ── Access level ──────────────────────────────────────────────────────────────


def test_a_role_below_developer_is_refused(main, monkeypatch):
    monkeypatch.setattr(
        main,
        "_gitlab_request",
        lambda *a, **k: ({"permissions": {"project_access": {"access_level": 20}}}, {}),
    )

    with pytest.raises(RuntimeError, match="below Developer"):
        main._get_project("token", "group/project")


def test_a_group_role_counts_when_the_project_states_none(main, monkeypatch):
    """A token acting through a group reports only the group role; reading just
    project_access would refuse a project it can push to."""
    monkeypatch.setattr(
        main,
        "_gitlab_request",
        lambda *a, **k: (
            {
                "default_branch": "main",
                "permissions": {"project_access": None, "group_access": {"access_level": 40}},
            },
            {},
        ),
    )

    assert main._get_project("token", "group/project")["default_branch"] == "main"


def test_an_unstated_role_is_not_treated_as_no_role(main, monkeypatch):
    """A project access token reports no role at all, and still pushes."""
    monkeypatch.setattr(
        main, "_gitlab_request", lambda *a, **k: ({"default_branch": "trunk", "permissions": {}}, {})
    )

    assert main._get_project("token", "group/project")["default_branch"] == "trunk"


def test_an_inaccessible_project_names_itself(main, monkeypatch):
    def fake_request(*args, **kwargs):
        raise _http_error(404)

    monkeypatch.setattr(main, "_gitlab_request", fake_request)

    with pytest.raises(RuntimeError, match="group/project"):
        main._get_project("token", "group/project")


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
    main._git(["clone", "https://gitlab.com/group/project.git", "/tmp/x"], token="glpat_secret")

    assert "glpat_secret" not in " ".join(captured["argv"])
    assert captured["env"]["GIT_CONFIG_KEY_0"] == "http.extraHeader"
    assert captured["env"]["GIT_CONFIG_VALUE_0"].startswith("Authorization: Basic ")
    assert "glpat_secret" not in captured["env"]["GIT_CONFIG_VALUE_0"]
    assert captured["env"]["GIT_TERMINAL_PROMPT"] == "0"


def test_git_authenticates_the_token_as_the_oauth2_user(main, monkeypatch):
    """GitLab accepts a personal access token over HTTPS as the `oauth2` user."""
    import base64

    captured = {}

    def fake_run(argv, **kwargs):
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(main.subprocess, "run", fake_run)
    main._git(["fetch"], token="glpat_secret")

    encoded = captured["env"]["GIT_CONFIG_VALUE_0"].removeprefix("Authorization: Basic ")
    assert base64.b64decode(encoded).decode() == "oauth2:glpat_secret"


def test_git_failures_do_not_echo_the_token(main, monkeypatch):
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 128, "", "fatal: bad credentials glpat_secret")

    monkeypatch.setattr(main.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as excinfo:
        main._git(["push", "origin", "HEAD"], token="glpat_secret")

    assert "glpat_secret" not in str(excinfo.value)
    assert "***" in str(excinfo.value)


# ── Secrets handed to the conversation ────────────────────────────────────────


def test_only_the_gitlab_token_is_forwarded_by_default(main, monkeypatch):
    """The agent reads the issue itself, so it needs the GitLab token - and
    nothing else in the deployment's secret store."""
    monkeypatch.setattr(
        main,
        "_list_secret_names",
        lambda agent_url, api_key: [
            {"name": "GITLAB_TOKEN"},
            {"name": "NPM_TOKEN"},
            {"name": "AWS_SECRET_ACCESS_KEY"},
        ],
    )

    assert main.AGENT_SECRET_NAMES == ["GITLAB_TOKEN"]
    assert list(main._build_secrets_payload("http://agent", "key")) == ["GITLAB_TOKEN"]


def test_an_empty_allow_list_forwards_nothing(main, monkeypatch):
    monkeypatch.setattr(main, "AGENT_SECRET_NAMES", [])
    called = False

    def fake_list(agent_url, api_key):
        nonlocal called
        called = True
        return [{"name": "GITLAB_TOKEN"}]

    monkeypatch.setattr(main, "_list_secret_names", fake_list)

    assert main._build_secrets_payload("http://agent", "key") == {}
    assert called is False


def test_only_declared_secrets_are_forwarded(main, monkeypatch):
    monkeypatch.setattr(main, "AGENT_SECRET_NAMES", ["NPM_TOKEN", "ABSENT_TOKEN"])
    monkeypatch.setattr(
        main,
        "_list_secret_names",
        lambda agent_url, api_key: [{"name": "GITLAB_TOKEN"}, {"name": "NPM_TOKEN"}],
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


def test_only_open_issues_with_the_label_are_requested(main, monkeypatch):
    """GitLab keeps merge requests on their own endpoint, so the filter is the
    whole of the selection."""
    captured = {}

    def fake_paginate(token, path, params=None):
        captured["path"] = path
        captured["params"] = params
        return [{"iid": 1, "title": "an issue"}]

    monkeypatch.setattr(main, "_gitlab_paginate", fake_paginate)

    issues = main._list_labeled_issues("token", "group/project")

    assert [issue["iid"] for issue in issues] == [1]
    assert captured["path"] == "/projects/group%2Fproject/issues"
    assert captured["params"]["state"] == "opened"
    assert captured["params"]["labels"] == "openhands"


def test_latest_matching_label_event_wins(main, monkeypatch):
    events = [
        {"action": "add", "id": 1, "created_at": "2026-01-01T00:00:00Z", "label": {"name": "openhands"}},
        {"action": "add", "id": 2, "created_at": "2026-01-03T00:00:00Z", "label": {"name": "other"}},
        {"action": "remove", "id": 3, "created_at": "2026-01-04T00:00:00Z", "label": {"name": "openhands"}},
        {"action": "add", "id": 4, "created_at": "2026-01-02T00:00:00Z", "label": {"name": "OpenHands"}},
    ]
    monkeypatch.setattr(main, "_gitlab_paginate", lambda token, path, params=None: events)

    event = main._latest_trigger_label_event("token", "group/project", 42)

    assert event["id"] == 4


def test_an_event_whose_label_was_deleted_is_skipped(main, monkeypatch):
    """GitLab keeps the event and nulls its label when the label is deleted."""
    monkeypatch.setattr(
        main,
        "_gitlab_paginate",
        lambda token, path, params=None: [
            {"action": "add", "id": 9, "created_at": "2026-01-01T00:00:00Z", "label": None}
        ],
    )

    assert main._latest_trigger_label_event("token", "group/project", 42) is None


def test_no_matching_label_event_returns_none(main, monkeypatch):
    monkeypatch.setattr(
        main,
        "_gitlab_paginate",
        lambda token, path, params=None: [
            {"action": "remove", "id": 9, "created_at": "2026-01-01T00:00:00Z", "label": {"name": "openhands"}}
        ],
    )

    assert main._latest_trigger_label_event("token", "group/project", 42) is None


def test_gitlab_labels_are_plain_strings(main):
    """GitLab returns issue labels as strings, not objects."""
    assert main._has_trigger_label({"labels": ["bug", "OpenHands"]}) is True
    assert main._has_trigger_label({"labels": ["bug"]}) is False
    assert main._has_trigger_label({}) is False


# ── Branch naming ─────────────────────────────────────────────────────────────


def test_branch_name_is_the_first_free_one(main, monkeypatch):
    """Re-applying the label must not force-push over the previous attempt."""
    taken = {"openhands/issue-42", "openhands/issue-42-2"}

    def fake_request(token, method, path, params=None, body=None):
        branch = path.split("/repository/branches/", 1)[1].replace("%2F", "/")
        if branch in taken:
            return {"name": branch}, {}
        raise _http_error(404)

    monkeypatch.setattr(main, "_gitlab_request", fake_request)

    assert main._branch_name("token", "group/project", 42) == "openhands/issue-42-3"


def test_the_branch_name_is_url_encoded_in_the_lookup(main, monkeypatch):
    """A prefix with a slash in it becomes extra path segments if left alone."""
    seen = []

    def fake_request(token, method, path, params=None, body=None):
        seen.append(path)
        raise _http_error(404)

    monkeypatch.setattr(main, "_gitlab_request", fake_request)
    main._branch_name("token", "group/project", 42)

    assert seen[0] == "/projects/group%2Fproject/repository/branches/openhands%2Fissue-42"


def test_branch_lookup_does_not_swallow_other_errors(main, monkeypatch):
    def fake_request(token, method, path, params=None, body=None):
        raise _http_error(500)

    monkeypatch.setattr(main, "_gitlab_request", fake_request)

    with pytest.raises(urllib.error.HTTPError):
        main._branch_name("token", "group/project", 42)


# ── Merge request creation ────────────────────────────────────────────────────


def test_a_draft_is_a_title_prefix(main, monkeypatch):
    """GitLab has no draft flag on the merge request API."""
    assert main._merge_request_title("[#42] Retry uploads") == "Draft: [#42] Retry uploads"

    monkeypatch.setattr(main, "DRAFT_MERGE_REQUEST", False)
    assert main._merge_request_title("[#42] Retry uploads") == "[#42] Retry uploads"


def test_the_merge_request_is_opened_from_the_branch_onto_the_default(main, monkeypatch):
    sent = {}

    def fake_request(token, method, path, params=None, body=None):
        sent["path"] = path
        sent["body"] = body
        return {"web_url": "https://gitlab.com/group/project/-/merge_requests/7", "iid": 7}, {}

    monkeypatch.setattr(main, "_gitlab_request", fake_request)

    mr = main._open_merge_request(
        "token", "group/project", "openhands/issue-42", "main", "[#42] Retry uploads", "why"
    )

    assert mr["iid"] == 7
    assert sent["path"] == "/projects/group%2Fproject/merge_requests"
    assert sent["body"]["source_branch"] == "openhands/issue-42"
    assert sent["body"]["target_branch"] == "main"
    assert sent["body"]["title"] == "Draft: [#42] Retry uploads"
    assert sent["body"]["description"] == "why"


def test_a_conflict_adopts_the_merge_request_that_already_exists(main, monkeypatch):
    """A retried finalization must not fail on the merge request it opened the
    first time round."""
    def fake_request(token, method, path, params=None, body=None):
        raise _http_error(409)

    monkeypatch.setattr(main, "_gitlab_request", fake_request)
    monkeypatch.setattr(
        main,
        "_existing_merge_request",
        lambda token, project, branch: {"web_url": "https://gitlab.com/mr/7", "iid": 7},
    )

    mr = main._open_merge_request(
        "token", "group/project", "openhands/issue-42", "main", "title", "body"
    )

    assert mr["iid"] == 7


def test_a_conflict_with_no_merge_request_behind_it_is_still_an_error(main, monkeypatch):
    def fake_request(token, method, path, params=None, body=None):
        raise urllib.error.HTTPError("url", 409, "err", {}, None)

    monkeypatch.setattr(main, "_gitlab_request", fake_request)
    monkeypatch.setattr(main, "_existing_merge_request", lambda token, project, branch: None)

    with pytest.raises((RuntimeError, AttributeError)):
        main._open_merge_request("token", "group/project", "b", "main", "title", "body")


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
    subprocess.run(
        ["git", "commit", "-q", "-m", "agent commit"], cwd=checkout, check=True, capture_output=True
    )
    (checkout / "extra.py").write_text("print('extra')\n")

    commits = main._commit_agent_work(checkout, 42, "title", base_sha)

    assert commits == 2


def test_an_untouched_clone_produces_no_commits(main, tmp_path):
    """No commits is how an agent reports an issue it could not implement, so it
    must not become an empty merge request."""
    checkout = tmp_path / "clone"
    base_sha = _init_repo(checkout)

    assert main._commit_agent_work(checkout, 42, "title", base_sha) == 0


# ── Releasing the clone ───────────────────────────────────────────────────────


def test_a_running_conversation_keeps_its_clone(main, monkeypatch, tmp_path):
    checkout = main._checkouts_root() / "group__project" / "issue-42-1"
    checkout.mkdir(parents=True)
    rec = {"workspace_dir": str(checkout), "conversation_id": "conv-1"}
    monkeypatch.setattr(main, "conversation_status", lambda *a: "running")

    assert main._release_checkout(rec, "http://agent", "key") is False
    assert checkout.exists()
    assert rec["workspace_dir"] == str(checkout)


def test_a_stopped_conversation_releases_its_clone(main, monkeypatch, tmp_path):
    checkout = main._checkouts_root() / "group__project" / "issue-42-1"
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
    checkout = main._checkouts_root() / "group__project" / "issue-42-1"
    checkout.mkdir(parents=True)
    rec = {"workspace_dir": str(checkout), "conversation_id": "conv-1"}

    def boom(*args):
        raise RuntimeError("agent server unreachable")

    monkeypatch.setattr(main, "conversation_status", boom)

    assert main._release_checkout(rec, "http://agent", "key") is False
    assert checkout.exists()


# ── Merge request description ─────────────────────────────────────────────────


def test_merge_request_body_links_the_issue_and_discloses_the_agent(main):
    body = main._merge_request_body(42, "Adds a retry.", "http://oh/conversations/c1")

    assert "Adds a retry." in body
    assert "Closes #42" in body
    assert "http://oh/conversations/c1" in body
    assert "_This merge request was opened by an AI agent (OpenHands)._" in body


def test_merge_request_body_is_truncated(main):
    body = main._merge_request_body(42, "x" * (main.MAX_MR_BODY_CHARS + 100), "url")

    assert len(body) < main.MAX_MR_BODY_CHARS + 400
    assert "(summary truncated)" in body


# ── Prompt ────────────────────────────────────────────────────────────────────


def _prompt(main):
    return main._build_implementation_prompt(
        "group/project",
        {
            "iid": 42,
            "title": "Retry uploads",
            "description": "It 502s, see the log in the linked pipeline.",
            "author": {"username": "alice"},
            "labels": ["openhands"],
            "web_url": "https://gitlab.com/group/project/-/issues/42",
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
    assert "https://gitlab.com/group/project/-/issues/42" in prompt
    assert "https://gitlab.com/api/v4/projects/group%2Fproject/issues/42" in prompt
    assert "/notes" in prompt
    assert "GITLAB_TOKEN" in prompt


def test_the_prompt_does_not_embed_the_issue_text(main):
    prompt = _prompt(main)

    assert "It 502s" not in prompt


def test_the_prompt_tells_the_agent_to_push_and_open_the_merge_request(main):
    """The merge request should appear when the agent stops, not on the next poll."""
    prompt = _prompt(main)

    assert "git push" in prompt and "https://oauth2:$GITLAB_TOKEN@gitlab.com/group/project.git" in prompt
    assert "HEAD:refs/heads/openhands/issue-42" in prompt
    assert "/projects/group%2Fproject/merge_requests" in prompt
    assert '"Draft: [#42] Retry uploads"' in prompt
    assert "Closes #42" in prompt
    assert "GITLAB_MR_OPENED" in prompt


def test_the_prompt_says_a_command_must_name_the_secret(main):
    """The SDK only puts a secret in the environment of a command that mentions
    it, so an instruction that omits the name would simply fail to authenticate."""
    prompt = _prompt(main)

    assert "only put in the environment of a command that mentions it" in prompt
    assert "Never echo it" in prompt


def test_the_prompt_keeps_the_untrusted_input_boundary(main):
    prompt = _prompt(main)

    assert "untrusted input" in prompt
    assert "projects other than group/project" in prompt


def test_a_ready_for_review_configuration_drops_the_draft_prefix(main, monkeypatch):
    monkeypatch.setattr(main, "DRAFT_MERGE_REQUEST", False)
    prompt = _prompt(main)

    assert "Draft: [#42]" not in prompt
    assert "ready for review" in prompt


def test_the_prompt_points_at_a_self_managed_instance(main, monkeypatch):
    monkeypatch.setattr(main, "GITLAB_API_URL", "https://gitlab.example.com/api/v4")
    prompt = _prompt(main)

    assert "https://gitlab.example.com/api/v4/projects/group%2Fproject/issues/42" in prompt
    assert "https://oauth2:$GITLAB_TOKEN@gitlab.example.com/group/project.git" in prompt


# ── State ─────────────────────────────────────────────────────────────────────


def test_state_is_kept_per_project(main, tmp_path):
    main.save_state("group/one", {"version": 1, "project": "group/one", "tasks": {"1:label:1": {}}})
    main.save_state("group/two", {"version": 1, "project": "group/two", "tasks": {}})

    assert list(main.load_state("group/one")["tasks"]) == ["1:label:1"]
    assert main.load_state("group/two")["tasks"] == {}
    assert main.load_state("group/three") == {
        "version": 1,
        "project": "group/three",
        "trigger_label": main.TRIGGER_LABEL,
        "tasks": {},
    }


def test_a_subgroup_project_gets_its_own_state_document(main):
    assert main._state_key("group/team/service") == "state:group__team__service"
    assert "group__team__service" in main._state_file_path("group/team/service")


def test_unreadable_state_starts_fresh_rather_than_failing_the_run(main):
    path = Path(main._state_file_path("group/project"))
    path.write_text("{not json")

    assert main.load_state("group/project")["tasks"] == {}


def test_state_is_written_atomically(main):
    state = {"version": 1, "project": "group/project", "tasks": {"1:label:1": {"status": "active"}}}
    main.save_state("group/project", state)

    path = Path(main._state_file_path("group/project"))
    assert json.loads(path.read_text()) == state
    assert not Path(f"{path}.tmp").exists()
