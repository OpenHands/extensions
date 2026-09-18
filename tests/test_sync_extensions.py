"""Tests for scripts/sync_extensions.py core functions."""

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from sync_extensions import (
    CMD_MARKER,
    CommandSpec,
    REPO_ROOT,
    _entry_type,
    build_command_content,
    collect_needed_commands,
    generate_catalog,
    load_marketplaces,
    parse_frontmatter,
    slash_triggers,
    sync_commands,
    sync_symlinks,
)


# ── parse_frontmatter ────────────────────────────────────────────────

class TestParseFrontmatter:
    def test_basic(self):
        text = (
            "---\n"
            "name: test-skill\n"
            "description: A test skill\n"
            "triggers:\n"
            "  - /test\n"
            "---\n"
            "Body"
        )
        meta = parse_frontmatter(text)
        assert meta["name"] == "test-skill"
        assert meta["description"] == "A test skill"
        assert meta["triggers"] == ["/test"]

    def test_no_frontmatter(self):
        assert parse_frontmatter("No frontmatter here") == {}

    def test_empty_frontmatter(self):
        meta = parse_frontmatter("---\n---\nBody")
        assert meta.get("triggers", []) == []
        assert "name" not in meta

    def test_multiple_triggers(self):
        text = (
            "---\n"
            "name: multi\n"
            "triggers:\n"
            "  - /foo\n"
            "  - /bar\n"
            "  - baz\n"
            "---\n"
        )
        meta = parse_frontmatter(text)
        assert meta["triggers"] == ["/foo", "/bar", "baz"]

    def test_no_triggers_key(self):
        text = "---\nname: no-triggers\ndescription: desc\n---\n"
        meta = parse_frontmatter(text)
        assert meta["triggers"] == []

    def test_triggers_with_comments(self):
        text = (
            "---\n"
            "triggers:\n"
            "  - /cmd\n"
            "  # this is a comment\n"
            "  - /other\n"
            "---\n"
        )
        meta = parse_frontmatter(text)
        assert "/cmd" in meta["triggers"]
        assert "/other" in meta["triggers"]

    def test_folded_block_scalar_description(self):
        text = (
            "---\n"
            "name: test\n"
            "description: >\n"
            "  This is a long\n"
            "  description text\n"
            "other: value\n"
            "---\n"
        )
        meta = parse_frontmatter(text)
        assert meta["description"] == "This is a long description text"

    def test_unicode(self):
        text = (
            "---\n"
            "name: unic\u00f6de-skill\n"
            "description: \u00dcn\u00efc\u00f6d\u00e9 description \U0001f680\n"
            "---\n"
        )
        meta = parse_frontmatter(text)
        assert meta["name"] == "unic\u00f6de-skill"
        assert "\U0001f680" in meta["description"]


class TestParseFrontmatterEdgeCases:
    """Edge-case tests ensuring graceful degradation."""

    def test_malformed_yaml_missing_close(self):
        assert parse_frontmatter("---\nname: incomplete\n") == {}

    def test_invalid_yaml_returns_empty(self):
        assert parse_frontmatter("---\n: [invalid yaml{{\n---\n") == {}

    def test_colon_in_description(self):
        text = '---\nname: test\ndescription: "key: value pair"\n---\n'
        meta = parse_frontmatter(text)
        assert meta["description"] == "key: value pair"

    def test_quoted_values_stripped(self):
        text = "---\nname: \"quoted-name\"\ndescription: 'single-quoted'\n---\n"
        meta = parse_frontmatter(text)
        assert meta["name"] == "quoted-name"
        assert meta["description"] == "single-quoted"

    def test_triggers_end_at_next_key(self):
        text = (
            "---\n"
            "triggers:\n"
            "  - /a\n"
            "  - /b\n"
            "name: after-triggers\n"
            "---\n"
        )
        meta = parse_frontmatter(text)
        assert meta["triggers"] == ["/a", "/b"]
        assert meta["name"] == "after-triggers"

    def test_null_trigger_skipped(self):
        text = (
            "---\n"
            "triggers:\n"
            "  - /cmd\n"
            "  -\n"
            "  - /other\n"
            "---\n"
        )
        meta = parse_frontmatter(text)
        assert "/cmd" in meta["triggers"]
        assert "/other" in meta["triggers"]

    def test_frontmatter_only_block(self):
        meta = parse_frontmatter("---\nname: only\n---")
        assert meta["name"] == "only"


# ── slash_triggers ────────────────────────────────────────────────────

class TestSlashTriggers:
    def test_filters_slash_only(self):
        meta = {"triggers": ["/init", "keyword", "/build"]}
        assert slash_triggers(meta) == ["/init", "/build"]

    def test_empty(self):
        assert slash_triggers({}) == []
        assert slash_triggers({"triggers": []}) == []


# ── _entry_type ───────────────────────────────────────────────────────

class TestEntryType:
    def test_skills_path(self):
        assert _entry_type("./skills/foo") == "skill"

    def test_plugins_path(self):
        assert _entry_type("./plugins/bar") == "plugin"

    def test_relative_plugins(self):
        assert _entry_type("../plugins/baz") == "plugin"

    def test_relative_skills(self):
        assert _entry_type("../skills/qux") == "skill"

    def test_fallback_is_skill(self):
        assert _entry_type("./nonexistent-xyz") == "skill"


# ── collect_needed_commands ───────────────────────────────────────────

class TestCollectNeededCommands:
    def test_returns_command_specs(self):
        specs = collect_needed_commands()
        assert all(isinstance(s, CommandSpec) for s in specs)
        assert len(specs) > 0

    def test_paths_are_under_commands_dir(self):
        for spec in collect_needed_commands():
            assert spec.path.parent.name == "commands"
            assert spec.path.suffix == ".md"

    def test_colon_triggers_are_normalized_for_filenames(self, tmp_path, monkeypatch):
        skill_dir = tmp_path / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: Test\ntriggers:\n  - /test:command\n---\nBody\n"
        )

        monkeypatch.setattr("sync_extensions.SKILL_DIRS", [tmp_path / "skills"])

        specs = collect_needed_commands()
        assert [spec.path.relative_to(tmp_path).as_posix() for spec in specs] == [
            "skills/test-skill/commands/test-command.md"
        ]


# ── load_marketplaces ────────────────────────────────────────────────

class TestLoadMarketplaces:
    def test_loads_at_least_one(self):
        mps = load_marketplaces()
        assert len(mps) > 0

    def test_marketplaces_have_required_fields(self):
        for mp in load_marketplaces():
            assert "plugins" in mp
            assert "_file" in mp


# ── generate_catalog ─────────────────────────────────────────────────

class TestGenerateCatalog:
    def test_catalog_contains_marketplace_names(self):
        catalog = generate_catalog()
        assert "openhands-extensions" in catalog

    def test_catalog_has_table_header(self):
        catalog = generate_catalog()
        assert "| Name | Type | Description | Commands |" in catalog

    def test_catalog_counts_are_consistent(self):
        catalog = generate_catalog()
        assert "marketplace(s)" in catalog
        assert "extensions" in catalog

    def test_catalog_only_has_skill_or_plugin_types(self):
        """Every table row's Type column must be 'skill' or 'plugin'."""
        catalog = generate_catalog()
        types_found: list[str] = []
        for line in catalog.splitlines():
            # Skip non-table lines, header, and separator
            if not line.startswith("|") or line.startswith("|---") or "Type" in line:
                continue
            cols = [c.strip() for c in line.split("|")]
            # cols[0] is empty (before first |), cols[1]=Name, cols[2]=Type
            if len(cols) >= 3:
                types_found.append(cols[2])
        assert len(types_found) > 0, "Expected at least one table entry"
        invalid = [t for t in types_found if t not in ("skill", "plugin")]
        assert not invalid, f"Found invalid types in catalog: {invalid}"


# ── sync_commands ────────────────────────────────────────────────────

class TestSyncCommands:
    def test_check_mode_reports_no_problems_when_in_sync(self):
        problems = sync_commands(check=True)
        assert problems == [], f"Unexpected problems: {problems}"

    def test_manually_edited_file_detected_in_check_mode(self, tmp_path, monkeypatch):
        """A command file without the header should be flagged in --check mode."""
        # Create a skill with a slash trigger
        skill_dir = tmp_path / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            "---\nname: test-skill\ndescription: Test\ntriggers:\n  - /test-cmd\n---\nBody\n"
        )
        # Create a manually-edited command file (no header)
        cmd_dir = skill_dir / "commands"
        cmd_dir.mkdir()
        (cmd_dir / "test-cmd.md").write_text("Custom content, no header\n")

        monkeypatch.setattr("sync_extensions.REPO_ROOT", tmp_path)
        monkeypatch.setattr("sync_extensions.SKILL_DIRS", [tmp_path / "skills"])
        monkeypatch.setattr("sync_extensions._slash_cmd_cache", {})

        problems = sync_commands(check=True)
        assert any("manually-edited" in p for p in problems)


# ── vendor manifests ─────────────────────────────────────────────────

def _make_plugin_skill(root: Path, name: str = "demo") -> Path:
    """Create a fake skill dir with a canonical .plugin/plugin.json."""
    skill = root / "skills" / name
    (skill / ".plugin").mkdir(parents=True)
    (skill / ".plugin" / "plugin.json").write_text('{"name": "demo"}\n')
    return skill


def _make_real_vendor_mirror(skill: Path, vendor: str = ".codex-plugin") -> Path:
    path = skill / vendor
    path.mkdir(exist_ok=True)
    (path / "plugin.json").write_text('{"name": "demo"}\n')
    return path


def _point_sync_at(tmp_path, monkeypatch):
    monkeypatch.setattr("sync_extensions.SKILL_DIRS", [tmp_path / "skills"])
    monkeypatch.setattr("sync_extensions.REPO_ROOT", tmp_path)


class TestVendorManifests:
    def test_iterate_vendor_dirs_are_real_and_mirror_canonical(self):
        """Codex drops symlinked dirs on install, so iterate ships real ones."""
        iterate = REPO_ROOT / "skills" / "iterate"
        canon = (iterate / ".plugin" / "plugin.json").read_bytes()
        for vendor in (".codex-plugin", ".claude-plugin"):
            path = iterate / vendor
            assert not path.is_symlink(), f"{vendor} must not be a symlink"
            assert path.is_dir(), f"{vendor} must be a real directory"
            assert (path / "plugin.json").read_bytes() == canon

    def test_symlink_to_canonical_passes(self, tmp_path, monkeypatch):
        skill = _make_plugin_skill(tmp_path)
        try:
            for vendor in (".codex-plugin", ".claude-plugin"):
                (skill / vendor).symlink_to(".plugin", target_is_directory=True)
        except OSError:
            pytest.skip("symlinks need privileges on this platform")
        _point_sync_at(tmp_path, monkeypatch)

        assert sync_symlinks(check=True) == []

    def test_real_dir_mirror_passes_and_stale_copy_is_flagged(self, tmp_path, monkeypatch):
        skill = _make_plugin_skill(tmp_path)
        vendor = _make_real_vendor_mirror(skill)
        _make_real_vendor_mirror(skill, ".claude-plugin")
        _point_sync_at(tmp_path, monkeypatch)

        assert sync_symlinks(check=True) == []

        (vendor / "plugin.json").write_text('{"name": "stale"}\n')
        problems = sync_symlinks(check=True)
        assert any("stale manifest copy" in p for p in problems)

    def test_fix_mode_refreshes_stale_copy(self, tmp_path, monkeypatch):
        skill = _make_plugin_skill(tmp_path)
        vendor = _make_real_vendor_mirror(skill)
        _make_real_vendor_mirror(skill, ".claude-plugin")
        (vendor / "plugin.json").write_text('{"name": "stale"}\n')
        _point_sync_at(tmp_path, monkeypatch)

        problems = sync_symlinks(check=False)
        assert any("stale manifest copy" in p for p in problems)
        assert (vendor / "plugin.json").read_text() == '{"name": "demo"}\n'
        assert sync_symlinks(check=True) == []

    def test_lossy_install_copy_keeps_codex_manifest(self, tmp_path):
        """Mimic Codex `plugin add`, which drops symlinked directories.

        The installed cache must still contain
        `.codex-plugin/plugin.json` for the plugin to load.
        """
        src = REPO_ROOT / "skills" / "iterate"
        dst = tmp_path / "iterate"
        shutil.copytree(
            src,
            dst,
            ignore=lambda d, names: [
                n for n in names if (Path(d) / n).is_symlink()
            ],
        )
        manifest = dst / ".codex-plugin" / "plugin.json"
        assert manifest.is_file(), "Codex install lost .codex-plugin/plugin.json"
        assert manifest.read_bytes() == (src / ".plugin" / "plugin.json").read_bytes()

    def test_missing_vendor_still_gets_symlink(self, tmp_path, monkeypatch):
        skill = _make_plugin_skill(tmp_path)
        _point_sync_at(tmp_path, monkeypatch)
        try:
            assert sync_symlinks(check=False) == []
        except OSError:
            pytest.skip("symlinks need privileges on this platform")

        assert (skill / ".codex-plugin").is_symlink()
        assert (skill / ".claude-plugin").is_symlink()


# ── marketplace source paths ─────────────────────────────────────────

class TestMarketplaceSourcePaths:
    def test_all_source_paths_exist(self):
        """Every source path in every marketplace should resolve on disk."""
        import json

        for mp in load_marketplaces():
            mp_file = mp["_file"]
            for plugin in mp["plugins"]:
                src = plugin.get("source", "")
                resolved = REPO_ROOT / src.lstrip("./")
                assert resolved.exists(), (
                    f"{mp_file.name}: {plugin.get('name', '?')} source "
                    f"'{src}' does not exist at {resolved}"
                )
