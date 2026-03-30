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

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# Category definitions with emojis and patterns
# Patterns match both conventional commit style (feat:, fix:) and bracket/paren style ([Feat]:, (Fix):)
CATEGORIES = {
    "breaking": {
        "emoji": "⚠️",
        "title": "Breaking Changes",
        "commit_patterns": [r"^BREAKING[\s\-:]", r"!:", r"^\[?BREAKING\]?[\s\-:]"],
        "labels": ["breaking-change", "breaking"],
    },
    "features": {
        "emoji": "✨",
        "title": "New Features",
        "commit_patterns": [
            r"^feat(?:ure)?[\s\-:\(]",
            r"^[\[\(]feat(?:ure)?[\]\)][\s\-:]*",  # [Feat]: or (Feat):
        ],
        "labels": ["enhancement", "feature"],
    },
    "fixes": {
        "emoji": "🐛",
        "title": "Bug Fixes",
        "commit_patterns": [
            r"^fix(?:es)?[\s\-:\(]",
            r"^bugfix[\s\-:\(]",
            r"^[\[\(]fix(?:es)?[\]\)][\s\-:]*",  # [Fix]: or (Fix):
            r"^[\[\(]hotfix[\]\)][\s\-:]*",  # [Hotfix]: or (Hotfix):
            r"^hotfix[\s\-:\(]",
        ],
        "labels": ["bug", "bugfix"],
    },
    "docs": {
        "emoji": "📚",
        "title": "Documentation",
        "commit_patterns": [
            r"^docs?[\s\-:\(]",
            r"^[\[\(]docs?[\]\)][\s\-:]*",  # [Docs]: or (Docs):
        ],
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
            r"^[\[\(]chore[\]\)][\s\-:]*",  # [Chore]: or (Chore):
            r"^[\[\(]ci[\]\)][\s\-:]*",
            r"^[\[\(]refactor[\]\)][\s\-:]*",
            r"^[\[\(]test[\]\)][\s\-:]*",
        ],
        "labels": ["internal", "chore", "ci", "dependencies"],
    },
}

KEYWORD_PATTERNS = {
    "docs": [
        r"\bdocs?\b",
        r"\bdocumentation\b",
        r"\breadme\b",
        r"\bchangelog\b",
        r"\bguide\b",
        r"\bopenapi\b",
    ],
    "internal": [
        r"\bci\b",
        r"\blint\b",
        r"\btyping\b",
        r"\brefactor\b",
        r"\bdebug\b",
        r"\bpre-commit\b",
        r"\bdockerfile\b",
        r"\bdependencies?\b",
        r"\brelease\b",
        r"\btool descriptions?\b",
        r"\bmicroagents?\b",
    ],
    "fixes": [
        r"\bfix(?:es|ed)?\b",
        r"\bbug\b",
        r"\berror\b",
        r"\bfail(?:ed|ing)?\b",
        r"\bissue\b",
        r"\bcrash\b",
        r"\btimeout\b",
        r"\bleak\b",
        r"\bmissing\b",
        r"\berroneous\b",
        r"\breconnect\b",
        r"\breset\b",
    ],
    "features": [
        r"^(add|allow|support|enable|implement|introduce|create|provide|improve)\b",
    ],
}


@dataclass
class Change:
    """Represents a single change/commit in the release."""

    message: str
    sha: str
    author: str
    pr_number: int | None = None
    pr_labels: list[str] = field(default_factory=list)
    body: str = ""
    url: str = ""
    author_type: str = ""
    pr_created_at: str = ""
    pr_merged_at: str = ""
    category: str = "other"

    def to_markdown(self, repo_name: str) -> str:
        """Format the change as a markdown list item."""
        # Clean up the message - remove conventional commit prefix
        # Supports multiple formats:
        #   - feat: message, fix(scope): message, feat!: breaking
        #   - [Feat]: message, (Fix): message, [Chore]: message
        msg = self.message.strip()
        for pattern in [
            # Standard conventional commit: feat:, fix(scope):, feat!:
            r"^(feat|fix|docs?|chore|ci|refactor|test|build|style|perf|BREAKING|hotfix)(\(.+?\))?!?:\s+",
            # Bracket/paren style: [Feat]:, (Fix):, [Hotfix]:
            r"^[\[\(](feat|fix|docs?|chore|ci|refactor|test|build|style|perf|BREAKING|hotfix)[\]\)][\s\-:]+",
        ]:
            msg = re.sub(pattern, "", msg, flags=re.IGNORECASE)
        msg = msg.strip()

        # Capitalize first letter
        if msg:
            msg = msg[0].upper() + msg[1:]

        # Add PR link if available and not already in the message
        if self.pr_number:
            pr_ref = f"#{self.pr_number}"
            if pr_ref not in msg:
                msg += f" ({pr_ref})"

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
    commit_count: int = 0
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

        # Add new contributors section
        if self.new_contributors:
            lines.append("### 👥 New Contributors")
            for contrib in self.new_contributors:
                pr_text = f" in #{contrib.first_pr}" if contrib.first_pr else ""
                lines.append(f"- @{contrib.username} made their first contribution{pr_text}")
            lines.append("")

        # Add full changelog link
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
    # Filter to only semver tags (with optional pre-release/build metadata)
    semver_pattern = re.compile(r"^v?\d+\.\d+\.\d+(?:[.-].*)?$")
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
    commits = response.get("commits", [])

    total_commits = response.get("total_commits")
    if isinstance(total_commits, int) and total_commits > len(commits):
        print(
            "Warning: GitHub compare API truncated the commit list; "
            "release notes may be incomplete.",
            file=sys.stderr,
        )

    return commits


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
    except Exception as e:
        # Log but don't fail - PR data is optional
        print(f"Warning: Could not fetch PR for commit {sha[:7]}: {e}", file=sys.stderr)
    return None


def _matches_any_pattern(text: str, patterns: list[str]) -> bool:
    """Return True if the text matches any of the provided regex patterns."""
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def categorize_change(change: Change) -> str:
    """Determine the category for a change based on commit message and PR labels."""
    # Exact matches first: conventional commit prefixes are the strongest signal.
    for category, info in CATEGORIES.items():
        if _matches_any_pattern(change.message, info["commit_patterns"]):
            return category

    # Strong keyword matches help suppress noisy internal-only PRs even when a
    # repository applies broad labels like `bug` or `enhancement`.
    for category in ["docs", "internal"]:
        if _matches_any_pattern(change.message, KEYWORD_PATTERNS[category]):
            return category

    label_names = [label.lower() for label in change.pr_labels]
    for category, info in CATEGORIES.items():
        if any(label.lower() in label_names for label in info["labels"]):
            return category

    # Fallback heuristics make PR-title based release notes more useful while
    # still preferring user-facing categories over noisy implementation details.
    for category in ["fixes", "features"]:
        if _matches_any_pattern(change.message, KEYWORD_PATTERNS[category]):
            return category

    return "other"


def _parse_github_timestamp(timestamp: str) -> datetime:
    """Parse a GitHub timestamp into a timezone-aware datetime."""
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def _is_bot_author(author: str, author_type: str = "") -> bool:
    """Return True when the contributor is clearly a bot account."""
    normalized_type = author_type.lower()
    return normalized_type == "bot" or author.endswith("[bot]")


def _search_merged_pull_requests_by_author(
    repo_name: str, author: str, token: str
) -> list[dict[str, Any]]:
    """Return merged PRs in the repo authored by the given GitHub user."""
    results: list[dict[str, Any]] = []
    page = 1
    query = f'repo:{repo_name} is:pr is:merged author:"{author}"'
    encoded_query = urllib.parse.quote(query)

    while True:
        endpoint = (
            f"/search/issues?q={encoded_query}&per_page=100&page={page}"
            "&sort=created&order=asc"
        )
        response = github_api_request(endpoint, token)
        items = response.get("items", [])
        results.extend(items)
        if len(items) < 100:
            break
        page += 1

    return results


def is_new_contributor(
    author: str,
    repo_name: str,
    before_timestamp: str,
    token: str,
    current_pr_number: int | None = None,
    author_type: str = "",
) -> bool:
    """Check whether a human author's earliest release PR is their first merged PR."""
    if not author or _is_bot_author(author, author_type) or not before_timestamp:
        return False

    threshold = _parse_github_timestamp(before_timestamp)

    try:
        for pr in _search_merged_pull_requests_by_author(repo_name, author, token):
            if current_pr_number and pr.get("number") == current_pr_number:
                continue
            closed_at = pr.get("closed_at")
            if not closed_at:
                continue
            if _parse_github_timestamp(closed_at) < threshold:
                return False
        return True
    except Exception as e:
        print(f"Warning: Could not check contributor history for {author}: {e}", file=sys.stderr)
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
    except Exception as e:
        # Log but fall back to current date
        print(f"Warning: Could not get tag date for {tag}: {e}", file=sys.stderr)
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _process_commit(
    commit_data: dict[str, Any], repo_name: str, token: str
) -> Change | None:
    """Process a single commit into a Change object."""
    sha = commit_data["sha"]
    message = commit_data["commit"]["message"].split("\n")[0]  # First line only
    author = commit_data.get("author", {}).get("login", "")

    # Skip merge commits
    if message.lower().startswith("merge "):
        return None

    # Get PR info
    pr_number = None
    pr_labels: list[str] = []
    pr = get_pr_for_commit(repo_name, sha, token)
    body = ""
    url = ""
    author_type = ""
    pr_created_at = ""
    pr_merged_at = ""
    if pr:
        pr_number = pr["number"]
        pr_labels = [label["name"] for label in pr.get("labels", [])]
        author = pr.get("user", {}).get("login", "") or author
        author_type = pr.get("user", {}).get("type", "") or ""
        message = pr.get("title") or message
        body = pr.get("body") or ""
        url = pr.get("html_url") or ""
        pr_created_at = pr.get("created_at") or ""
        pr_merged_at = pr.get("merged_at") or ""

    return Change(
        message=message,
        sha=sha,
        author=author,
        pr_number=pr_number,
        pr_labels=pr_labels,
        body=body,
        url=url,
        author_type=author_type,
        pr_created_at=pr_created_at,
        pr_merged_at=pr_merged_at,
    )


def _dedupe_changes(changes_list: list[Change]) -> list[Change]:
    """Collapse multiple commits from the same PR into one release-note entry."""
    deduped: list[Change] = []
    seen_keys: set[str] = set()

    for change in changes_list:
        key = f"pr:{change.pr_number}" if change.pr_number else f"sha:{change.sha}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(change)

    return deduped


def _categorize_changes(
    changes_list: list[Change],
) -> dict[str, list[Change]]:
    """Categorize a list of changes by type."""
    categorized: dict[str, list[Change]] = {cat: [] for cat in CATEGORIES}
    categorized["other"] = []

    for change in changes_list:
        change.category = categorize_change(change)
        if change.category in categorized:
            categorized[change.category].append(change)
        else:
            categorized["other"].append(change)

    return categorized


def _process_contributors(
    changes_list: list[Change],
    repo_name: str,
    token: str,
) -> tuple[list[Contributor], list[Contributor]]:
    """Extract contributors and identify first-time human PR contributors."""
    contributors: dict[str, Contributor] = {}
    earliest_pr_by_author: dict[str, Change] = {}
    new_contributors: list[Contributor] = []

    for change in changes_list:
        author = change.author
        if not author:
            continue

        contrib = contributors.get(author)
        if contrib is None:
            contrib = Contributor(username=author, first_pr=change.pr_number)
            contributors[author] = contrib
        elif contrib.first_pr is None and change.pr_number:
            contrib.first_pr = change.pr_number

        if not change.pr_number:
            continue

        candidate_timestamp = change.pr_merged_at or change.pr_created_at
        current = earliest_pr_by_author.get(author)
        current_timestamp = (current.pr_merged_at or current.pr_created_at) if current else ""
        if current is None or (
            candidate_timestamp
            and (not current_timestamp or candidate_timestamp < current_timestamp)
        ):
            earliest_pr_by_author[author] = change
            contrib.first_pr = change.pr_number

    for author, contrib in contributors.items():
        first_pr_change = earliest_pr_by_author.get(author)
        if not first_pr_change:
            continue

        first_pr_timestamp = first_pr_change.pr_merged_at or first_pr_change.pr_created_at
        if is_new_contributor(
            author,
            repo_name,
            first_pr_timestamp,
            token,
            current_pr_number=first_pr_change.pr_number,
            author_type=first_pr_change.author_type,
        ):
            contrib.is_new = True
            new_contributors.append(contrib)

    return list(contributors.values()), new_contributors


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

    # Phase 1: Process commits into Change objects
    raw_changes = [
        change
        for c in commits
        if (change := _process_commit(c, repo_name, token)) is not None
    ]

    # Phase 2: Collapse multiple commits from the same PR into a single entry.
    changes = _dedupe_changes(raw_changes)

    # Phase 3: Categorize changes
    categorized = _categorize_changes(changes)

    # Phase 4: Extract and identify contributors
    contributors, new_contributors = _process_contributors(changes, repo_name, token)

    return ReleaseNotes(
        tag=tag,
        previous_tag=previous_tag,
        date=tag_date,
        repo_name=repo_name,
        commit_count=len(commits),
        changes=categorized,
        contributors=contributors,
        new_contributors=new_contributors,
    )


def set_github_output(name: str, value: str) -> None:
    """Set a GitHub Actions output variable."""
    output_file = os.getenv("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            # Handle multiline values
            if "\n" in value:
                delimiter = f"EOF_{os.urandom(4).hex()}"
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
    set_github_output("commit_count", str(notes.commit_count))
    set_github_output("contributor_count", str(len(notes.contributors)))
    set_github_output("new_contributor_count", str(len(notes.new_contributors)))

    print("\nRelease notes generated successfully!")


if __name__ == "__main__":
    main()
