"""Tests for the release notes generator plugin."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add the plugin scripts directory to the path
plugin_dir = Path(__file__).parent.parent / "plugins" / "release-notes" / "scripts"
sys.path.insert(0, str(plugin_dir))

from generate_release_notes import (
    CATEGORIES,
    Change,
    Contributor,
    ReleaseNotes,
    _dedupe_changes,
    _process_commit,
    categorize_change,
    get_commits_between_tags,
)
from prompt import format_prompt


class TestChange:
    """Tests for the Change dataclass."""

    def test_to_markdown_basic(self):
        """Test basic markdown formatting."""
        change = Change(
            message="Add new feature",
            sha="abc123",
            author="testuser",
        )
        result = change.to_markdown("owner/repo")
        assert result == "- Add new feature @testuser"

    def test_to_markdown_with_pr(self):
        """Test markdown formatting with PR number."""
        change = Change(
            message="Resolve memory leak",
            sha="abc123",
            author="testuser",
            pr_number=42,
        )
        result = change.to_markdown("owner/repo")
        assert result == "- Resolve memory leak (#42) @testuser"

    def test_to_markdown_strips_conventional_commit_prefix(self):
        """Test that conventional commit prefixes are stripped."""
        change = Change(
            message="feat: Add new feature",
            sha="abc123",
            author="testuser",
            pr_number=42,
        )
        result = change.to_markdown("owner/repo")
        assert "feat:" not in result
        assert "Add new feature" in result

    def test_to_markdown_strips_scoped_prefix(self):
        """Test that scoped conventional commit prefixes are stripped."""
        change = Change(
            message="fix(api): Resolve timeout issue",
            sha="abc123",
            author="testuser",
        )
        result = change.to_markdown("owner/repo")
        assert "fix(api):" not in result
        assert "Resolve timeout issue" in result

    def test_to_markdown_capitalizes_first_letter(self):
        """Test that the first letter is capitalized."""
        change = Change(
            message="fix: lower case message",
            sha="abc123",
            author="testuser",
        )
        result = change.to_markdown("owner/repo")
        assert "Lower case message" in result


class TestCategorizeChange:
    """Tests for the categorize_change function."""

    def test_categorize_feat_prefix(self):
        """Test categorization of feat: prefix."""
        change = Change(message="feat: Add new API", sha="abc", author="user")
        assert categorize_change(change) == "features"

    def test_categorize_feature_prefix(self):
        """Test categorization of feature: prefix."""
        change = Change(message="feature: Add new API", sha="abc", author="user")
        assert categorize_change(change) == "features"

    def test_categorize_fix_prefix(self):
        """Test categorization of fix: prefix."""
        change = Change(message="fix: Resolve crash", sha="abc", author="user")
        assert categorize_change(change) == "fixes"

    def test_categorize_docs_prefix(self):
        """Test categorization of docs: prefix."""
        change = Change(message="docs: Update README", sha="abc", author="user")
        assert categorize_change(change) == "docs"

    def test_categorize_chore_prefix(self):
        """Test categorization of chore: prefix."""
        change = Change(message="chore: Update dependencies", sha="abc", author="user")
        assert categorize_change(change) == "internal"

    def test_categorize_ci_prefix(self):
        """Test categorization of ci: prefix."""
        change = Change(message="ci: Add GitHub Actions", sha="abc", author="user")
        assert categorize_change(change) == "internal"

    def test_categorize_breaking_prefix(self):
        """Test categorization of BREAKING: prefix."""
        change = Change(message="BREAKING: Remove deprecated API", sha="abc", author="user")
        assert categorize_change(change) == "breaking"

    def test_categorize_by_label_enhancement(self):
        """Test categorization by enhancement label."""
        change = Change(
            message="Add feature",
            sha="abc",
            author="user",
            pr_labels=["enhancement"],
        )
        assert categorize_change(change) == "features"

    def test_categorize_by_label_bug(self):
        """Test categorization by bug label."""
        change = Change(
            message="Fix something",
            sha="abc",
            author="user",
            pr_labels=["bug"],
        )
        assert categorize_change(change) == "fixes"

    def test_categorize_by_label_breaking_change(self):
        """Test categorization by breaking-change label."""
        change = Change(
            message="Change API",
            sha="abc",
            author="user",
            pr_labels=["breaking-change"],
        )
        assert categorize_change(change) == "breaking"

    def test_categorize_uncategorized(self):
        """Test uncategorized changes fall to other."""
        change = Change(message="Random change", sha="abc", author="user")
        assert categorize_change(change) == "other"

    def test_commit_prefix_takes_precedence_over_label(self):
        """Test that commit prefix categorization takes precedence."""
        change = Change(
            message="feat: Add feature",
            sha="abc",
            author="user",
            pr_labels=["bug"],  # Conflicting label
        )
        # Should be categorized as feature based on prefix
        assert categorize_change(change) == "features"

    def test_keyword_categorizes_docs(self):
        """Test docs keyword fallback categorization."""
        change = Change(
            message="Update documentation with new examples",
            sha="abc",
            author="user",
        )
        assert categorize_change(change) == "docs"

    def test_keyword_categorizes_internal_before_feature(self):
        """Test internal keyword fallback takes precedence over generic feature verbs."""
        change = Change(
            message="Add extensive typing to controller directory",
            sha="abc",
            author="user",
        )
        assert categorize_change(change) == "internal"

    def test_keyword_categorizes_fixes(self):
        """Test fix keyword fallback categorization."""
        change = Change(
            message="Resolve timeout error in session reconnect",
            sha="abc",
            author="user",
        )
        assert categorize_change(change) == "fixes"

    def test_keyword_categorizes_features(self):
        """Test feature keyword fallback categorization."""
        change = Change(
            message="Add VS Code tab alongside the terminal",
            sha="abc",
            author="user",
        )
        assert categorize_change(change) == "features"


class TestReleaseNotes:
    """Tests for the ReleaseNotes dataclass."""

    def test_to_markdown_basic(self):
        """Test basic release notes generation."""
        notes = ReleaseNotes(
            tag="v1.0.0",
            previous_tag="v0.9.0",
            date="2026-03-06",
            repo_name="owner/repo",
            changes={
                "features": [
                    Change(message="Add feature", sha="abc", author="user1", pr_number=1)
                ],
                "fixes": [
                    Change(message="Fix bug", sha="def", author="user2", pr_number=2)
                ],
            },
        )
        markdown = notes.to_markdown()

        assert "## [v1.0.0] - 2026-03-06" in markdown
        assert "### ✨ New Features" in markdown
        assert "### 🐛 Bug Fixes" in markdown
        assert "Add feature (#1) @user1" in markdown
        assert "(#2) @user2" in markdown  # Fix bug becomes Bug due to prefix stripping
        assert "compare/v0.9.0...v1.0.0" in markdown

    def test_to_markdown_with_breaking_changes(self):
        """Test release notes with breaking changes."""
        notes = ReleaseNotes(
            tag="v2.0.0",
            previous_tag="v1.0.0",
            date="2026-03-06",
            repo_name="owner/repo",
            changes={
                "breaking": [
                    Change(message="Remove API", sha="abc", author="user", pr_number=1)
                ],
            },
        )
        markdown = notes.to_markdown()

        assert "### ⚠️ Breaking Changes" in markdown
        assert "Remove API" in markdown

    def test_to_markdown_with_new_contributors(self):
        """Test release notes with new contributors."""
        notes = ReleaseNotes(
            tag="v1.0.0",
            previous_tag="v0.9.0",
            date="2026-03-06",
            repo_name="owner/repo",
            changes={},
            new_contributors=[
                Contributor(username="newuser", first_pr=42, is_new=True),
            ],
        )
        markdown = notes.to_markdown()

        assert "### 👥 New Contributors" in markdown
        assert "@newuser made their first contribution in #42" in markdown

    def test_to_markdown_internal_excluded_by_default(self):
        """Test that internal changes are excluded by default."""
        notes = ReleaseNotes(
            tag="v1.0.0",
            previous_tag="v0.9.0",
            date="2026-03-06",
            repo_name="owner/repo",
            changes={
                "internal": [
                    Change(message="Update CI", sha="abc", author="user", pr_number=1)
                ],
            },
        )
        markdown = notes.to_markdown(include_internal=False)

        assert "Internal" not in markdown

    def test_to_markdown_internal_included_when_requested(self):
        """Test that internal changes are included when requested."""
        notes = ReleaseNotes(
            tag="v1.0.0",
            previous_tag="v0.9.0",
            date="2026-03-06",
            repo_name="owner/repo",
            changes={
                "internal": [
                    Change(message="Update CI", sha="abc", author="user", pr_number=1)
                ],
            },
        )
        markdown = notes.to_markdown(include_internal=True)

        assert "### 🏗️ Internal/Infrastructure" in markdown
        assert "Update CI" in markdown

    def test_to_markdown_omits_other_changes(self):
        """Test that uncategorized changes are omitted for a more concise summary."""
        notes = ReleaseNotes(
            tag="v1.0.0",
            previous_tag="v0.9.0",
            date="2026-03-06",
            repo_name="owner/repo",
            changes={
                "other": [
                    Change(message="Random internal cleanup", sha="abc", author="user")
                ],
            },
        )
        markdown = notes.to_markdown()

        assert "Other Changes" not in markdown
        assert "Random internal cleanup" not in markdown


class TestProcessingHelpers:
    """Tests for processing helpers."""

    def test_dedupe_changes_collapses_multiple_commits_from_same_pr(self):
        """Test that only one entry is kept per PR."""
        changes = [
            Change(message="First commit", sha="abc", author="user", pr_number=10),
            Change(message="Second commit", sha="def", author="user", pr_number=10),
            Change(message="Standalone commit", sha="ghi", author="user"),
        ]

        deduped = _dedupe_changes(changes)

        assert [change.pr_number for change in deduped] == [10, None]
        assert [change.sha for change in deduped] == ["abc", "ghi"]

    @patch("generate_release_notes.get_pr_for_commit")
    def test_process_commit_prefers_pr_title_and_author(self, mock_get_pr_for_commit):
        """Test that PR metadata is preferred for user-facing release note entries."""
        mock_get_pr_for_commit.return_value = {
            "number": 42,
            "title": "Add settings page",
            "body": "Adds a new settings page for managing preferences.",
            "html_url": "https://github.com/owner/repo/pull/42",
            "labels": [{"name": "enhancement"}],
            "user": {"login": "pr-author"},
        }
        commit = {
            "sha": "abc123",
            "commit": {"message": "feat: Low-level implementation detail\n\nMore text"},
            "author": {"login": "commit-author"},
        }

        change = _process_commit(commit, "owner/repo", "token")

        assert change is not None
        assert change.message == "Add settings page"
        assert change.author == "pr-author"
        assert change.pr_number == 42
        assert change.pr_labels == ["enhancement"]
        assert change.body == "Adds a new settings page for managing preferences."
        assert change.url == "https://github.com/owner/repo/pull/42"

    @patch("generate_release_notes.github_api_request")
    def test_get_commits_between_tags_warns_on_truncation(self, mock_github_api_request, capsys):
        """Test that compare API truncation is surfaced to users."""
        mock_github_api_request.return_value = {
            "total_commits": 300,
            "commits": [{"sha": "abc"}],
        }

        commits = get_commits_between_tags("owner/repo", "v1.0.0", "v1.1.0", "token")

        assert commits == [{"sha": "abc"}]
        assert "truncated the commit list" in capsys.readouterr().err


class TestPrompt:
    """Tests for the release-notes agent prompt."""

    def test_format_prompt_includes_editorial_instructions(self):
        """Test that the prompt tells the agent to make editorial judgments."""
        prompt = format_prompt(
            repo_name="owner/repo",
            tag="v1.2.0",
            previous_tag="v1.1.0",
            date="2026-03-07",
            commit_count=12,
            include_internal=False,
            output_format="release",
            full_changelog_url="https://github.com/owner/repo/compare/v1.1.0...v1.2.0",
            change_candidates="- Ref: #42\n  Title: Add dark mode",
            new_contributors="- @new-user made their first contribution in #42",
        )

        assert "Write official release notes for `owner/repo` tag `v1.2.0`." in prompt
        assert "decide which PRs are important enough to mention" in prompt
        assert "group related PRs into a single bullet" in prompt
        assert "omit trivial, repetitive, or low-signal changes" in prompt
        assert "include every new contributor listed below" in prompt
        assert "Current tag: v1.2.0" in prompt
        assert "Full changelog URL:" in prompt



class TestCategories:
    """Tests for the CATEGORIES constant."""

    def test_all_categories_have_required_fields(self):
        """Test that all categories have the required fields."""
        required_fields = ["emoji", "title", "commit_patterns", "labels"]
        for category, info in CATEGORIES.items():
            for field in required_fields:
                assert field in info, f"Category {category} missing {field}"

    def test_breaking_category_exists(self):
        """Test that the breaking category exists."""
        assert "breaking" in CATEGORIES
        assert CATEGORIES["breaking"]["emoji"] == "⚠️"

    def test_features_category_exists(self):
        """Test that the features category exists."""
        assert "features" in CATEGORIES
        assert CATEGORIES["features"]["emoji"] == "✨"

    def test_fixes_category_exists(self):
        """Test that the fixes category exists."""
        assert "fixes" in CATEGORIES
        assert CATEGORIES["fixes"]["emoji"] == "🐛"

    def test_docs_category_exists(self):
        """Test that the docs category exists."""
        assert "docs" in CATEGORIES
        assert CATEGORIES["docs"]["emoji"] == "📚"

    def test_internal_category_exists(self):
        """Test that the internal category exists."""
        assert "internal" in CATEGORIES
        assert CATEGORIES["internal"]["emoji"] == "🏗️"


class TestPluginStructure:
    """Tests for the plugin directory structure."""

    def test_plugin_directory_exists(self):
        """Test that the plugin directory exists."""
        plugin_dir = Path(__file__).parent.parent / "plugins" / "release-notes"
        assert plugin_dir.is_dir()

    def test_skill_md_exists(self):
        """Test that SKILL.md exists."""
        skill_md = Path(__file__).parent.parent / "plugins" / "release-notes" / "SKILL.md"
        assert skill_md.is_file()

    def test_readme_exists(self):
        """Test that README.md exists."""
        readme = Path(__file__).parent.parent / "plugins" / "release-notes" / "README.md"
        assert readme.is_file()

    def test_action_yml_exists(self):
        """Test that action.yml exists."""
        action = Path(__file__).parent.parent / "plugins" / "release-notes" / "action.yml"
        assert action.is_file()

    def test_script_exists(self):
        """Test that the generator script exists."""
        script = (
            Path(__file__).parent.parent
            / "plugins"
            / "release-notes"
            / "scripts"
            / "generate_release_notes.py"
        )
        assert script.is_file()

    def test_workflow_exists(self):
        """Test that the workflow file exists."""
        workflow = (
            Path(__file__).parent.parent
            / "plugins"
            / "release-notes"
            / "workflows"
            / "release-notes.yml"
        )
        assert workflow.is_file()

    def test_agent_script_exists(self):
        """Test that the agent orchestration script exists."""
        script = (
            Path(__file__).parent.parent
            / "plugins"
            / "release-notes"
            / "scripts"
            / "agent_script.py"
        )
        assert script.is_file()

    def test_prompt_script_exists(self):
        """Test that the prompt template exists."""
        prompt = (
            Path(__file__).parent.parent
            / "plugins"
            / "release-notes"
            / "scripts"
            / "prompt.py"
        )
        assert prompt.is_file()

    def test_skills_symlink_exists(self):
        """Test that the skills symlink exists."""
        symlink = (
            Path(__file__).parent.parent
            / "plugins"
            / "release-notes"
            / "skills"
            / "releasenotes"
        )
        assert symlink.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
