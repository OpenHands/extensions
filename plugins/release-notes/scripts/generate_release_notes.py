#!/usr/bin/env python3
"""
Release Notes Generator

Generates consistent, well-structured release notes from git history.
Categorizes changes based on conventional commit prefixes and PR labels.

Environment Variables:
    GITHUB_TOKEN: GitHub token for API access (required)
    TAG: The release tag to generate notes for (required)
    PREVIOUS_TAG: Override automatic detection of previous release (optional)
    INCLUDE_INTERNAL: Include internal/infrastructure changes (default: false)
    OUTPUT_FORMAT: Output format - 'release' or 'changelog' (default: release)
    REPO_NAME: Repository name in format owner/repo (required)
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# Category definitions with emojis and patterns
CATEGORIES = {
    "breaking": {
        "emoji": "⚠️",
        "title": "Breaking Changes",
        "commit_patterns": [r"^BREAKING[\s\-:]", r"!:"],
        "labels": ["breaking-change", "breaking"],
    },
    "features": {
        "emoji": "✨",
        "title": "New Features",
        "commit_patterns": [r"^feat(?:ure)?[\s\-:\(]"],
        "labels": ["enhancement", "feature"],
    },
    "fixes": {
        "emoji": "🐛",
        "title": "Bug Fixes",
        "commit_patterns": [r"^fix(?:es)?[\s\-:\(]", r"^bugfix[\s\-:\(]"],
        "labels": ["bug", "bugfix"],
    },
    "docs": {
        "emoji": "📚",
        "title": "Documentation",
        "commit_patterns": [r"^docs?[\s\-:\(]"],
        "labels": ["documentation", "docs"],
    },
    "internal": {
        "emoji": "🏗️",
        "title": "Internal/Infrastructure",
        "commit_patterns": [
            r"^chore[\s\-:\(]",
            r"^ci[\s\-:\(]",
            r"^refactor[\s\-:\(]",
            r"^test[\s\-:\(]",
            r"^build[\s\-:\(]",
            r"^style[\s\-:\(]",
            r"^perf[\s\-:\(]",
        ],
        "labels": ["internal", "chore", "ci", "dependencies"],
    },
}


@dataclass
class Change:
    """Represents a single change/commit in the release."""

    message: str
    sha: str
    author: str
    pr_number: int | None = None
    pr_labels: list[str] = field(default_factory=list)
    category: str = "other"

    def to_markdown(self, repo_name: str) -> str:
        """Format the change as a markdown list item."""
        # Clean up the message - remove conventional commit prefix
        msg = self.message.strip()
        for pattern in [
            r"^(feat|fix|docs?|chore|ci|refactor|test|build|style|perf|BREAKING)(\(.+?\))?[:\s]+",
        ]:
            msg = re.sub(pattern, "", msg, flags=re.IGNORECASE)
        msg = msg.strip()

        # Capitalize first letter
        if msg:
            msg = msg[0].upper() + msg[1:]

        # Add PR link if available
        if self.pr_number:
            msg += f" (#{self.pr_number})"

        # Add author
        if self.author:
            msg += f" @{self.author}"

        return f"- {msg}"


@dataclass
class Contributor:
    """Represents a contributor to the release."""

    username: str
    first_pr: int | None = None
    is_new: bool = False


@dataclass
class ReleaseNotes:
    """Holds all data needed to generate release notes."""

    tag: str
    previous_tag: str
    date: str
    repo_name: str
    changes: dict[str, list[Change]] = field(default_factory=dict)
    contributors: list[Contributor] = field(default_factory=list)
    new_contributors: list[Contributor] = field(default_factory=list)

    def to_markdown(self, include_internal: bool = False) -> str:
        """Generate the full release notes markdown."""
        lines = [f"## [{self.tag}] - {self.date}", ""]

        # Order of categories to display
        category_order = ["breaking", "features", "fixes", "docs"]
        if include_internal:
            category_order.append("internal")

        # Add categorized changes
        for category in category_order:
            changes = self.changes.get(category, [])
            if changes:
                cat_info = CATEGORIES[category]
                lines.append(f"### {cat_info['emoji']} {cat_info['title']}")
                for change in changes:
                    lines.append(change.to_markdown(self.repo_name))
                lines.append("")

        # Add uncategorized changes if any
        other_changes = self.changes.get("other", [])
        if other_changes:
            lines.append("### Other Changes")
            for change in other_changes:
                lines.append(change.to_markdown(self.repo_name))
            lines.append("")

        # Add new contributors section
        if self.new_contributors:
            lines.append("### 👥 New Contributors")
            for contrib in self.new_contributors:
                pr_text = f" in #{contrib.first_pr}" if contrib.first_pr else ""
                lines.append(f"- @{contrib.username} made their first contribution{pr_text}")
            lines.append("")

        # Add full changelog link
        owner, repo = self.repo_name.split("/")
        lines.append(
            f"**Full Changelog**: https://github.com/{self.repo_name}/compare/"
            f"{self.previous_tag}...{self.tag}"
        )

        return "\n".join(lines)


def get_env(name: str, default: str | None = None, required: bool = False) -> str:
    """Get an environment variable."""
    value = os.getenv(name, default)
    if required and not value:
        print(f"Error: {name} environment variable is required")
        sys.exit(1)
    return value or ""


def github_api_request(
    endpoint: str,
    token: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
) -> Any:
    """Make a request to the GitHub API."""
    url = f"https://api.github.com{endpoint}"
    request = urllib.request.Request(url, method=method)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")

    if data:
        request.add_header("Content-Type", "application/json")
        request.data = json.dumps(data).encode("utf-8")

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        details = (e.read() or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"GitHub API request failed: HTTP {e.code} {e.reason}. {details}"
        ) from e


def get_tags(repo_name: str, token: str) -> list[dict[str, Any]]:
    """Get all tags from the repository, sorted by creation date."""
    tags = []
    page = 1
    per_page = 100

    while True:
        endpoint = f"/repos/{repo_name}/tags?per_page={per_page}&page={page}"
        page_tags = github_api_request(endpoint, token)
        if not page_tags:
            break
        tags.extend(page_tags)
        if len(page_tags) < per_page:
            break
        page += 1

    return tags


def find_previous_tag(
    current_tag: str, tags: list[dict[str, Any]]
) -> str | None:
    """Find the previous release tag before the current one."""
    # Filter to only semver tags
    semver_pattern = re.compile(r"^v?\d+\.\d+\.\d+")
    semver_tags = [t for t in tags if semver_pattern.match(t["name"])]

    # Find current tag index
    current_idx = None
    for i, tag in enumerate(semver_tags):
        if tag["name"] == current_tag:
            current_idx = i
            break

    if current_idx is None:
        return None

    # Return the next tag (which is the previous release since tags are sorted newest first)
    if current_idx + 1 < len(semver_tags):
        return semver_tags[current_idx + 1]["name"]

    return None


def get_commits_between_tags(
    repo_name: str, base_tag: str, head_tag: str, token: str
) -> list[dict[str, Any]]:
    """Get all commits between two tags."""
    endpoint = f"/repos/{repo_name}/compare/{base_tag}...{head_tag}"
    response = github_api_request(endpoint, token)
    return response.get("commits", [])


def get_pr_for_commit(
    repo_name: str, sha: str, token: str
) -> dict[str, Any] | None:
    """Get the PR associated with a commit (if any)."""
    endpoint = f"/repos/{repo_name}/commits/{sha}/pulls"
    try:
        prs = github_api_request(endpoint, token)
        if prs:
            # Return the first merged PR
            for pr in prs:
                if pr.get("merged_at"):
                    return pr
            # If no merged PR, return the first one
            return prs[0]
    except Exception:
        pass
    return None


def categorize_change(change: Change) -> str:
    """Determine the category for a change based on commit message and PR labels."""
    message_lower = change.message.lower()

    # Check each category
    for category, info in CATEGORIES.items():
        # Check commit message patterns
        for pattern in info["commit_patterns"]:
            if re.search(pattern, change.message, re.IGNORECASE):
                return category

        # Check PR labels
        for label in change.pr_labels:
            if label.lower() in [l.lower() for l in info["labels"]]:
                return category

    return "other"


def is_new_contributor(
    author: str, repo_name: str, before_date: str, token: str
) -> bool:
    """Check if this is the author's first contribution to the repository."""
    # Search for commits by this author before the given date
    endpoint = (
        f"/repos/{repo_name}/commits"
        f"?author={author}&until={before_date}&per_page=1"
    )
    try:
        commits = github_api_request(endpoint, token)
        return len(commits) == 0
    except Exception:
        return False


def get_tag_date(repo_name: str, tag: str, token: str) -> str:
    """Get the date when a tag was created."""
    endpoint = f"/repos/{repo_name}/git/refs/tags/{tag}"
    try:
        ref = github_api_request(endpoint, token)
        # Get the commit or tag object
        obj_sha = ref["object"]["sha"]
        obj_type = ref["object"]["type"]

        if obj_type == "tag":
            # Annotated tag - get the tag object
            tag_endpoint = f"/repos/{repo_name}/git/tags/{obj_sha}"
            tag_obj = github_api_request(tag_endpoint, token)
            date_str = tag_obj["tagger"]["date"]
        else:
            # Lightweight tag - get the commit
            commit_endpoint = f"/repos/{repo_name}/git/commits/{obj_sha}"
            commit_obj = github_api_request(commit_endpoint, token)
            date_str = commit_obj["committer"]["date"]

        # Parse and format the date
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def generate_release_notes(
    tag: str,
    previous_tag: str | None,
    repo_name: str,
    token: str,
    include_internal: bool = False,
) -> ReleaseNotes:
    """Generate release notes for the given tag."""
    # Get all tags
    tags = get_tags(repo_name, token)

    # Find previous tag if not provided
    if not previous_tag:
        previous_tag = find_previous_tag(tag, tags)

    if not previous_tag:
        print(f"Warning: Could not find previous tag for {tag}")
        previous_tag = tags[-1]["name"] if tags else "HEAD~100"

    print(f"Generating release notes: {previous_tag} -> {tag}")

    # Get tag date
    tag_date = get_tag_date(repo_name, tag, token)

    # Get commits between tags
    commits = get_commits_between_tags(repo_name, previous_tag, tag, token)
    print(f"Found {len(commits)} commits")

    # Process commits into changes
    changes: dict[str, list[Change]] = {cat: [] for cat in CATEGORIES}
    changes["other"] = []
    contributors: dict[str, Contributor] = {}
    new_contributors: list[Contributor] = []

    for commit_data in commits:
        sha = commit_data["sha"]
        message = commit_data["commit"]["message"].split("\n")[0]  # First line only
        author = commit_data.get("author", {}).get("login", "")

        # Skip merge commits
        if message.lower().startswith("merge "):
            continue

        # Get PR info
        pr_number = None
        pr_labels: list[str] = []
        pr = get_pr_for_commit(repo_name, sha, token)
        if pr:
            pr_number = pr["number"]
            pr_labels = [label["name"] for label in pr.get("labels", [])]
            # Use PR author if commit author not available
            if not author:
                author = pr.get("user", {}).get("login", "")

        # Create change object
        change = Change(
            message=message,
            sha=sha,
            author=author,
            pr_number=pr_number,
            pr_labels=pr_labels,
        )

        # Categorize
        change.category = categorize_change(change)

        # Add to appropriate category
        if change.category in changes:
            changes[change.category].append(change)
        else:
            changes["other"].append(change)

        # Track contributor
        if author and author not in contributors:
            contrib = Contributor(username=author, first_pr=pr_number)
            contributors[author] = contrib

            # Check if new contributor
            if is_new_contributor(author, repo_name, f"{tag_date}T00:00:00Z", token):
                contrib.is_new = True
                new_contributors.append(contrib)

    return ReleaseNotes(
        tag=tag,
        previous_tag=previous_tag,
        date=tag_date,
        repo_name=repo_name,
        changes=changes,
        contributors=list(contributors.values()),
        new_contributors=new_contributors,
    )


def set_github_output(name: str, value: str) -> None:
    """Set a GitHub Actions output variable."""
    output_file = os.getenv("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            # Handle multiline values
            if "\n" in value:
                delimiter = "EOF"
                f.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")
            else:
                f.write(f"{name}={value}\n")
    else:
        print(f"::set-output name={name}::{value}")


def main():
    """Main entry point."""
    # Get configuration from environment
    token = get_env("GITHUB_TOKEN", required=True)
    tag = get_env("TAG", required=True)
    previous_tag = get_env("PREVIOUS_TAG") or None
    include_internal = get_env("INCLUDE_INTERNAL", "false").lower() == "true"
    output_format = get_env("OUTPUT_FORMAT", "release")
    repo_name = get_env("REPO_NAME", required=True)

    print(f"Generating release notes for {repo_name}")
    print(f"Tag: {tag}")
    print(f"Previous tag: {previous_tag or 'auto-detect'}")
    print(f"Include internal: {include_internal}")
    print(f"Output format: {output_format}")

    # Generate release notes
    notes = generate_release_notes(
        tag=tag,
        previous_tag=previous_tag,
        repo_name=repo_name,
        token=token,
        include_internal=include_internal,
    )

    # Generate markdown
    markdown = notes.to_markdown(include_internal=include_internal)

    # Write to file
    with open("release_notes.md", "w") as f:
        f.write(markdown)

    print("\n" + "=" * 60)
    print("Generated Release Notes:")
    print("=" * 60)
    print(markdown)
    print("=" * 60)

    # Set GitHub Actions outputs
    set_github_output("release_notes", markdown)
    set_github_output("previous_tag", notes.previous_tag)
    set_github_output("commit_count", str(sum(len(c) for c in notes.changes.values())))
    set_github_output("contributor_count", str(len(notes.contributors)))
    set_github_output("new_contributor_count", str(len(notes.new_contributors)))

    print("\nRelease notes generated successfully!")


if __name__ == "__main__":
    main()
