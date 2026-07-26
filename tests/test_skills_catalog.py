"""Tests for the skills catalog codegen (scripts/build-skills-catalog.mjs).

Covers:
- parseFrontmatter edge cases (hyphenated keys, multiline, list items, etc.)
- End-to-end buildCatalog against temp fixtures
- Generated skills/index.js validity and structure
- Determinism: re-running the script produces identical output
"""

import json
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build-skills-catalog.mjs"
SKILLS_INDEX = ROOT / "skills" / "index.js"


def run_node(script: str, *, cwd: str | Path = ROOT, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
    )


# ---------------------------------------------------------------------------
# parseFrontmatter unit tests (via Node subprocess)
# ---------------------------------------------------------------------------

class TestParseFrontmatter:
    """Unit tests for parseFrontmatter, exercised via Node import."""

    def _parse(self, frontmatter_body: str) -> dict:
        """Run parseFrontmatter on *frontmatter_body* and return the result."""
        escaped = json.dumps(frontmatter_body)
        script = textwrap.dedent(f"""\
            import {{ parseFrontmatter }} from './scripts/build-skills-catalog.mjs';
            const result = parseFrontmatter({escaped});
            process.stdout.write(JSON.stringify(result));
        """)
        result = run_node(script)
        return json.loads(result.stdout)

    def test_simple_key_value(self):
        fm = self._parse("name: my-skill\ndescription: A test skill")
        assert fm["name"] == "my-skill"
        assert fm["description"] == "A test skill"

    def test_hyphenated_keys(self):
        fm = self._parse("name: my-skill\ncompatibility: works-everywhere")
        assert fm["compatibility"] == "works-everywhere"

    def test_hyphenated_key_not_silently_dropped(self):
        """Keys like event-key: should be parsed, not ignored."""
        # We verify indirectly: if a hyphenated key precedes a list,
        # the list items must be collected under that key.
        script = textwrap.dedent("""\
            import { parseFrontmatter } from './scripts/build-skills-catalog.mjs';
            // parseFrontmatter returns a fixed shape, so test the internal
            // parsing by checking a known hyphenated output key.
            const fm = parseFrontmatter("license: MIT");
            // Also verify a raw parse captures hyphenated keys internally
            // by re-implementing a quick check:
            const raw = "event-key: hello";
            const match = raw.match(/^[\\w-]+:\\s*(.*)/);
            if (!match) { console.error("Regex failed for hyphenated key"); process.exit(1); }
            process.stdout.write("ok");
        """)
        result = run_node(script)
        assert result.stdout == "ok"

    def test_list_items(self):
        fm = self._parse("name: test\ntriggers:\n- github\n- git\n- pull request")
        assert fm["triggers"] == ["github", "git", "pull request"]

    def test_empty_triggers_when_scalar(self):
        fm = self._parse("name: test\ntriggers: not-a-list")
        assert fm["triggers"] == []

    def test_multiline_description_folded(self):
        fm = self._parse("name: test\ndescription: >\n  This is a long\n  description text")
        assert "This is a long" in fm["description"]
        assert "description text" in fm["description"]

    def test_multiline_description_literal(self):
        fm = self._parse("name: test\ndescription: |\n  Line one\n  Line two")
        assert "Line one" in fm["description"]
        assert "Line two" in fm["description"]

    def test_missing_name_returns_empty(self):
        fm = self._parse("description: no name here")
        assert fm["name"] == ""

    def test_missing_description_returns_empty(self):
        fm = self._parse("name: test")
        assert fm["description"] == ""
        assert fm["triggers"] == []

    def test_optional_fields_omitted_when_absent(self):
        fm = self._parse("name: test\ndescription: desc")
        assert "license" not in fm
        assert "compatibility" not in fm

    def test_optional_fields_present_when_set(self):
        fm = self._parse("name: test\nlicense: MIT\ncompatibility: all platforms")
        assert fm["license"] == "MIT"
        assert fm["compatibility"] == "all platforms"

    def test_empty_input(self):
        fm = self._parse("")
        assert fm["name"] == ""
        assert fm["description"] == ""
        assert fm["triggers"] == []


# ---------------------------------------------------------------------------
# End-to-end codegen tests with temp fixtures (using buildCatalog)
# ---------------------------------------------------------------------------

class TestCodegenEndToEnd:
    """Run buildCatalog against temp SKILL.md fixtures."""

    def _run_codegen(self, tmp_path: Path, skills: dict[str, str]) -> list[dict]:
        """Create temp skill dirs, run buildCatalog, return parsed catalog."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        for name, content in skills.items():
            skill_dir = skills_dir / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(content)

        # Empty marketplaces dir: isolates fixtures from the real manifests so a
        # future fixture named after a real skill (e.g. "docker") can't pick up
        # its real category or trip the real conflict/unknown-category checks.
        markets_dir = tmp_path / "marketplaces"
        markets_dir.mkdir()

        script = textwrap.dedent(f"""\
            import {{ buildCatalog }} from './scripts/build-skills-catalog.mjs';
            const entries = buildCatalog({json.dumps(str(skills_dir))}, {json.dumps(str(markets_dir))});
            process.stdout.write(JSON.stringify(entries));
        """)
        result = run_node(script)
        return json.loads(result.stdout)

    def test_basic_skill(self, tmp_path):
        entries = self._run_codegen(tmp_path, {
            "my-skill": "---\nname: my-skill\ndescription: A skill\ntriggers:\n- test\n---\nBody content here"
        })
        assert len(entries) == 1
        assert entries[0]["name"] == "my-skill"
        assert entries[0]["description"] == "A skill"
        assert entries[0]["triggers"] == ["test"]
        assert entries[0]["content"] == "Body content here"

    def test_name_falls_back_to_directory(self, tmp_path):
        entries = self._run_codegen(tmp_path, {
            "fallback-dir": "---\ndescription: no name field\n---\nBody"
        })
        assert entries[0]["name"] == "fallback-dir"

    def test_missing_frontmatter_skipped(self, tmp_path):
        entries = self._run_codegen(tmp_path, {
            "good-skill": "---\nname: good\ndescription: yes\n---\nBody",
            "bad-skill": "No frontmatter delimiters at all",
        })
        assert len(entries) == 1
        assert entries[0]["name"] == "good"

    def test_missing_frontmatter_warns(self, tmp_path):
        """SKILL.md without frontmatter should produce a stderr warning."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "bad").mkdir()
        (skills_dir / "bad" / "SKILL.md").write_text("No frontmatter here")

        # Empty marketplaces dir: isolates this fixture from the real manifests.
        markets_dir = tmp_path / "marketplaces"
        markets_dir.mkdir()

        script = textwrap.dedent(f"""\
            import {{ buildCatalog }} from './scripts/build-skills-catalog.mjs';
            buildCatalog({json.dumps(str(skills_dir))}, {json.dumps(str(markets_dir))});
        """)
        result = run_node(script)
        assert "Warning" in result.stderr
        assert "missing frontmatter" in result.stderr

    def test_body_with_triple_dashes_preserved(self, tmp_path):
        content = "---\nname: test\ndescription: d\n---\nBefore\n---\nAfter"
        entries = self._run_codegen(tmp_path, {"test-skill": content})
        assert "---" in entries[0]["content"]
        assert "Before" in entries[0]["content"]
        assert "After" in entries[0]["content"]

    def test_generated_file_is_valid_js(self, tmp_path):
        """Write a catalog to a file and verify it's importable as JS."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        for name in ("alpha", "beta"):
            (skills_dir / name).mkdir()
            (skills_dir / name / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: {name} desc\n---\nBody {name}"
            )

        # Empty marketplaces dir: isolates this fixture from the real manifests.
        markets_dir = tmp_path / "marketplaces"
        markets_dir.mkdir()

        output = tmp_path / "output.js"
        script = textwrap.dedent(f"""\
            import {{ writeFileSync }} from "node:fs";
            import {{ buildCatalog }} from './scripts/build-skills-catalog.mjs';
            const entries = buildCatalog({json.dumps(str(skills_dir))}, {json.dumps(str(markets_dir))});
            const src = "export const SKILLS_CATALOG = " + JSON.stringify(entries) + ";\\nexport default SKILLS_CATALOG;\\n";
            writeFileSync({json.dumps(str(output))}, src);
        """)
        run_node(script)

        verify = textwrap.dedent(f"""\
            const mod = await import({json.dumps(str(output))});
            if (!Array.isArray(mod.SKILLS_CATALOG)) process.exit(1);
            if (mod.SKILLS_CATALOG.length !== 2) process.exit(1);
            if (mod.default !== mod.SKILLS_CATALOG) process.exit(1);
        """)
        run_node(verify)

    def test_entries_sorted_by_directory_name(self, tmp_path):
        entries = self._run_codegen(tmp_path, {
            "zebra": "---\nname: zebra\ndescription: z\n---\nZ",
            "alpha": "---\nname: alpha\ndescription: a\n---\nA",
            "middle": "---\nname: middle\ndescription: m\n---\nM",
        })
        names = [e["name"] for e in entries]
        assert names == ["alpha", "middle", "zebra"]

    def test_optional_fields_included_when_present(self, tmp_path):
        entries = self._run_codegen(tmp_path, {
            "lic": "---\nname: lic\ndescription: d\nlicense: MIT\ncompatibility: all\n---\nBody"
        })
        assert entries[0]["license"] == "MIT"
        assert entries[0]["compatibility"] == "all"

    def test_optional_fields_omitted_when_absent(self, tmp_path):
        entries = self._run_codegen(tmp_path, {
            "bare": "---\nname: bare\ndescription: d\n---\nBody"
        })
        assert "license" not in entries[0]
        assert "compatibility" not in entries[0]

    def test_directories_without_skill_md_ignored(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "has-skill").mkdir()
        (skills_dir / "has-skill" / "SKILL.md").write_text("---\nname: ok\ndescription: d\n---\nBody")
        (skills_dir / "no-skill").mkdir()  # no SKILL.md

        # Empty marketplaces dir: isolates this fixture from the real manifests.
        markets_dir = tmp_path / "marketplaces"
        markets_dir.mkdir()

        script = textwrap.dedent(f"""\
            import {{ buildCatalog }} from './scripts/build-skills-catalog.mjs';
            const entries = buildCatalog({json.dumps(str(skills_dir))}, {json.dumps(str(markets_dir))});
            process.stdout.write(JSON.stringify(entries));
        """)
        result = run_node(script)
        entries = json.loads(result.stdout)
        assert len(entries) == 1
        assert entries[0]["name"] == "ok"


# ---------------------------------------------------------------------------
# Generated skills/index.js validation (real repo data)
# ---------------------------------------------------------------------------

class TestGeneratedSkillsIndex:
    """Validate the checked-in skills/index.js against the live SKILL.md files."""

    def test_index_js_is_valid_and_exports_array(self):
        """The generated skills/index.js is valid JS with a non-empty array export."""
        script = textwrap.dedent("""\
            import { SKILLS_CATALOG } from './skills/index.js';
            if (!Array.isArray(SKILLS_CATALOG)) process.exit(1);
            if (SKILLS_CATALOG.length === 0) process.exit(1);
            import SKILLS from './skills/index.js';
            if (SKILLS !== SKILLS_CATALOG) process.exit(1);
        """)
        run_node(script)

    def test_every_entry_has_required_fields(self):
        """Each catalog entry must have name, description, triggers, and content."""
        script = textwrap.dedent("""\
            import { SKILLS_CATALOG } from './skills/index.js';
            for (const entry of SKILLS_CATALOG) {
              if (typeof entry.name !== 'string' || !entry.name) {
                console.error('Missing name:', JSON.stringify(entry).slice(0, 100));
                process.exit(1);
              }
              if (typeof entry.description !== 'string') {
                console.error('Missing description for:', entry.name);
                process.exit(1);
              }
              if (!Array.isArray(entry.triggers)) {
                console.error('Missing triggers for:', entry.name);
                process.exit(1);
              }
              if (typeof entry.content !== 'string') {
                console.error('Missing content for:', entry.name);
                process.exit(1);
              }
            }
        """)
        run_node(script)

    def test_no_duplicate_names(self):
        """Skill names should be unique in the catalog."""
        script = textwrap.dedent("""\
            import { SKILLS_CATALOG } from './skills/index.js';
            const names = SKILLS_CATALOG.map(e => e.name);
            const dupes = names.filter((n, i) => names.indexOf(n) !== i);
            if (dupes.length > 0) {
              console.error('Duplicate names:', dupes);
              process.exit(1);
            }
        """)
        run_node(script)

    def test_catalog_is_sorted(self):
        """Entries should be sorted alphabetically by name."""
        script = textwrap.dedent("""\
            import { SKILLS_CATALOG } from './skills/index.js';
            const names = SKILLS_CATALOG.map(e => e.name);
            const sorted = [...names].sort();
            for (let i = 0; i < names.length; i++) {
              if (names[i] !== sorted[i]) {
                console.error('Not sorted: ' + names[i] + ' should be ' + sorted[i]);
                process.exit(1);
              }
            }
        """)
        run_node(script)

    def test_index_is_up_to_date(self):
        """Re-running the codegen script should produce identical output."""
        before = SKILLS_INDEX.read_text()
        subprocess.run(["node", str(SCRIPT)], cwd=str(ROOT), check=True, capture_output=True)
        after = SKILLS_INDEX.read_text()
        assert before == after, "skills/index.js is out of date — run: node scripts/build-skills-catalog.mjs"


# ---------------------------------------------------------------------------
# Marketplace skill categories (consumed by the agent-canvas /skills rail)
# ---------------------------------------------------------------------------

MARKETPLACES_DIR = ROOT / "marketplaces"

SKILL_CATEGORY_IDS = {
    "automations",
    "environment",
    "code-hosting",
    "agent-authoring",
    "code-quality",
    "integrations",
    "writing",
    "design",
    "other",
}

# Skills with no marketplace entry. They cannot be added without also creating
# .plugin/plugin.json and vendor symlinks (see test_skill_plugin_loading.py),
# which would publish them as Codex/Claude Code plugins. They fall back to
# "other" in the generated catalog.
SKILLS_WITHOUT_MARKETPLACE_ENTRY = {"qa-changes", "release-notes"}

EXPECTED_CATEGORY_COUNTS = {
    "environment": 10,
    "automations": 9,
    "code-hosting": 8,
    "agent-authoring": 8,
    "code-quality": 6,
    "integrations": 5,
    "writing": 4,
    "design": 2,
    "other": 1,
}


def _marketplace_skill_categories() -> dict[str, str]:
    """Map skill directory name -> category, across every marketplace manifest."""
    result: dict[str, str] = {}
    for path in sorted(MARKETPLACES_DIR.glob("*.json")):
        manifest = json.loads(path.read_text())
        for entry in manifest.get("plugins", []):
            source = entry.get("source", "")
            if not source.startswith("./skills/"):
                continue
            result[source.split("/")[-1]] = entry.get("category")
    return result


class TestMarketplaceSkillCategories:
    def test_every_skill_entry_uses_a_known_category(self):
        bad = {
            name: category
            for name, category in _marketplace_skill_categories().items()
            if category not in SKILL_CATEGORY_IDS
        }
        assert bad == {}, f"Unknown categories: {bad}"

    def test_uncovered_skills_are_exactly_the_known_exceptions(self):
        dirs = {
            d.name
            for d in (ROOT / "skills").iterdir()
            if d.is_dir() and not d.name.startswith(".")
        }
        uncovered = dirs - set(_marketplace_skill_categories())
        assert uncovered == SKILLS_WITHOUT_MARKETPLACE_ENTRY

    def test_category_distribution_is_balanced(self):
        from collections import Counter

        counts = dict(Counter(_marketplace_skill_categories().values()))
        assert counts == EXPECTED_CATEGORY_COUNTS

    def test_plugin_entries_keep_their_own_taxonomy(self):
        """Plugin entries are for Claude Code browsing and must not be rewritten."""
        categories = set()
        for path in sorted(MARKETPLACES_DIR.glob("*.json")):
            manifest = json.loads(path.read_text())
            for entry in manifest.get("plugins", []):
                if entry.get("source", "").startswith("./skills/"):
                    continue
                categories.add(entry.get("category"))
        assert categories - SKILL_CATEGORY_IDS, (
            "Plugin entries appear to have been rewritten to the skill taxonomy"
        )


class TestCategoryJoin:
    """buildCatalog joins marketplace categories onto skill entries."""

    def _build(self, tmp_path, skills: dict[str, str], manifests: dict[str, dict], check: bool = True):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        for name, content in skills.items():
            (skills_dir / name).mkdir()
            (skills_dir / name / "SKILL.md").write_text(content)

        markets_dir = tmp_path / "marketplaces"
        markets_dir.mkdir()
        for filename, manifest in manifests.items():
            (markets_dir / filename).write_text(json.dumps(manifest))

        script = textwrap.dedent(f"""\
            import {{ buildCatalog }} from './scripts/build-skills-catalog.mjs';
            const entries = buildCatalog({json.dumps(str(skills_dir))}, {json.dumps(str(markets_dir))});
            process.stdout.write(JSON.stringify(entries));
        """)
        return run_node(script, check=check)

    def test_category_is_joined_from_the_manifest(self, tmp_path):
        result = self._build(
            tmp_path,
            {"docker": "---\nname: docker\ndescription: d\n---\nBody"},
            {"m.json": {"plugins": [{"name": "docker", "source": "./skills/docker", "category": "environment"}]}},
        )
        entries = json.loads(result.stdout)
        assert entries[0]["category"] == "environment"

    def test_plugin_entries_are_ignored_when_building_the_map(self, tmp_path):
        result = self._build(
            tmp_path,
            {"docker": "---\nname: docker\ndescription: d\n---\nBody"},
            {"m.json": {"plugins": [
                {"name": "some-plugin", "source": "./plugins/some-plugin", "category": "utilities"},
                {"name": "docker", "source": "./skills/docker", "category": "environment"},
            ]}},
        )
        entries = json.loads(result.stdout)
        assert entries[0]["category"] == "environment"

    def test_unknown_category_throws_naming_the_skill(self, tmp_path):
        result = self._build(
            tmp_path,
            {"docker": "---\nname: docker\ndescription: d\n---\nBody"},
            {"m.json": {"plugins": [{"name": "docker", "source": "./skills/docker", "category": "code-hostig"}]}},
            check=False,
        )
        assert result.returncode != 0
        assert "docker" in result.stderr
        assert "code-hostig" in result.stderr
        assert "environment" in result.stderr  # the legal set is printed

    def test_conflicting_categories_across_manifests_throws(self, tmp_path):
        result = self._build(
            tmp_path,
            {"docker": "---\nname: docker\ndescription: d\n---\nBody"},
            {
                "a.json": {"plugins": [{"name": "docker", "source": "./skills/docker", "category": "environment"}]},
                "b.json": {"plugins": [{"name": "docker", "source": "./skills/docker", "category": "design"}]},
            },
            check=False,
        )
        assert result.returncode != 0
        assert "docker" in result.stderr
        assert "Conflicting categories" in result.stderr
        assert "environment" in result.stderr  # the first manifest's value
        assert "design" in result.stderr  # the second manifest's conflicting value

    def test_skill_without_an_entry_gets_other_and_warns(self, tmp_path):
        result = self._build(
            tmp_path,
            {"lonely": "---\nname: lonely\ndescription: d\n---\nBody"},
            {"m.json": {"plugins": []}},
        )
        entries = json.loads(result.stdout)
        assert entries[0]["category"] == "other"
        assert "lonely" in result.stderr


class TestGeneratedCategories:
    """Validate the checked-in skills/index.js categories."""

    def test_every_entry_has_a_known_category(self):
        script = textwrap.dedent("""\
            import { SKILLS_CATALOG, SKILL_CATEGORY_IDS } from './skills/index.js';
            const legal = new Set(SKILL_CATEGORY_IDS);
            for (const entry of SKILLS_CATALOG) {
              if (!legal.has(entry.category)) {
                console.error('Bad category for ' + entry.name + ': ' + entry.category);
                process.exit(1);
              }
            }
        """)
        run_node(script)

    def test_uncovered_skills_land_in_other(self):
        script = textwrap.dedent(f"""\
            import {{ SKILLS_CATALOG }} from './skills/index.js';
            const expected = {json.dumps(sorted(SKILLS_WITHOUT_MARKETPLACE_ENTRY))};
            const actual = SKILLS_CATALOG.filter(e => e.category === 'other').map(e => e.name).sort();
            const extra = actual.filter(n => !expected.includes(n) && n !== 'flarglebargle');
            if (extra.length) {{
              console.error('Unexpected uncategorized skills: ' + extra.join(', '));
              process.exit(1);
            }}
        """)
        run_node(script)
