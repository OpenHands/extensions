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
    _process_contributors,
    categorize_change,
    get_commits_between_tags,
    is_new_contributor,
)
from prompt import format_prompt
from validate_release_notes import (
    ReleaseNotesValidationError,
    append_reference_coverage_appendix,
    format_coverage_summary,
    missing_references,
    validate_release_notes_markdown,
)


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
            "user": {"login": "pr-author", "type": "User"},
            "created_at": "2026-03-05T12:00:00Z",
            "merged_at": "2026-03-06T09:30:00Z",
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
        assert change.author_type == "User"
        assert change.pr_created_at == "2026-03-05T12:00:00Z"
        assert change.pr_merged_at == "2026-03-06T09:30:00Z"

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

    @patch("generate_release_notes._search_merged_pull_requests_by_author")
    def test_is_new_contributor_rejects_prior_merged_pr(self, mock_search):
        """A contributor is not new if they already merged a PR earlier."""
        mock_search.return_value = [
            {"number": 41, "closed_at": "2026-03-01T10:00:00Z"},
            {"number": 42, "closed_at": "2026-03-06T09:30:00Z"},
        ]

        assert not is_new_contributor(
            "pr-author",
            "owner/repo",
            "2026-03-06T09:30:00Z",
            "token",
            current_pr_number=42,
            author_type="User",
        )

    @patch("generate_release_notes._search_merged_pull_requests_by_author")
    def test_is_new_contributor_accepts_first_merged_pr(self, mock_search):
        """A contributor is new when the only merged PR found is the current one."""
        mock_search.return_value = [{"number": 42, "closed_at": "2026-03-06T09:30:00Z"}]

        assert is_new_contributor(
            "pr-author",
            "owner/repo",
            "2026-03-06T09:30:00Z",
            "token",
            current_pr_number=42,
            author_type="User",
        )

    @patch("generate_release_notes._search_merged_pull_requests_by_author")
    def test_is_new_contributor_ignores_bot_accounts(self, mock_search):
        """Bot-authored PRs should never appear in new contributors."""
        assert not is_new_contributor(
            "dependabot[bot]",
            "owner/repo",
            "2026-03-06T09:30:00Z",
            "token",
            current_pr_number=42,
            author_type="Bot",
        )
        mock_search.assert_not_called()

    @patch("generate_release_notes.is_new_contributor")
    def test_process_contributors_uses_earliest_release_pr_per_author(self, mock_is_new):
        """Contributor detection should use the author's earliest PR in the release."""
        mock_is_new.side_effect = lambda author, *_args, **_kwargs: author == "alice"
        changes = [
            Change(
                message="Later PR",
                sha="bbb2222",
                author="alice",
                pr_number=43,
                author_type="User",
                pr_created_at="2026-03-10T12:00:00Z",
                pr_merged_at="2026-03-11T12:00:00Z",
            ),
            Change(
                message="Earlier PR",
                sha="aaa1111",
                author="alice",
                pr_number=42,
                author_type="User",
                pr_created_at="2026-03-05T12:00:00Z",
                pr_merged_at="2026-03-06T09:30:00Z",
            ),
            Change(
                message="Bot PR",
                sha="ccc3333",
                author="dependabot[bot]",
                pr_number=44,
                author_type="Bot",
                pr_created_at="2026-03-07T12:00:00Z",
                pr_merged_at="2026-03-08T12:00:00Z",
            ),
        ]

        contributors, new_contributors = _process_contributors(changes, "owner/repo", "token")

        assert [contributor.username for contributor in contributors] == ["alice", "dependabot[bot]"]
        assert [contributor.first_pr for contributor in contributors] == [42, 44]
        assert [contributor.username for contributor in new_contributors] == ["alice"]
        mock_is_new.assert_any_call(
            "alice",
            "owner/repo",
            "2026-03-06T09:30:00Z",
            "token",
            current_pr_number=42,
            author_type="User",
        )
        mock_is_new.assert_any_call(
            "dependabot[bot]",
            "owner/repo",
            "2026-03-08T12:00:00Z",
            "token",
            current_pr_number=44,
            author_type="Bot",
        )


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
        assert "aggressively compress the notes into a shorter set of higher-signal bullets" in prompt
        assert "if a section would have more than 5 bullets" in prompt
        assert "omit trivial, repetitive, or low-signal changes" in prompt
        assert "prefer end-user impact over implementation detail" in prompt
        assert "prioritize public APIs, user-visible capabilities, security fixes" in prompt
        assert "treat toolkit-maintainer or contributor-facing changes as secondary" in prompt
        assert "should stay in the small/internal appendix unless they are unusually significant" in prompt
        assert "public API additions still belong in `### ✨ New Features`" in prompt
        assert "omit prompt wording, benchmark plumbing, workflow maintenance" in prompt
        assert "start with a short, conversational 1-2 sentence overview" in prompt
        assert "optional top-level highlight bullets (maximum 3)" in prompt
        assert "every change bullet must end with explicit references" in prompt
        assert "format PR references as `(#123) @username`" in prompt
        assert "include every new contributor listed below" in prompt
        assert "Current tag: v1.2.0" in prompt
        assert "Full changelog URL:" in prompt


class TestValidation:
    """Tests for release notes attribution validation."""

    def test_validate_release_notes_accepts_grouped_prs_with_authors(self):
        """Grouped bullets are allowed when every PR and author is listed."""
        notes = ReleaseNotes(
            tag="v1.2.0",
            previous_tag="v1.1.0",
            date="2026-03-07",
            repo_name="owner/repo",
            changes={
                "features": [
                    Change(message="Add dark mode", sha="abc1234", author="alice", pr_number=42),
                    Change(message="Add theme presets", sha="def5678", author="bob", pr_number=43),
                ]
            },
        )
        markdown = """## [v1.2.0] - 2026-03-07

### ✨ New Features
- Add appearance improvements (#42) @alice, (#43) @bob

**Full Changelog**: https://github.com/owner/repo/compare/v1.1.0...v1.2.0
"""

        summary = validate_release_notes_markdown(markdown, notes)

        assert summary.bullet_count == 1
        assert summary.referenced_prs == [42, 43]
        assert summary.referenced_authors == ["alice", "bob"]

    def test_validate_release_notes_rejects_missing_author(self):
        """Each referenced PR must include the matching author handle."""
        notes = ReleaseNotes(
            tag="v1.2.0",
            previous_tag="v1.1.0",
            date="2026-03-07",
            repo_name="owner/repo",
            changes={
                "fixes": [
                    Change(message="Fix reconnect bug", sha="abc1234", author="alice", pr_number=42),
                ]
            },
        )
        markdown = """## [v1.2.0] - 2026-03-07

### 🐛 Bug Fixes
- Fix reconnect bug (#42)

**Full Changelog**: https://github.com/owner/repo/compare/v1.1.0...v1.2.0
"""

        with pytest.raises(ReleaseNotesValidationError, match=r"missing @alice"):
            validate_release_notes_markdown(markdown, notes)

    def test_validate_release_notes_rejects_missing_refs(self):
        """Each change bullet must contain explicit references."""
        notes = ReleaseNotes(
            tag="v1.2.0",
            previous_tag="v1.1.0",
            date="2026-03-07",
            repo_name="owner/repo",
            changes={
                "features": [
                    Change(message="Add dark mode", sha="abc1234", author="alice", pr_number=42),
                ]
            },
        )
        markdown = """## [v1.2.0] - 2026-03-07

### ✨ New Features
- Add dark mode @alice

**Full Changelog**: https://github.com/owner/repo/compare/v1.1.0...v1.2.0
"""

        with pytest.raises(
            ReleaseNotesValidationError,
            match=r"Bullet missing explicit PR/commit references",
        ):
            validate_release_notes_markdown(markdown, notes)

    def test_validate_release_notes_accepts_standalone_commit_refs(self):
        """Standalone commits can be referenced by short SHA plus author."""
        notes = ReleaseNotes(
            tag="v1.2.0",
            previous_tag="v1.1.0",
            date="2026-03-07",
            repo_name="owner/repo",
            changes={
                "docs": [
                    Change(message="Update docs", sha="abc1234fedcba", author="alice"),
                ]
            },
        )
        markdown = """## [v1.2.0] - 2026-03-07

### 📚 Documentation
- Update docs (abc1234) @alice

**Full Changelog**: https://github.com/owner/repo/compare/v1.1.0...v1.2.0
"""

        summary = validate_release_notes_markdown(markdown, notes)

        assert summary.referenced_commits == ["abc1234"]
        assert summary.referenced_authors == ["alice"]

    def test_validate_release_notes_accepts_accurate_new_contributor_section(self):
        """The validator should allow the exact expected new contributor entry."""
        notes = ReleaseNotes(
            tag="v1.2.0",
            previous_tag="v1.1.0",
            date="2026-03-07",
            repo_name="owner/repo",
            changes={
                "fixes": [
                    Change(message="Fix reconnect bug", sha="abc1234", author="alice", pr_number=42),
                ]
            },
            new_contributors=[Contributor(username="alice", first_pr=42, is_new=True)],
        )
        markdown = """## [v1.2.0] - 2026-03-07

### 🐛 Bug Fixes
- Fix reconnect bug (#42) @alice

### 👥 New Contributors
- @alice made their first contribution in #42

**Full Changelog**: https://github.com/owner/repo/compare/v1.1.0...v1.2.0
"""

        summary = validate_release_notes_markdown(markdown, notes)

        assert summary.referenced_prs == [42]
        assert summary.referenced_authors == ["alice"]

    def test_validate_release_notes_rejects_inaccurate_new_contributor_entry(self):
        """The validator should reject incorrect or hallucinated first-contribution bullets."""
        notes = ReleaseNotes(
            tag="v1.2.0",
            previous_tag="v1.1.0",
            date="2026-03-07",
            repo_name="owner/repo",
            changes={
                "fixes": [
                    Change(message="Fix reconnect bug", sha="abc1234", author="alice", pr_number=42),
                ]
            },
            new_contributors=[Contributor(username="alice", first_pr=42, is_new=True)],
        )
        markdown = """## [v1.2.0] - 2026-03-07

### 🐛 Bug Fixes
- Fix reconnect bug (#42) @alice

### 👥 New Contributors
- @alice made their first contribution in #99

**Full Changelog**: https://github.com/owner/repo/compare/v1.1.0...v1.2.0
"""

        with pytest.raises(
            ReleaseNotesValidationError,
            match=r"must reference #42",
        ):
            validate_release_notes_markdown(markdown, notes)


    def test_validate_release_notes_rejects_missing_new_contributor_section(self):
        """Expected new contributors must appear in the dedicated section."""
        notes = ReleaseNotes(
            tag="v1.2.0",
            previous_tag="v1.1.0",
            date="2026-03-07",
            repo_name="owner/repo",
            changes={
                "fixes": [
                    Change(message="Fix reconnect bug", sha="abc1234", author="alice", pr_number=42),
                ]
            },
            new_contributors=[Contributor(username="alice", first_pr=42, is_new=True)],
        )
        markdown = """## [v1.2.0] - 2026-03-07

### 🐛 Bug Fixes
- Fix reconnect bug (#42) @alice

**Full Changelog**: https://github.com/owner/repo/compare/v1.1.0...v1.2.0
"""

        with pytest.raises(
            ReleaseNotesValidationError,
            match=r"missing new contributor coverage for: @alice",
        ):
            validate_release_notes_markdown(markdown, notes)

    def test_format_coverage_summary_lists_prs_and_authors(self):
        """Coverage summary output is suitable for logs and evidence."""
        summary = format_coverage_summary(
            validate_release_notes_markdown(
                """## [v1.2.0] - 2026-03-07

### ✨ New Features
- Add dark mode (#42) @alice, (#43) @bob

**Full Changelog**: https://github.com/owner/repo/compare/v1.1.0...v1.2.0
""",
                ReleaseNotes(
                    tag="v1.2.0",
                    previous_tag="v1.1.0",
                    date="2026-03-07",
                    repo_name="owner/repo",
                    changes={
                        "features": [
                            Change(
                                message="Add dark mode",
                                sha="abc1234",
                                author="alice",
                                pr_number=42,
                            ),
                            Change(
                                message="Add theme presets",
                                sha="def5678",
                                author="bob",
                                pr_number=43,
                            ),
                        ]
                    },
                ),
            )
        )

        assert "PRs referenced: #42, #43" in summary
        assert "Authors referenced: @alice, @bob" in summary

    def test_validate_release_notes_allows_agent_to_recategorize_other_candidates(self):
        """The validator should allow refs for candidates the agent re-categorizes."""
        notes = ReleaseNotes(
            tag="v1.2.0",
            previous_tag="v1.1.0",
            date="2026-03-07",
            repo_name="owner/repo",
            changes={
                "other": [
                    Change(message="Export public API", sha="abc1234", author="alice", pr_number=42),
                ]
            },
        )
        markdown = """## [v1.2.0] - 2026-03-07

### ✨ New Features
- Export public API (#42) @alice

**Full Changelog**: https://github.com/owner/repo/compare/v1.1.0...v1.2.0
"""

        summary = validate_release_notes_markdown(markdown, notes)

        assert summary.referenced_prs == [42]
        assert summary.referenced_authors == ["alice"]

    def test_validate_release_notes_rejects_missing_pr_coverage(self):
        """Validation fails if any release-range PR is omitted entirely."""
        notes = ReleaseNotes(
            tag="v1.2.0",
            previous_tag="v1.1.0",
            date="2026-03-07",
            repo_name="owner/repo",
            changes={
                "features": [
                    Change(message="Add dark mode", sha="abc1234", author="alice", pr_number=42),
                    Change(message="Add theme presets", sha="def5678", author="bob", pr_number=43),
                ]
            },
        )
        markdown = """## [v1.2.0] - 2026-03-07

### ✨ New Features
- Add dark mode (#42) @alice

**Full Changelog**: https://github.com/owner/repo/compare/v1.1.0...v1.2.0
"""

        with pytest.raises(
            ReleaseNotesValidationError,
            match=r"missing PR/commit coverage for: #43",
        ):
            validate_release_notes_markdown(markdown, notes)

        assert missing_references(markdown, notes) == ["#43"]

    def test_append_reference_coverage_appendix_adds_missing_refs(self):
        """A deterministic appendix covers PRs the agent chose not to mention."""
        notes = ReleaseNotes(
            tag="v1.2.0",
            previous_tag="v1.1.0",
            date="2026-03-07",
            repo_name="owner/repo",
            changes={
                "features": [
                    Change(message="Add dark mode", sha="abc1234", author="alice", pr_number=42),
                ],
                "internal": [
                    Change(message="Update CI", sha="def5678", author="bob", pr_number=43),
                    Change(message="Refactor workflow", sha="fedcba9", author="bob", pr_number=44),
                ],
            },
        )
        markdown = """## [v1.2.0] - 2026-03-07

This release focuses on polish and delivery improvements.

### ✨ New Features
- Add dark mode (#42) @alice

**Full Changelog**: https://github.com/owner/repo/compare/v1.1.0...v1.2.0
"""

        augmented = append_reference_coverage_appendix(markdown, notes)

        assert "### 🔎 Small Fixes/Internal Changes" in augmented
        assert "- @bob: #43, #44" in augmented
        assert augmented.count("@bob") == 1
        summary = validate_release_notes_markdown(augmented, notes)
        assert summary.referenced_prs == [42, 43, 44]


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

    def test_validator_script_exists(self):
        """Test that the attribution validator script exists."""
        validator = (
            Path(__file__).parent.parent
            / "plugins"
            / "release-notes"
            / "scripts"
            / "validate_release_notes.py"
        )
        assert validator.is_file()

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
            / "release-notes"
        )
        assert symlink.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
