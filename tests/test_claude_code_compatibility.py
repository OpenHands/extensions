"""Test Claude Code marketplace compatibility.

Claude Code expects the marketplace manifest at .claude-plugin/marketplace.json
when adding a repository as a marketplace via `claude plugin marketplace add owner/repo`.
"""

import json
from pathlib import Path


def get_repo_root():
    """Get the path to the repository root."""
    return Path(__file__).parent.parent


class TestClaudeCodeCompatibility:
    """Test that the repository maintains Claude Code compatibility."""

    def test_claude_plugin_directory_exists(self):
        """Verify the .claude-plugin directory exists."""
        claude_plugin_dir = get_repo_root() / ".claude-plugin"
        assert claude_plugin_dir.exists(), (
            ".claude-plugin directory not found. "
            "Claude Code expects marketplace at .claude-plugin/marketplace.json"
        )
        assert claude_plugin_dir.is_dir(), ".claude-plugin should be a directory"

    def test_marketplace_json_exists_at_expected_location(self):
        """Verify marketplace.json exists at .claude-plugin/marketplace.json."""
        marketplace_path = get_repo_root() / ".claude-plugin" / "marketplace.json"
        assert marketplace_path.exists(), (
            ".claude-plugin/marketplace.json not found. "
            "Claude Code expects this file when adding repo as marketplace via "
            "`claude plugin marketplace add owner/repo`"
        )

    def test_marketplace_json_is_readable(self):
        """Verify marketplace.json is readable (symlink resolves correctly)."""
        marketplace_path = get_repo_root() / ".claude-plugin" / "marketplace.json"
        try:
            content = marketplace_path.read_text()
            assert len(content) > 0, "marketplace.json is empty"
        except Exception as e:
            raise AssertionError(f"Failed to read marketplace.json: {e}")

    def test_marketplace_json_is_valid_json(self):
        """Verify marketplace.json contains valid JSON."""
        marketplace_path = get_repo_root() / ".claude-plugin" / "marketplace.json"
        content = marketplace_path.read_text()
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise AssertionError(f"marketplace.json contains invalid JSON: {e}")
        assert isinstance(data, dict), "marketplace.json should contain a JSON object"

    def test_marketplace_json_has_required_fields(self):
        """Verify marketplace.json has the required fields for Claude Code."""
        marketplace_path = get_repo_root() / ".claude-plugin" / "marketplace.json"
        content = marketplace_path.read_text()
        data = json.loads(content)

        required_fields = ["name", "plugins"]
        missing = [f for f in required_fields if f not in data]
        assert len(missing) == 0, f"marketplace.json missing required fields: {missing}"

    def test_marketplace_symlink_points_to_canonical_location(self):
        """Verify .claude-plugin/marketplace.json is a symlink to marketplaces/default.json."""
        marketplace_path = get_repo_root() / ".claude-plugin" / "marketplace.json"
        canonical_path = get_repo_root() / "marketplaces" / "default.json"

        assert marketplace_path.is_symlink(), (
            ".claude-plugin/marketplace.json should be a symlink to "
            "marketplaces/default.json to keep a single source of truth"
        )

        resolved = marketplace_path.resolve()
        assert resolved == canonical_path.resolve(), (
            f".claude-plugin/marketplace.json should resolve to {canonical_path}, "
            f"but resolves to {resolved}"
        )

    def test_canonical_and_claude_location_have_same_content(self):
        """Verify both marketplace locations have identical content."""
        claude_path = get_repo_root() / ".claude-plugin" / "marketplace.json"
        canonical_path = get_repo_root() / "marketplaces" / "default.json"

        claude_content = claude_path.read_text()
        canonical_content = canonical_path.read_text()

        assert claude_content == canonical_content, (
            "Content mismatch between .claude-plugin/marketplace.json and "
            "marketplaces/default.json. They should be identical."
        )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
