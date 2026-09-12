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
