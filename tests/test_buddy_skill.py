"""Tests for the buddy skill and marketplace registration."""

import json
from pathlib import Path

from openhands.sdk.context.skills import Skill
from openhands.sdk.context.skills.trigger import KeywordTrigger
from openhands.sdk.plugin import Marketplace


REPO_ROOT = Path(__file__).resolve().parent.parent
BUDDY_SKILL_PATH = REPO_ROOT / "skills" / "buddy" / "SKILL.md"
DEFAULT_MARKETPLACE_PATH = REPO_ROOT / "marketplaces" / "default.json"


def test_buddy_skill_loads_with_expected_trigger():
    """The buddy skill should load as a keyword-triggered skill."""
    skill = Skill.load(BUDDY_SKILL_PATH, skill_base_dir=REPO_ROOT / "skills" / "buddy")

    assert skill.name == "buddy"
    assert skill.description is not None and "/buddy" in skill.description
    assert isinstance(skill.trigger, KeywordTrigger)
    assert skill.trigger.keywords == ["/buddy"]


def test_default_marketplace_includes_buddy_skill():
    """The default marketplace should expose the buddy skill."""
    data = json.loads(DEFAULT_MARKETPLACE_PATH.read_text())
    marketplace = Marketplace.model_validate({**data, "path": str(REPO_ROOT)})

    buddy_entry = next(plugin for plugin in marketplace.plugins if plugin.name == "buddy")
    assert buddy_entry.source == "./buddy"
    assert buddy_entry.description is not None and "ASCII companion" in buddy_entry.description
