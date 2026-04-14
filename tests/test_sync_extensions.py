"""Tests for scripts/sync_extensions.py core functions."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from sync_extensions import (
    CommandSpec,
    _entry_type,
    collect_needed_commands,
    generate_catalog,
    load_marketplaces,
    parse_frontmatter,
    slash_triggers,
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
        """Every entry type in the catalog should be skill or plugin."""
        catalog = generate_catalog()
        assert "| extension |" not in catalog
        assert "| unknown |" not in catalog
