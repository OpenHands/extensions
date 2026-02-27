"""Test that marketplaces, skills, and plugins can be loaded by the SDK."""

from pathlib import Path

import pytest
from openhands.sdk.context.skills import Skill
from openhands.sdk.plugin import Marketplace, MarketplacePluginEntry


def get_repo_root():
    """Get the path to the repository root."""
    return Path(__file__).parent.parent


def get_all_skill_directories():
    """Get all skill directory names that have a SKILL.md file."""
    skills_dir = get_repo_root() / "skills"
    return [
        d for d in skills_dir.iterdir()
        if d.is_dir() and not d.name.startswith('.') and (d / "SKILL.md").exists()
    ]


class TestDefaultMarketplace:
    """Test that the default marketplace can be loaded by the SDK."""

    def test_marketplace_loads_with_sdk(self):
        """Verify the default marketplace can be loaded using SDK's Marketplace model."""
        marketplace_path = get_repo_root() / "marketplaces" / "default.json"
        
        # Load using SDK's pydantic model
        import json
        with open(marketplace_path) as f:
            data = json.load(f)
        
        marketplace = Marketplace.model_validate({**data, "path": str(get_repo_root())})
        
        assert marketplace.name == "default"
        assert marketplace.owner is not None
        assert marketplace.owner.name == "OpenHands"
        assert len(marketplace.plugins) > 0

    def test_all_plugin_entries_valid(self):
        """Verify all plugin entries can be validated as MarketplacePluginEntry."""
        marketplace_path = get_repo_root() / "marketplaces" / "default.json"
        
        import json
        with open(marketplace_path) as f:
            data = json.load(f)
        
        errors = []
        for plugin_data in data.get("plugins", []):
            try:
                entry = MarketplacePluginEntry.model_validate(plugin_data)
                assert entry.name, f"Plugin missing name"
                assert entry.source, f"Plugin {entry.name} missing source"
                assert entry.description, f"Plugin {entry.name} missing description"
            except Exception as e:
                errors.append(f"{plugin_data.get('name', 'unknown')}: {e}")
        
        assert len(errors) == 0, f"Plugin validation errors:\n" + "\n".join(errors)

    def test_marketplace_includes_all_skills(self):
        """Verify every skill directory is referenced in at least one marketplace."""
        import json

        marketplaces_dir = get_repo_root() / "marketplaces"
        marketplace_files = sorted(marketplaces_dir.glob("*.json"))
        assert len(marketplace_files) > 0, "No marketplace JSON files found"

        # Collect sources across all marketplaces
        all_sources = set()
        for mp_path in marketplace_files:
            with open(mp_path) as f:
                data = json.load(f)
            marketplace = Marketplace.model_validate({**data, "path": str(get_repo_root())})
            for plugin in marketplace.plugins:
                source = plugin.source if isinstance(plugin.source, str) else ""
                # Normalize: strip leading "./" and resolve parent refs to get the leaf name
                name = Path(source).name
                all_sources.add(name)

        # Get all skill directories
        skill_dirs = {d.name for d in get_all_skill_directories()}

        missing = skill_dirs - all_sources
        assert len(missing) == 0, f"Skills not in any marketplace: {sorted(missing)}"


class TestSkillsLoadWithSDK:
    """Test that all skills can be loaded by the SDK."""

    def test_all_skills_load_with_sdk(self):
        """Verify all SKILL.md files can be loaded using SDK's Skill.load()."""
        skill_dirs = get_all_skill_directories()
        
        errors = []
        for skill_dir in skill_dirs:
            skill_path = skill_dir / "SKILL.md"
            try:
                skill = Skill.load(skill_path, skill_base_dir=skill_dir)
                assert skill.name, f"Skill {skill_dir.name} has no name"
                assert skill.content, f"Skill {skill_dir.name} has no content"
            except Exception as e:
                errors.append(f"{skill_dir.name}: {e}")
        
        assert len(errors) == 0, (
            f"Failed to load {len(errors)} skills:\n" + "\n".join(errors)
        )

    def test_skills_have_valid_metadata(self):
        """Verify all skills have valid metadata (name, description)."""
        skill_dirs = get_all_skill_directories()
        
        missing_metadata = []
        for skill_dir in skill_dirs:
            skill_path = skill_dir / "SKILL.md"
            try:
                skill = Skill.load(skill_path, skill_base_dir=skill_dir)
                if not skill.description:
                    missing_metadata.append(f"{skill_dir.name}: missing description")
            except Exception:
                pass  # Already caught in test_all_skills_load_with_sdk
        
        assert len(missing_metadata) == 0, (
            f"Skills with missing metadata:\n" + "\n".join(missing_metadata)
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
