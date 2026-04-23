"""Test that risk/safety evaluation is integrated into the unified code review skill."""

from pathlib import Path


def get_repo_root():
    return Path(__file__).parent.parent


def get_code_review_skill():
    return (get_repo_root() / "skills" / "code-review" / "SKILL.md").read_text()


def get_risk_evaluation_reference():
    return (
        get_repo_root()
        / "skills"
        / "code-review"
        / "references"
        / "risk-evaluation.md"
    ).read_text()


class TestRiskEvaluationReference:
    """Verify the risk-evaluation.md reference file is complete."""

    def test_reference_file_exists(self):
        path = (
            get_repo_root()
            / "skills"
            / "code-review"
            / "references"
            / "risk-evaluation.md"
        )
        assert path.exists()

    def test_has_all_risk_levels(self):
        content = get_risk_evaluation_reference()
        assert "Low Risk" in content
        assert "Medium Risk" in content
        assert "High Risk" in content

    def test_has_risk_factors(self):
        content = get_risk_evaluation_reference()
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
        content = get_risk_evaluation_reference()
        assert "not auto-merg" in content.lower()
        assert "human" in content.lower()

    def test_has_repo_specific_risk_rules(self):
        content = get_risk_evaluation_reference()
        assert "AGENTS.md" in content
        assert "repo-specific" in content.lower() or "Repo-specific" in content

    def test_has_risk_assessment_output_format(self):
        content = get_risk_evaluation_reference()
        assert "Risk Assessment" in content


class TestCodeReviewSkillReferencesRisk:
    """Verify the unified code-review skill references the risk evaluation."""

    def test_has_risk_evaluation_scenario(self):
        content = get_code_review_skill()
        assert "Risk and Safety Evaluation" in content

    def test_references_risk_evaluation_file(self):
        content = get_code_review_skill()
        assert "references/risk-evaluation.md" in content

    def test_risk_section_appears_after_dependency_section(self):
        content = get_code_review_skill()
        dep_pos = content.index("8. **Dependency Changes**")
        risk_pos = content.index("9. **Risk and Safety Evaluation**")
        assert risk_pos > dep_pos

    def test_always_include_risk_instruction(self):
        content = get_code_review_skill()
        assert "Always include the" in content
        assert "Risk and Safety Evaluation" in content

    def test_has_risk_assessment_in_output_format(self):
        content = get_code_review_skill()
        assert "RISK ASSESSMENT" in content
