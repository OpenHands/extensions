"""Test that skills listed in marketplaces can be loaded as Codex/Claude plugins.

Every marketplace entry that references a ``skills/`` directory needs a
``.plugin/plugin.json`` manifest and vendor manifests (``.codex-plugin``,
``.claude-plugin``) so that Codex and Claude Code can discover and load them.
A vendor manifest is either a symlink to ``.plugin/`` or a real directory
mirroring ``plugin.json`` (Codex install drops symlinked dirs; see issue #257).

Regression test for: https://github.com/OpenHands/extensions/issues/201
"""

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
PLUGINS_DIR = REPO_ROOT / "plugins"
MARKETPLACES_DIR = REPO_ROOT / "marketplaces"

REQUIRED_MANIFEST_FIELDS = ["name", "description", "author", "version"]
VENDOR_SYMLINKS = [".claude-plugin", ".codex-plugin"]


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


def _marketplace_skill_entries():
    """Yield (skill_name, source_path) for every marketplace entry under skills/."""
    for mp_file in sorted(MARKETPLACES_DIR.glob("*.json")):
        with open(mp_file) as f:
            data = json.load(f)
        for p in data.get("plugins", []):
            src = p["source"]
            if src.startswith("./skills/"):
                yield p["name"], REPO_ROOT / src.lstrip("./")


class TestAllMarketplaceSkillsHaveManifests:
    """Every skill listed in a marketplace must have a plugin manifest for Codex."""

    def test_all_marketplace_skills_have_plugin_json(self):
        """Every marketplace skill entry must have .plugin/plugin.json."""
        missing = []
        for name, path in _marketplace_skill_entries():
            manifest = path / ".plugin" / "plugin.json"
            if not manifest.exists():
                missing.append(name)
        assert not missing, (
            f"Skills missing .plugin/plugin.json (Codex can't load them): "
            f"{', '.join(missing)}"
        )

    def test_all_marketplace_skills_have_vendor_manifests(self):
        """Every marketplace skill with a manifest must have vendor manifests."""
        problems = []
        for name, path in _marketplace_skill_entries():
            if not (path / ".plugin" / "plugin.json").exists():
                continue
            for vendor in VENDOR_SYMLINKS:
                if not _vendor_manifest_ok(path, vendor):
                    problems.append(f"{name}/{vendor}")
        assert not problems, (
            f"Missing vendor manifests: {', '.join(problems)}"
        )

    def test_all_manifests_have_required_fields(self):
        """Every skill manifest must have name, description, author, version."""
        problems = []
        for name, path in _marketplace_skill_entries():
            manifest = path / ".plugin" / "plugin.json"
            if not manifest.exists():
                continue
            data = json.loads(manifest.read_text())
            for field in REQUIRED_MANIFEST_FIELDS:
                if field not in data:
                    problems.append(f"{name}: missing '{field}'")
            author = data.get("author")
            if not isinstance(author, dict):
                problems.append(f"{name}: 'author' must be an object")
            elif "name" not in author:
                problems.append(f"{name}: author missing 'name'")
        assert not problems, (
            f"Manifest validation errors:\n" + "\n".join(problems)
        )

    def test_manifest_name_matches_directory(self):
        """The 'name' in plugin.json must match the directory name."""
        problems = []
        for name, path in _marketplace_skill_entries():
            manifest = path / ".plugin" / "plugin.json"
            if not manifest.exists():
                continue
            data = json.loads(manifest.read_text())
            if data.get("name") != path.name:
                problems.append(f"{name}: manifest name '{data.get('name')}' != dir '{path.name}'")
        assert not problems, (
            f"Name mismatches:\n" + "\n".join(problems)
        )


class TestIteratePluginLoading:
    """Verify the iterate skill can be loaded as a plugin (issue #201)."""

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


def _vendor_manifest_ok(directory: Path, vendor: str) -> bool:
    """A vendor manifest is a symlink to .plugin/ or a real dir mirror."""
    link = directory / vendor
    if link.is_symlink():
        return link.resolve() == (directory / ".plugin").resolve()
    if link.is_dir():
        src = directory / ".plugin" / "plugin.json"
        dst = link / "plugin.json"
        return src.is_file() and dst.is_file() and src.read_bytes() == dst.read_bytes()
    return False


class TestVendorSymlinksForManifests:
    """Every directory with .plugin/ must have vendor manifests."""

    @pytest.fixture(
        params=list(_all_dirs_with_plugin_manifest()),
        ids=lambda d: f"{d.parent.name}/{d.name}",
    )
    def dir_with_manifest(self, request):
        return request.param

    def test_has_vendor_manifests(self, dir_with_manifest):
        """Directories with .plugin/ must have .claude-plugin and .codex-plugin manifests."""
        for vendor in VENDOR_SYMLINKS:
            assert _vendor_manifest_ok(dir_with_manifest, vendor), (
                f"{dir_with_manifest / vendor} must be a symlink to .plugin "
                "or a real directory mirroring plugin.json"
            )
