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


def _format_prompt(*, require_evidence: bool) -> str:
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
