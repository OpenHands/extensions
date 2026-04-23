"""Test that skills with commands/ can be loaded as plugins.

Skills listed in the marketplace that have a commands/ directory need a
.plugin/plugin.json manifest and vendor symlinks so that Codex and Claude
Code can discover and load them.  This test ensures that those skills are
properly configured.

Regression test for: https://github.com/OpenHands/extensions/issues/201
"""

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
PLUGINS_DIR = REPO_ROOT / "plugins"

REQUIRED_MANIFEST_FIELDS = ["name", "description", "author", "version"]
VENDOR_SYMLINKS = [".claude-plugin", ".codex-plugin"]


def _skills_with_commands():
    """Yield skill directory paths that contain a commands/ subdirectory."""
    if not SKILLS_DIR.is_dir():
        return
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        if (skill_dir / "commands").is_dir() and (skill_dir / ".plugin" / "plugin.json").exists():
            yield skill_dir


def _all_dirs_with_plugin_manifest():
    """Yield directories (plugins/ and skills/) that have .plugin/plugin.json."""
    for base in [PLUGINS_DIR, SKILLS_DIR]:
        if not base.is_dir():
            continue
        for entry_dir in sorted(base.iterdir()):
            if not entry_dir.is_dir() or entry_dir.name.startswith("."):
                continue
            manifest = entry_dir / ".plugin" / "plugin.json"
            if manifest.exists():
                yield entry_dir


class TestIteratePluginLoading:
    """Verify the iterate skill can be loaded as a plugin (issue #201)."""

    def test_iterate_has_plugin_manifest(self):
        """The iterate skill must have .plugin/plugin.json."""
        manifest = SKILLS_DIR / "iterate" / ".plugin" / "plugin.json"
        assert manifest.exists(), (
            "skills/iterate/.plugin/plugin.json is missing — "
            "Codex and Claude Code require this manifest to load the plugin."
        )

    def test_iterate_manifest_is_valid(self):
        """The iterate manifest must have all required fields."""
        manifest = SKILLS_DIR / "iterate" / ".plugin" / "plugin.json"
        data = json.loads(manifest.read_text())
        for field in REQUIRED_MANIFEST_FIELDS:
            assert field in data, f"iterate plugin.json missing '{field}'"
        assert data["name"] == "iterate"
        assert isinstance(data["author"], dict), "author must be an object"
        assert "name" in data["author"], "author must have a 'name' field"

    def test_iterate_has_vendor_symlinks(self):
        """The iterate skill must have .claude-plugin and .codex-plugin symlinks."""
        iterate_dir = SKILLS_DIR / "iterate"
        for vendor in VENDOR_SYMLINKS:
            link = iterate_dir / vendor
            assert link.is_symlink(), f"skills/iterate/{vendor} must be a symlink"
            assert link.resolve() == (iterate_dir / ".plugin").resolve(), (
                f"skills/iterate/{vendor} must point to .plugin"
            )

    def test_iterate_loads_as_sdk_plugin(self):
        """The iterate skill must load via Plugin.load() without error."""
        from openhands.sdk.plugin.plugin import Plugin

        plugin = Plugin.load(SKILLS_DIR / "iterate")
        assert plugin.name == "iterate"
        assert plugin.version == "1.0.0"
        assert len(plugin.commands) > 0
        command_names = {c.name for c in plugin.commands}
        assert "iterate" in command_names
        assert "babysit" in command_names
        assert "verify" in command_names


class TestVendorSymlinksForManifests:
    """Every directory with .plugin/ must have vendor symlinks."""

    @pytest.fixture(
        params=list(_all_dirs_with_plugin_manifest()),
        ids=lambda d: f"{d.parent.name}/{d.name}",
    )
    def dir_with_manifest(self, request):
        return request.param

    def test_has_vendor_symlinks(self, dir_with_manifest):
        """Directories with .plugin/ must have .claude-plugin and .codex-plugin symlinks."""
        for vendor in VENDOR_SYMLINKS:
            link = dir_with_manifest / vendor
            assert link.is_symlink(), (
                f"{link.relative_to(REPO_ROOT)} must be a symlink to .plugin"
            )
            assert link.resolve() == (dir_with_manifest / ".plugin").resolve(), (
                f"{link.relative_to(REPO_ROOT)} must point to .plugin"
            )
