"""Test that the code-review skill includes risk/safety evaluation."""

from pathlib import Path


def get_repo_root():
    return Path(__file__).parent.parent


def get_skill_content():
    skill_path = get_repo_root() / "skills" / "code-review" / "SKILL.md"
    return skill_path.read_text()


class TestRiskEvaluationSection:
    """Verify the code-review skill contains risk/safety evaluation guidance."""

    def test_has_risk_evaluation_scenario(self):
        content = get_skill_content()
        assert "5. Risk and Safety Evaluation" in content

    def test_has_all_risk_levels(self):
        content = get_skill_content()
        assert "Low Risk" in content
        assert "Medium Risk" in content
        assert "High Risk" in content

    def test_has_risk_factors(self):
        content = get_skill_content()
        factors = [
            "Pattern conformance",
            "Security sensitivity",
            "Infrastructure dependencies",
            "Blast radius",
            "Core system impact",
        ]
        for factor in factors:
            assert factor in content, f"Missing risk factor: {factor}"

    def test_has_high_risk_escalation_guidance(self):
        content = get_skill_content()
        assert "not auto-merg" in content.lower()
        assert "human" in content.lower()

    def test_has_repo_specific_risk_rules(self):
        content = get_skill_content()
        assert "AGENTS.md" in content
        assert "repo-specific" in content.lower() or "Repo-specific" in content

    def test_has_risk_assessment_output_format(self):
        content = get_skill_content()
        assert "Risk Assessment" in content

    def test_risk_section_appears_after_testing_section(self):
        content = get_skill_content()
        testing_pos = content.index("4. Testing and Behavior Verification")
        risk_pos = content.index("5. Risk and Safety Evaluation")
        assert risk_pos > testing_pos

    def test_always_include_risk_instruction(self):
        content = get_skill_content()
        assert "Always include the Risk and Safety Evaluation" in content
