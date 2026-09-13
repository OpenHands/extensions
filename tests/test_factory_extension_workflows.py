"""Canonical workflow reuse and fail-closed evidence matching."""

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]


def load(name):
    path = ROOT / "skills/github-software-factory/scripts" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_review_reuses_canonical_workflow_in_any_workspace(tmp_path):
    workflow = load("extension_workflows")
    pr = {"number": 7, "title": "Example", "head": {"sha": "a" * 40}}
    canonical = workflow.module("skills/github-pr-reviewer/scripts/main.py")
    expected = canonical._build_review_prompt("owner/repo", pr, "a" * 40, {"id": "run"})
    prompts = []
    for workspace in (tmp_path / "local", tmp_path / "container"):
        prompt = workflow.review_prompt("owner/repo", pr, workspace, "run")
        assert prompt.startswith(expected)
        prompts.append(prompt.replace(str(workspace), "WORKSPACE"))
    assert prompts[0] == prompts[1]


def test_qa_loads_canonical_prompt_and_skills(tmp_path):
    workflow = load("extension_workflows")
    pr = {
        "number": 7,
        "title": "Example",
        "head": {"sha": "a" * 40, "ref": "feature"},
        "base": {"ref": "main"},
    }
    prompt = workflow.qa_prompt("owner/repo", pr, tmp_path, "run", "patch", {})
    assert (
        workflow.module("plugins/qa-changes/scripts/prompt.py").format_prompt(
            "Example", "", "owner/repo", "main", "feature", "7", "a" * 40, "patch"
        )
        in prompt
    )
    for name in ("qa-changes", "github-pr-review"):
        assert (ROOT / f"skills/{name}/SKILL.md").read_text() in prompt


def report(**overrides):
    return {
        "id": 42,
        "commit_id": "a" * 40,
        "state": "COMMENTED",
        "body": "<!-- factory-run:run:review -->\n✅ APPROVED",
        **overrides,
    }


@pytest.mark.parametrize(
    "overrides,old",
    [
        ({"commit_id": "b" * 40}, set()),
        ({}, {42}),
        ({"body": "✅ APPROVED"}, set()),
        ({"state": "PENDING"}, set()),
    ],
)
def test_stale_unrelated_and_unpublished_reviews_cannot_accept(overrides, old):
    workflow = load("extension_workflows")
    with pytest.raises(RuntimeError):
        workflow.posted_report([report(**overrides)], old, "a" * 40, "run", "review")


@pytest.mark.parametrize(
    "stage,body,expected",
    [
        ("review", "✅ APPROVED", True),
        ("review", "✅ APPROVED\n🔄 CHANGES REQUESTED", False),
        ("review", "The earlier review said ✅ APPROVED", False),
        ("qa", "## ✅ QA Report: PASS\nEvidence", True),
        ("qa", "## ⚠️ QA Report: PASS WITH ISSUES", False),
        ("qa", "## QA Report: PARTIAL", False),
        ("qa", "PASS", False),
    ],
)
def test_only_unambiguous_canonical_verdicts_pass(stage, body, expected):
    assert load("extension_workflows").report_passed({"body": body}, stage) is expected


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://attacker.test",
        "repos/other/repo/pulls/7",
        "repos/owner/repo/../secrets",
        "repos/owner/repo/pulls/%37",
        "repos/owner/repo/pulls/7#fragment",
    ],
)
def test_transport_rejects_other_repositories_urls_and_encoded_routes(endpoint):
    with pytest.raises(ValueError):
        load("scoped_gh").repository_path(endpoint, "owner/repo")


def test_transport_keeps_repository_relative_path():
    assert (
        load("scoped_gh").repository_path(
            "/repos/owner/repo/pulls/7/files?per_page=100", "owner/repo"
        )
        == "/pulls/7/files?per_page=100"
    )


def test_gateway_grant_is_materialized_only_from_selected_environment(
    tmp_path, monkeypatch
):
    script = load("scoped_gh")
    config = {"token_env": "FACTORY_REVIEWER_GRANT"}
    path = tmp_path / "config.json"
    path.write_text('{"token_env":"FACTORY_REVIEWER_GRANT"}')
    monkeypatch.setenv("FACTORY_REVIEWER_GRANT", "reviewer-fixture-grant")
    monkeypatch.setenv("FACTORY_DEVELOPER_GRANT", "developer-fixture-grant")
    assert script.gateway_token(config, path) == "reviewer-fixture-grant"
    saved = tmp_path / ".factory-gateway-token"
    assert saved.stat().st_mode & 0o777 == 0o600
    monkeypatch.delenv("FACTORY_REVIEWER_GRANT")
    assert script.gateway_token(config, path) == "reviewer-fixture-grant"
    assert "developer-fixture-grant" not in saved.read_text()
    assert "fixture-grant" not in path.read_text()


def test_missing_profile_grant_cannot_fall_back_to_another_secret(
    tmp_path, monkeypatch
):
    script = load("scoped_gh")
    monkeypatch.delenv("FACTORY_REVIEWER_GRANT", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "broad-token")
    with pytest.raises(ValueError, match="not supplied"):
        script.gateway_token(
            {"token_env": "FACTORY_REVIEWER_GRANT"}, tmp_path / "config.json"
        )


def test_bundler_rejects_embedded_credentials(tmp_path, monkeypatch):
    import json

    scripts = ROOT / "skills/github-software-factory/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"token": "inline-credential"}))
    with pytest.raises(ValueError, match="profile secret"):
        load("build_bundle").build(config, tmp_path / "bundle.tar.gz")


def test_coordinator_implementation_prompt_has_no_direct_publication_commands(tmp_path):
    prompt = load("extension_workflows").implementation_prompt(
        "owner/repo",
        {"number": 1, "title": "Task"},
        "factory/issue-1",
        "a" * 40,
        tmp_path,
        [],
    )
    assert "GITHUB_PERSONAL_ACCESS_TOKEN" not in prompt
    assert "git push" not in prompt
    assert "gh pr create" not in prompt
    assert "coordinator publishes" in prompt
    assert str(tmp_path / "bin/gh") in prompt


def test_scoped_transport_accepts_commit_comparisons():
    path = "/compare/" + "a" * 40 + "..." + "b" * 40
    assert (
        load("scoped_gh").repository_path("repos/owner/repo" + path, "owner/repo")
        == path
    )
