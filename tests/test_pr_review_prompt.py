import importlib.util
import sys
from pathlib import Path


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
    *, require_evidence: bool, use_sub_agents: bool = False
) -> str:
    module = _load_prompt_module()
    return module.format_prompt(
        skill_trigger="/codereview",
        title="Add evidence enforcement",
        body="## Summary\nAdds stricter review guidance.",
        repo_name="OpenHands/extensions",
        base_branch="main",
        head_branch="feature/evidence",
        pr_number="102",
        commit_id="abc123",
        diff="diff --git a/file b/file",
        review_context="",
        require_evidence=require_evidence,
        use_sub_agents=use_sub_agents,
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


def test_get_file_reviewer_skill_content():
    module = _load_prompt_module()
    content = module.get_file_reviewer_skill_content()

    assert "file-level code reviewer" in content
    # Unified review style (no more standard/roasted split)
    assert "pragmatic" in content
    # JSON schema documented
    assert "path" in content
    assert "line" in content
    assert "severity" in content
    assert "body" in content
    assert "critical" in content
    # Tool access documented
    assert "terminal" in content
    assert "file_editor" in content
    # Must not touch GitHub API
    assert "Do NOT post anything to the GitHub" in content
