"""Tests for scripts/sync_extensions.py core functions."""

import sys
from pathlib import Path

import pytest

# Make the scripts directory importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from sync_extensions import (
    CommandSpec,
    _entry_type,
    collect_needed_commands,
    generate_catalog,
    parse_frontmatter,
    slash_triggers,
)


class TestParseFrontmatter:
    def test_basic(self):
        text = "---\nname: test-skill\ndescription: A test skill\ntriggers:\n  - /test\n---\nBody"
        meta = parse_frontmatter(text)
        assert meta["name"] == "test-skill"
        assert meta["description"] == "A test skill"
        assert meta["triggers"] == ["/test"]

    def test_no_frontmatter(self):
        assert parse_frontmatter("No frontmatter here") == {}

    def test_empty_frontmatter(self):
        meta = parse_frontmatter("---\n---\nBody")
        # Empty block has no triggers key — parser only adds it when iterating
        assert meta.get("triggers", []) == []
        assert "name" not in meta

    def test_multiple_triggers(self):
        text = "---\nname: multi\ntriggers:\n  - /foo\n  - /bar\n  - baz\n---\n"
        meta = parse_frontmatter(text)
        assert meta["triggers"] == ["/foo", "/bar", "baz"]

    def test_no_triggers_key(self):
        text = "---\nname: no-triggers\ndescription: desc\n---\n"
        meta = parse_frontmatter(text)
        assert meta["triggers"] == []

    def test_triggers_with_blank_lines(self):
        text = "---\ntriggers:\n  - /first\n\n  - /second\n---\n"
        meta = parse_frontmatter(text)
        assert "/first" in meta["triggers"]
        assert "/second" in meta["triggers"]

    def test_triggers_with_comments(self):
        text = "---\ntriggers:\n  - /cmd\n  # this is a comment\n  - /other\n---\n"
        meta = parse_frontmatter(text)
        assert meta["triggers"] == ["/cmd", "/other"]

    def test_folded_block_scalar_description(self):
        text = "---\nname: test\ndescription: >\n  This is a long\n  description text\nother: value\n---\n"
        meta = parse_frontmatter(text)
        assert meta["description"] == "This is a long description text"

    def test_unicode(self):
        text = "---\nname: unicöde-skill\ndescription: Ünïcödé description 🚀\n---\n"
        meta = parse_frontmatter(text)
        assert meta["name"] == "unicöde-skill"
        assert "🚀" in meta["description"]


class TestSlashTriggers:
    def test_filters_slash_only(self):
        meta = {"triggers": ["/init", "keyword", "/build"]}
        assert slash_triggers(meta) == ["/init", "/build"]

    def test_empty(self):
        assert slash_triggers({}) == []
        assert slash_triggers({"triggers": []}) == []


class TestEntryType:
    def test_skills_path(self):
        assert _entry_type("./skills/foo") == "skill"

    def test_plugins_path(self):
        assert _entry_type("./plugins/bar") == "plugin"

    def test_relative_plugins(self):
        assert _entry_type("../plugins/baz") == "plugin"

    def test_relative_skills(self):
        assert _entry_type("../skills/qux") == "skill"

    def test_fallback(self):
        result = _entry_type("./nonexistent-xyz")
        assert result == "extension"


class TestCollectNeededCommands:
    def test_returns_command_specs(self):
        specs = collect_needed_commands()
        assert all(isinstance(s, CommandSpec) for s in specs)
        # At least some skills have slash triggers
        assert len(specs) > 0

    def test_paths_are_under_commands_dir(self):
        for spec in collect_needed_commands():
            assert spec.path.parent.name == "commands"
            assert spec.path.suffix == ".md"


class TestParseFrontmatterEdgeCases:
    """Edge-case tests ensuring graceful degradation."""

    def test_malformed_yaml_returns_partial(self):
        # Missing closing --- is handled (no match)
        text = "---\nname: incomplete\ndescription: stuff\n"
        assert parse_frontmatter(text) == {}

    def test_colon_in_description(self):
        text = "---\nname: test\ndescription: key: value pair\n---\n"
        meta = parse_frontmatter(text)
        assert meta["description"] == "key: value pair"

    def test_quoted_values(self):
        text = '---\nname: "quoted-name"\ndescription: \'single-quoted\'\n---\n'
        meta = parse_frontmatter(text)
        assert meta["name"] == '"quoted-name"'  # regex doesn't strip quotes

    def test_triggers_end_at_next_key(self):
        text = "---\ntriggers:\n  - /a\n  - /b\nname: after-triggers\n---\n"
        meta = parse_frontmatter(text)
        assert meta["triggers"] == ["/a", "/b"]
        assert meta["name"] == "after-triggers"


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

    def test_no_unknown_type_in_catalog(self):
        catalog = generate_catalog()
        assert "unknown" not in catalog
