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
        skill_trigger="/codereview-roasted",
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
    assert "DelegateTool" not in prompt
    assert "file_reviewer" not in prompt
    # Standard prompt should contain the normal review instruction
    assert "Analyze the changes and post your review" in prompt


def test_format_prompt_uses_sub_agent_prompt_when_enabled():
    prompt = _format_prompt(require_evidence=False, use_sub_agents=True)

    # Sub-agent prompt should mention coordination and delegation
    assert "review coordinator" in prompt
    assert "DelegateTool" in prompt
    assert "Spawn sub-agents" in prompt
    assert "file_reviewer" in prompt
    # Sub-agent prompt should still include the PR info
    assert "Add evidence enforcement" in prompt
    assert "OpenHands/extensions" in prompt
    assert "abc123" in prompt
    # Should include the diff
    assert "diff --git a/file b/file" in prompt


def test_sub_agent_prompt_includes_evidence_when_enabled():
    prompt = _format_prompt(require_evidence=True, use_sub_agents=True)

    assert "review coordinator" in prompt
    assert "## PR Description Evidence Requirement" in prompt


def test_get_file_reviewer_skill_content_standard():
    module = _load_prompt_module()
    content = module.get_file_reviewer_skill_content("standard")

    assert "file-level code reviewer" in content
    assert "Balanced review" in content
    assert "JSON array" in content


def test_get_file_reviewer_skill_content_roasted():
    module = _load_prompt_module()
    content = module.get_file_reviewer_skill_content("roasted")

    assert "file-level code reviewer" in content
    assert "Linus Torvalds" in content
    assert "JSON array" in content
