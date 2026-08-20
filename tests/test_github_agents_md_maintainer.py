"""Unit tests for the github-agents-md-maintainer automation script.

The focus is what the script decides on its own: which week it is working, when
it declines to work at all, where it clones to, and what it hands the agent.
"""

import importlib.util
import json
import subprocess
import time
import urllib.error
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).parent.parent
    / "skills"
    / "github-agents-md-maintainer"
    / "scripts"
    / "main.py"
)


@pytest.fixture
def main(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_BASE", str(tmp_path / "workspace"))
    monkeypatch.delenv("AUTOMATION_KV_TOKEN", raising=False)
    monkeypatch.delenv("AUTOMATION_API_URL", raising=False)
    spec = importlib.util.spec_from_file_location("agents_md_main", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://api.github.com", code, "err", {}, None)


# ── One unit of work is one ISO week ──────────────────────────────────────────


def test_the_period_is_the_iso_week(main):
    """A cron that fires more often, a retried run, or a restarted service all
    resolve to the same key, so the work happens once."""
    assert main._current_period() == time.strftime("%G-W%V", time.gmtime())
    assert main._task_key("2026-W34") == "agents-md:2026-W34"


def test_the_branch_carries_the_period(main, monkeypatch):
    monkeypatch.setattr(main, "_github_request", lambda *a, **k: (_ for _ in ()).throw(_http_error(404)))

    assert main._branch_name("tok", "acme/widget", "2026-W34") == "openhands/agents-md-2026-W34"


def test_a_taken_branch_name_is_skipped(main, monkeypatch):
    taken = {"openhands/agents-md-2026-W34"}

    def fake(token, method, path, params=None, body=None):
        branch = path.split("/git/ref/heads/", 1)[1]
        if branch in taken:
            return {"ref": branch}, {}
        raise _http_error(404)

    monkeypatch.setattr(main, "_github_request", fake)

    assert main._branch_name("tok", "acme/widget", "2026-W34") == "openhands/agents-md-2026-W34-2"


# ── Declining to work ─────────────────────────────────────────────────────────


def test_only_this_automations_pull_requests_count_as_in_flight(main, monkeypatch):
    """Someone else's open pull request must not silence the automation, and its
    own must."""
    monkeypatch.setattr(
        main,
        "_github_paginate",
        lambda token, path, params=None: [
            {"number": 1, "head": {"ref": "feature/something"}},
            {"number": 2, "head": {"ref": "openhands/agents-md-2026-W33"}},
            {"number": 3, "head": {"ref": "openhands/issue-42"}},
        ],
    )

    in_flight = main._open_pull_requests_from_this_automation("tok", "acme/widget")

    assert [pr["number"] for pr in in_flight] == [2]


def test_a_listing_failure_does_not_claim_a_pull_request_is_open(main, monkeypatch):
    """Failing closed here would mean an API blip silently skips the week."""

    def boom(*args, **kwargs):
        raise RuntimeError("GitHub unreachable")

    monkeypatch.setattr(main, "_github_paginate", boom)

    assert main._open_pull_requests_from_this_automation("tok", "acme/widget") == []


# ── Create or update ──────────────────────────────────────────────────────────


def test_a_missing_agents_file_is_detected(main, monkeypatch):
    monkeypatch.setattr(main, "_github_request", lambda *a, **k: (_ for _ in ()).throw(_http_error(404)))

    assert main._agents_file_state("tok", "acme/widget", "main") == "missing"
    assert main._pull_request_title("missing") == "docs: add AGENTS.md"


def test_an_unreadable_answer_is_treated_as_present(main, monkeypatch):
    """Proposing to "add" a file that already exists reads worse than the
    reverse, so an API failure resolves to update."""
    monkeypatch.setattr(main, "_github_request", lambda *a, **k: (_ for _ in ()).throw(_http_error(500)))

    assert main._agents_file_state("tok", "acme/widget", "main") == "present"
    assert main._pull_request_title("present") == "docs: update AGENTS.md"


# ── The prompt ────────────────────────────────────────────────────────────────


def _prompt(main, state="present"):
    return main._build_maintenance_prompt(
        "acme/widget", state, "openhands/agents-md-2026-W34", "main", "abc123", "2026-W34"
    )


def test_the_prompt_asks_for_an_edit_not_a_rewrite(main):
    prompt = _prompt(main)

    assert "update it so it matches" in prompt
    assert "This is an edit, not a rewrite" in prompt
    assert "someone else's writing" in prompt


def test_the_prompt_states_what_belongs_in_the_file(main):
    """The rules are the ones the agent-memory skill sets out."""
    prompt = _prompt(main)

    assert "task-specific" in prompt
    assert "have not verified" in prompt
    assert "No secrets" in prompt


def test_the_prompt_allows_doing_nothing(main):
    """Most weeks the file is fine, and an edit made to look busy is worse."""
    prompt = _prompt(main)

    assert "change nothing, open nothing" in prompt


def test_the_prompt_tells_the_agent_to_open_the_pull_request(main):
    prompt = _prompt(main)

    assert "x-access-token:$GITHUB_PERSONAL_ACCESS_TOKEN" in prompt
    assert "gh pr create --repo acme/widget --base main --head openhands/agents-md-2026-W34" in prompt
    assert "--draft" in prompt
    assert "GITHUB_PR_OPENED" in prompt


def test_a_ready_for_review_configuration_drops_the_draft_flag(main, monkeypatch):
    monkeypatch.setattr(main, "DRAFT_PULL_REQUEST", False)
    prompt = _prompt(main)

    assert "--draft" not in prompt
    assert "ready for review" in prompt


def test_the_prompt_keeps_the_untrusted_input_boundary(main):
    prompt = _prompt(main)

    assert "untrusted input" in prompt
    assert "repositories other than acme/widget" in prompt


# ── Configuration ─────────────────────────────────────────────────────────────


def test_config_json_overrides_the_constants(main, tmp_path):
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "repos": ["acme/one"],
                "branch_prefix": "bot/agents",
                "pull_request_mode": "ready",
                "max_new_per_run": 2,
                "agent_secret_names": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
            }
        )
    )

    config = main.load_config(tmp_path)

    assert config["branch_prefix"] == "bot/agents"
    assert config["pull_request_mode"] == "ready"


def test_the_github_token_is_forwarded_by_default(main, monkeypatch):
    monkeypatch.setattr(
        main,
        "_list_secret_names",
        lambda a, k: [{"name": "GITHUB_PERSONAL_ACCESS_TOKEN"}, {"name": "AWS_SECRET_ACCESS_KEY"}],
    )

    assert main.AGENT_SECRET_NAMES == ["GITHUB_PERSONAL_ACCESS_TOKEN"]
    assert list(main._build_secrets_payload("http://agent", "key")) == [
        "GITHUB_PERSONAL_ACCESS_TOKEN"
    ]


# ── Files on disk ─────────────────────────────────────────────────────────────


def test_the_clone_lives_under_its_own_root(main):
    path = main._checkout_path("acme/widget", "2026-W34")

    assert path.parent.parent == main._checkouts_root()
    assert str(path).endswith("agents-md/acme__widget/2026-W34")


def test_a_path_outside_the_checkout_root_is_never_removed(main, monkeypatch, tmp_path):
    outside = tmp_path / "precious"
    outside.mkdir()
    rec = {"workspace_dir": str(outside), "conversation_id": "conv-1"}
    monkeypatch.setattr(main, "conversation_status", lambda *a: "finished")

    assert main._release_checkout(rec, "http://agent", "key") is True
    assert outside.exists()


def test_a_running_conversation_keeps_its_clone(main, monkeypatch):
    checkout = main._checkout_path("acme/widget", "2026-W34")
    checkout.mkdir(parents=True)
    rec = {"workspace_dir": str(checkout), "conversation_id": "conv-1"}
    monkeypatch.setattr(main, "conversation_status", lambda *a: "running")

    assert main._release_checkout(rec, "http://agent", "key") is False
    assert checkout.exists()


def _init_repo(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    run = lambda *a: subprocess.run(["git", *a], cwd=path, check=True, capture_output=True)
    run("init", "-q", "-b", "main")
    run("config", "user.name", "Test")
    run("config", "user.email", "test@example.com")
    (path / "README.md").write_text("base\n")
    run("add", "-A")
    run("commit", "-q", "-m", "base")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_an_edited_agents_file_is_committed_and_counted(main, tmp_path):
    checkout = tmp_path / "clone"
    base = _init_repo(checkout)
    (checkout / "AGENTS.md").write_text("# AGENTS\n\nRun `pytest`.\n")

    assert main._commit_agent_work(checkout, base) == 1


def test_an_untouched_repository_produces_no_commits(main, tmp_path):
    """No commits is the expected weekly outcome, not a failure."""
    checkout = tmp_path / "clone"
    base = _init_repo(checkout)

    assert main._commit_agent_work(checkout, base) == 0


# ── Pull request body ─────────────────────────────────────────────────────────


def test_the_pull_request_body_dates_the_run_and_discloses_the_agent(main):
    body = main._pull_request_body("acme/widget", "Refreshed the test command.", "http://oh/c/1", "2026-W34")

    assert "Refreshed the test command." in body
    assert "2026-W34" in body
    assert "_This pull request was opened by an AI agent (OpenHands)._" in body
