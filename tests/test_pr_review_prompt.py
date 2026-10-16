import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

from test_pr_review_review_context import _load_agent_script_module


def _load_prompt_module():
    script_path = (
        Path(__file__).parent.parent
        / "plugins"
        / "pr-review"
        / "scripts"
        / "prompt.py"
    )
    spec = importlib.util.spec_from_file_location("pr_review_prompt", script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["pr_review_prompt"] = module
    spec.loader.exec_module(module)
    return module


def _format_prompt(
    *,
    require_evidence: bool,
    use_sub_agents: bool = False,
    repo_name: str = "OpenHands/extensions",
    require_pinned_actions: bool = False,
) -> str:
    module = _load_prompt_module()
    return module.format_prompt(
        skill_trigger="/codereview",
        title="Add evidence enforcement",
        body="## Summary\nAdds stricter review guidance.",
        repo_name=repo_name,
        base_branch="main",
        head_branch="feature/evidence",
        pr_number="102",
        commit_id="abc123",
        diff="diff --git a/file b/file",
        review_context="",
        require_evidence=require_evidence,
        use_sub_agents=use_sub_agents,
        require_pinned_actions=require_pinned_actions,
    )


def test_prompt_with_roasted_trigger():
    """Verify the backward-compatibility trigger alias works."""
    module = _load_prompt_module()
    prompt = module.format_prompt(
        skill_trigger="/codereview-roasted",
        title="Test PR",
        body="Test body",
        repo_name="owner/repo",
        base_branch="main",
        head_branch="feature",
        pr_number="1",
        commit_id="abc123",
        diff="test diff",
        review_context="",
        require_evidence=False,
    )
    assert "/codereview-roasted" in prompt


def test_prompt_instructs_reading_repo_guidance():
    """The reviewer must be told to read AGENTS.md (and other guideline docs)
    to understand the repo before reviewing."""
    prompt = _format_prompt(require_evidence=False)

    assert "AGENTS.md" in prompt
    assert "MUST read" in prompt
    assert "CONTRIBUTING.md" in prompt
    assert "inspect how the affected feature or code path works" in prompt
    assert "concrete failure on the current head" in prompt


def test_format_prompt_omits_evidence_requirements_by_default():
    prompt = _format_prompt(require_evidence=False)

    assert "## PR Description Evidence Requirement" not in prompt
    assert "real code path end-to-end" not in prompt
    assert "https://app.all-hands.dev/conversations/{conversation_id}" not in prompt


def test_format_prompt_includes_evidence_requirements_when_enabled():
    prompt = _format_prompt(require_evidence=True)

    assert "## PR Description Evidence Requirement" in prompt
    assert "`Evidence` section" in prompt
    assert "screenshot or video" in prompt
    assert "real code path end-to-end" in prompt
    assert "unit test output" in prompt
    assert "https://app.all-hands.dev/conversations/{conversation_id}" in prompt


# --- Sub-agent delegation prompt tests ---


def test_format_prompt_uses_standard_prompt_by_default():
    prompt = _format_prompt(require_evidence=False, use_sub_agents=False)

    # Standard prompt should NOT mention delegation or sub-agents
    assert "review coordinator" not in prompt
    assert "TaskToolSet" not in prompt
    assert "file_reviewer" not in prompt
    # Standard prompt should contain the normal review instruction
    assert "Analyze the changes and post your review" in prompt


def test_format_prompt_appends_delegation_suffix_when_enabled():
    prompt = _format_prompt(require_evidence=False, use_sub_agents=True)

    # Should still include the base prompt content
    assert "Add evidence enforcement" in prompt
    assert "OpenHands/extensions" in prompt
    assert "abc123" in prompt
    assert "diff --git a/file b/file" in prompt
    assert "Analyze the changes and post your review" in prompt
    # Delegation suffix appended
    assert "Sub-agent Delegation" in prompt
    assert "file_reviewer" in prompt
    assert "task" in prompt.lower()


def test_delegation_suffix_with_evidence():
    prompt = _format_prompt(require_evidence=True, use_sub_agents=True)

    assert "Sub-agent Delegation" in prompt
    assert "## PR Description Evidence Requirement" in prompt


def test_file_reviewer_skill_content():
    module = _load_prompt_module()
    content = module.FILE_REVIEWER_SKILL

    assert "file-level code reviewer" in content
    # Concrete findings only, while retaining limited-impact defects.
    assert "concrete failure" in content
    # JSON schema documented
    assert "path" in content
    assert "line" in content
    assert "severity" in content
    assert "body" in content
    assert "critical" in content
    assert '`"minor"`' in content
    assert '`"nit"`' not in content
    # Tool access documented
    assert "terminal" in content
    assert "file_editor" in content
    # Sub-agent returns results via finish tool
    assert "finish" in content


# --- action.yml default guard ---


def test_use_sub_agents_defaults_to_false():
    """Guard: use-sub-agents must default to 'false' until cost issues are resolved (#208)."""
    action_yml = (
        Path(__file__).parent.parent / "plugins" / "pr-review" / "action.yml"
    )
    with open(action_yml) as f:
        action = yaml.safe_load(f)

    default = action["inputs"]["use-sub-agents"]["default"]
    assert default == "false", (
        f"use-sub-agents default should be 'false' (got {default!r}). "
        "See https://github.com/OpenHands/extensions/issues/208"
    )


# --- Third-party action pinning ---


def _pinning_section(prompt: str) -> str:
    start = prompt.index("## Third-party Action Pinning")
    end = prompt.find("\n## ", start + 1)
    return prompt[start:] if end == -1 else prompt[start:end]


def test_format_prompt_omits_action_pinning_rule_by_default():
    prompt = _format_prompt(require_evidence=False, repo_name="acme/widgets")

    assert "## Third-party Action Pinning" not in prompt
    assert "40-character commit SHA" not in prompt


def test_action_pinning_rule_exempts_github_and_the_reviewed_repo_owner():
    section = _pinning_section(
        _format_prompt(
            require_evidence=False,
            repo_name="acme/widgets",
            require_pinned_actions=True,
        )
    )

    assert "40-character commit SHA" in section
    assert "`action.yml`" in section
    assert "added or modified `uses:`" in section
    assert "`actions`, `github`, or `acme` exactly, ignoring case" in section
    assert "`./`" in section
    assert "`acme-actions`" in section
    assert "`docker://`" in section
    assert "OpenHands" not in section


def test_require_pinned_actions_defaults_to_false_and_maps_to_env():
    action_yml = (
        Path(__file__).parent.parent / "plugins" / "pr-review" / "action.yml"
    )
    with open(action_yml) as f:
        action = yaml.safe_load(f)

    assert action["inputs"]["require-pinned-actions"]["default"] == "false"
    run_step = next(
        step for step in action["runs"]["steps"] if step["name"] == "Run PR review"
    )
    assert run_step["env"]["REQUIRE_PINNED_ACTIONS"] == (
        "${{ inputs.require-pinned-actions }}"
    )


@pytest.mark.parametrize(
    ("env_value", "expected"), [(None, False), ("false", False), ("true", True)]
)
def test_require_pinned_actions_env_reaches_config(monkeypatch, env_value, expected):
    agent_script = _load_agent_script_module()
    for name, value in {
        "GITHUB_TOKEN": "test-token",
        "LLM_API_KEY": "test-key",
        "PR_NUMBER": "102",
        "PR_TITLE": "Pin actions",
        "PR_BASE_BRANCH": "main",
        "PR_HEAD_BRANCH": "feature/pinning",
        "REPO_NAME": "acme/widgets",
    }.items():
        monkeypatch.setenv(name, value)
    if env_value is None:
        monkeypatch.delenv("REQUIRE_PINNED_ACTIONS", raising=False)
    else:
        monkeypatch.setenv("REQUIRE_PINNED_ACTIONS", env_value)

    config = agent_script.validate_environment()

    assert config["require_pinned_actions"] is expected
