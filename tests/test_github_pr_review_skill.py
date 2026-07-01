"""Tests for the github-pr-review skill content.

These tests guard the guidance the agent reads when it builds a GitHub review
with inline suggestions. The skill must teach the agent how GitHub
``suggestion`` blocks actually behave (range replacement), so accepted
suggestions don't silently duplicate or delete lines, and so the prose
description always matches the resulting change.

See: https://github.com/OpenHands/extensions/issues/292
"""

from pathlib import Path

import pytest

SKILL_PATH = (
    Path(__file__).parent.parent / "skills" / "github-pr-review" / "SKILL.md"
)


@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def test_skill_file_exists():
    assert SKILL_PATH.is_file(), f"missing skill file: {SKILL_PATH}"


def test_skill_does_not_claim_suggestion_must_match_range_length(skill_text: str):
    """Regression: the old "same number of lines as the range" rule was wrong.

    GitHub replaces the targeted range with the suggestion body regardless of
    how many lines the body contains. Telling the agent the counts must match
    pushed it to either delete lines (when shrinking a block) or duplicate
    lines (when expanding one), depending on which side it adjusted to satisfy
    the bogus rule. The skill must no longer state that constraint.
    """
    forbidden_phrases = [
        "suggestion must have the same number of lines as the range",
        "must have the same number of lines as the range",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in skill_text, (
            f"SKILL.md still contains the misleading rule {phrase!r}; "
            "GitHub suggestions replace the range with any number of lines."
        )


def test_skill_explains_replace_semantics(skill_text: str):
    """The skill must say in plain language that suggestions REPLACE the range."""
    assert "How Suggestions Actually Work" in skill_text
    # Mention replacement explicitly so the agent does not treat the suggestion
    # body as "extra lines added on top of the original".
    lowered = skill_text.lower()
    assert "replace" in lowered
    assert "any number of lines" in lowered


def test_skill_covers_add_remove_change_patterns(skill_text: str):
    """The skill should give explicit recipes for the three intents that
    most commonly produced broken suggestions: changing, adding, and
    deleting lines. Without these, the agent invents wrong patterns.
    """
    for keyword in ("Change line", "Add", "Delete"):
        assert keyword in skill_text, (
            f"SKILL.md is missing guidance for intent {keyword!r}; "
            "see issue #292."
        )


def test_skill_warns_about_duplicated_and_deleted_lines(skill_text: str):
    """The skill must call out the two failure modes from issue #292:
    accepted suggestions that duplicate or remove lines."""
    lowered = skill_text.lower()
    assert "duplicat" in lowered, (
        "SKILL.md should warn about suggestions that duplicate lines."
    )
    # "disappear"/"disappearing" is unique to the failure-mode description in
    # the "Common Mistakes" section. The generic terms "delete" and "remove"
    # also appear in the recipe table for intentional deletions, so checking
    # for those would let the failure-mode guidance be removed silently.
    assert "disappear" in lowered, (
        "SKILL.md should warn about suggestions that silently drop lines "
        "(see 'Disappearing lines' under Common Mistakes)."
    )


def test_skill_requires_description_to_match_suggestion(skill_text: str):
    """The skill must explicitly require the prose description to match the
    actual code change in the suggestion block (the third bug from #292)."""
    lowered = skill_text.lower()
    assert any(phrase in lowered for phrase in ("description does not match", "prose description", "description must match"))
    # The text should connect the description to the resulting code change.
    assert (
        "match" in lowered
    ), "SKILL.md should say the description must match the change."


def test_skill_has_pre_post_verification_step(skill_text: str):
    """Before posting, the agent must verify the suggestion against the file."""
    assert "Mandatory Verification" in skill_text or "Verification" in skill_text
    # Should point the agent at the real file content, not just the diff.
    assert "sed -n" in skill_text or "read the actual file" in skill_text.lower()


def test_skill_offers_prose_fallback(skill_text: str):
    """When unsure, the agent should drop the suggestion block and use prose
    instead — a correct comment beats a broken one-click fix."""
    lowered = skill_text.lower()
    assert "prose" in lowered, (
        "SKILL.md should tell the agent to fall back to a prose comment "
        "when the suggestion cannot be verified."
    )
