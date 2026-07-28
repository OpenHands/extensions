"""Contract tests for the refactoring-advisor skill."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "refactoring-advisor"
SKILL_PATH = SKILL_DIR / "SKILL.md"
TEMPLATE_PATH = SKILL_DIR / "references" / "report-template.md"


def _frontmatter_and_body(path: Path) -> tuple[dict, str]:
    text = path.read_text()
    _, frontmatter, body = text.split("---", 2)
    return yaml.safe_load(frontmatter), body


def test_refactoring_advisor_has_required_triggers_and_scope():
    metadata, body = _frontmatter_and_body(SKILL_PATH)
    references = "\n".join(path.read_text() for path in (SKILL_DIR / "references").glob("*.md"))
    searchable = f"{metadata['description']}\n{body}\n{references}".lower()

    for phrase in (
        "refactor",
        "code smells",
        "technical debt",
        "extract method",
        "reduce complexity",
        "clean up this codebase",
        "dependency injection",
    ):
        assert phrase in searchable

    for language in ("java", "python", "typescript", "c#"):
        assert language in searchable

    assert len(SKILL_PATH.read_text().splitlines()) < 500


def test_refactoring_advisor_enforces_output_only_and_di_evaluation():
    _, body = _frontmatter_and_body(SKILL_PATH)
    template = TEMPLATE_PATH.read_text()
    searchable = f"{body}\n{template}".lower()

    assert "do not provide implementation patches" in searchable
    assert "executable pseudocode" in searchable
    assert "every proposal contains an explicit dependency injection decision" in searchable
    assert "di evaluation" in searchable
    assert "prioritized action plan" in searchable


def test_refactoring_advisor_references_exist():
    for relative_path in (
        "references/discovery.md",
        "references/smells-and-strategies.md",
        "references/report-template.md",
        ".plugin/plugin.json",
        "README.md",
    ):
        assert (SKILL_DIR / relative_path).is_file(), relative_path
