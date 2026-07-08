"""Tests for scripts/sync_extensions.py core functions."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from sync_extensions import (
    CMD_MARKER,
    CommandSpec,
    PRIMARY_MARKETPLACE,
    REPO_ROOT,
    ROOT_MARKETPLACE_DIRS,
    _entry_type,
    _normalize_marketplace_bytes,
    build_command_content,
    collect_needed_commands,
    generate_catalog,
    load_marketplaces,
    parse_frontmatter,
    slash_triggers,
    sync_commands,
    sync_root_marketplace,
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


# ── root marketplace copies ──────────────────────────────────────────

class TestRootMarketplace:
    """The root vendor marketplace.json files must be real (non-symlink) copies.

    raw.githubusercontent.com does not dereference git symlinks through
    directory paths, so consumers using the standard
    ``.claude-plugin/marketplace.json`` path (e.g. plugin-directory with
    ``MARKETPLACE_SOURCE=github://openhands/extensions``) need real files.
    """

    def test_vendor_dirs_are_real_directories(self):
        for vendor in ROOT_MARKETPLACE_DIRS:
            vendor_dir = REPO_ROOT / vendor
            assert vendor_dir.is_dir(), f"{vendor}/ is not a directory"
            assert not vendor_dir.is_symlink(), (
                f"{vendor} is a symlink; raw.githubusercontent.com cannot "
                "traverse symlinked directory paths"
            )

    def test_marketplace_json_files_are_real_files(self):
        for vendor in ROOT_MARKETPLACE_DIRS:
            target = REPO_ROOT / vendor / "marketplace.json"
            assert target.is_file(), f"{target} is missing"
            assert not target.is_symlink(), (
                f"{target} is a symlink; raw.githubusercontent.com serves "
                "symlink blobs as their literal target text, not the catalog"
            )

    def test_marketplace_json_matches_canonical(self):
        canonical = _normalize_marketplace_bytes(PRIMARY_MARKETPLACE.read_bytes())
        for vendor in ROOT_MARKETPLACE_DIRS:
            target = REPO_ROOT / vendor / "marketplace.json"
            current = _normalize_marketplace_bytes(target.read_bytes())
            assert current == canonical, (
                f"{target.relative_to(REPO_ROOT)} is out of sync with "
                f"{PRIMARY_MARKETPLACE.relative_to(REPO_ROOT)}"
            )

    def test_marketplace_json_is_valid_catalog(self):
        import json

        canonical = json.loads(PRIMARY_MARKETPLACE.read_bytes())
        for vendor in ROOT_MARKETPLACE_DIRS:
            target = REPO_ROOT / vendor / "marketplace.json"
            data = json.loads(target.read_bytes())
            assert data.get("name") == canonical.get("name")
            assert len(data.get("plugins", [])) == len(canonical.get("plugins", []))

    def test_sync_root_marketplace_detects_and_fixes_symlinks(self, tmp_path, monkeypatch):
        """sync_root_marketplace replaces symlinked dirs/files with real copies."""
        import json

        monkeypatch.setattr("sync_extensions.REPO_ROOT", tmp_path)
        monkeypatch.setattr("sync_extensions.PRIMARY_MARKETPLACE", tmp_path / "marketplaces" / "openhands-extensions.json")

        # Canonical marketplace source.
        mp_dir = tmp_path / "marketplaces"
        mp_dir.mkdir()
        canonical_data = {"name": "openhands-extensions", "plugins": [{"name": "x", "source": "./skills/x"}]}
        canonical_bytes = (json.dumps(canonical_data, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
        (mp_dir / "openhands-extensions.json").write_bytes(canonical_bytes)

        # Recreate the broken double-symlink chain from the issue.
        plugin_dir = tmp_path / ".plugin"
        plugin_dir.mkdir()
        (plugin_dir / "marketplace.json").symlink_to("../marketplaces/openhands-extensions.json")
        (tmp_path / ".claude-plugin").symlink_to(".plugin")
        (tmp_path / ".codex-plugin").symlink_to(".plugin")

        # Check mode must report the symlinks as problems.
        problems = sync_root_marketplace(check=True)
        assert any("symlinked dir" in p for p in problems)
        assert any("symlinked file" in p for p in problems)

        # Write mode fixes them.
        sync_root_marketplace(check=False)
        for vendor in [".claude-plugin", ".codex-plugin", ".plugin"]:
            vendor_dir = tmp_path / vendor
            target = vendor_dir / "marketplace.json"
            assert vendor_dir.is_dir() and not vendor_dir.is_symlink(), f"{vendor} still a symlink dir"
            assert target.is_file() and not target.is_symlink(), f"{target} still a symlink file"
            assert _normalize_marketplace_bytes(target.read_bytes()) == canonical_bytes

        # After fixing, check mode is clean.
        assert sync_root_marketplace(check=True) == []

    def test_sync_root_marketplace_detects_stale_copy(self, tmp_path, monkeypatch):
        """sync_root_marketplace reports (and fixes) an out-of-date real copy."""
        import json

        monkeypatch.setattr("sync_extensions.REPO_ROOT", tmp_path)
        monkeypatch.setattr("sync_extensions.PRIMARY_MARKETPLACE", tmp_path / "marketplaces" / "openhands-extensions.json")

        mp_dir = tmp_path / "marketplaces"
        mp_dir.mkdir()
        canonical = {"name": "openhands-extensions", "plugins": [{"name": "x", "source": "./skills/x"}]}
        canonical_bytes = (json.dumps(canonical, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
        (mp_dir / "openhands-extensions.json").write_bytes(canonical_bytes)

        stale = {"name": "openhands-extensions", "plugins": []}
        for vendor in [".claude-plugin", ".codex-plugin", ".plugin"]:
            (tmp_path / vendor).mkdir()
            (tmp_path / vendor / "marketplace.json").write_text(json.dumps(stale))

        problems = sync_root_marketplace(check=True)
        assert len(problems) == 3
        assert all("out of date" in p for p in problems)

        sync_root_marketplace(check=False)
        for vendor in [".claude-plugin", ".codex-plugin", ".plugin"]:
            assert _normalize_marketplace_bytes((tmp_path / vendor / "marketplace.json").read_bytes()) == canonical_bytes
        assert sync_root_marketplace(check=True) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
