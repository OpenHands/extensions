#!/usr/bin/env python3
"""Validate attribution coverage in generated release notes."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass

from generate_release_notes import CATEGORIES, ReleaseNotes, generate_release_notes, get_env

PR_REF_PATTERN = re.compile(r"#(\d+)\b")
COMMIT_REF_PATTERN = re.compile(r"\(([0-9a-f]{7,40})\)")
USER_HANDLE_PATTERN = re.compile(r"@([A-Za-z0-9][A-Za-z0-9_\-\[\]]*)")
NEW_CONTRIBUTORS_HEADING = "### 👥 New Contributors"
COVERAGE_HEADING = "### 🔎 Small Fixes/Internal Changes"
REFERENCE_CATEGORY_ORDER = ["breaking", "features", "fixes", "docs", "internal", "other"]


@dataclass
class CoverageSummary:
    """Summary of attribution coverage found in release notes."""

    bullet_count: int
    referenced_prs: list[int]
    referenced_authors: list[str]
    referenced_commits: list[str]
    required_reference_count: int


@dataclass
class ValidationContext:
    """Parsed validation context for a single release note run."""

    reference_authors: dict[str, str]
    reference_order: list[str]
    change_section_headings: set[str]
    expected_new_contributors: dict[str, int | None]


class ReleaseNotesValidationError(ValueError):
    """Raised when generated release notes violate attribution rules."""


@dataclass
class MentionScanResult:
    """Collected ref/author coverage from markdown."""

    covered_refs: set[str]
    referenced_prs: set[int]
    referenced_authors: set[str]
    referenced_commits: set[str]
    found_new_contributors: dict[str, int | None]
    bullet_count: int
    errors: list[str]


def build_validation_context(
    notes: ReleaseNotes, include_internal: bool = False
) -> ValidationContext:
    """Build the reference and section metadata used for validation."""
    del include_internal  # Coverage should include every candidate the release may cite.

    reference_authors: dict[str, str] = {}
    reference_order: list[str] = []
    expected_new_contributors = {
        contributor.username: contributor.first_pr for contributor in notes.new_contributors
    }
    change_section_headings = {
        f"### {CATEGORIES[category]['emoji']} {CATEGORIES[category]['title']}"
        for category in CATEGORIES
    }

    for category in REFERENCE_CATEGORY_ORDER:
        for change in notes.changes.get(category, []):
            ref = f"#{change.pr_number}" if change.pr_number else change.sha[:7].lower()
            if ref in reference_authors:
                continue
            reference_authors[ref] = change.author
            reference_order.append(ref)

    return ValidationContext(
        reference_authors=reference_authors,
        reference_order=reference_order,
        change_section_headings=change_section_headings,
        expected_new_contributors=expected_new_contributors,
    )


def _extract_explicit_references(text: str) -> list[str]:
    refs = [f"#{match}" for match in PR_REF_PATTERN.findall(text)]
    refs.extend(match.lower() for match in COMMIT_REF_PATTERN.findall(text))

    deduped: list[str] = []
    for ref in refs:
        if ref not in deduped:
            deduped.append(ref)
    return deduped


def _scan_reference_mentions(markdown: str, context: ValidationContext) -> MentionScanResult:
    current_heading = ""
    covered_refs: set[str] = set()
    referenced_prs: set[int] = set()
    referenced_authors: set[str] = set()
    referenced_commits: set[str] = set()
    found_new_contributors: dict[str, int | None] = {}
    errors: list[str] = []
    bullet_count = 0

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("### "):
            current_heading = line
            continue

        if not line.startswith("- "):
            continue

        refs = _extract_explicit_references(line)
        is_change_bullet = current_heading in context.change_section_headings
        is_new_contributor_bullet = current_heading == NEW_CONTRIBUTORS_HEADING

        if is_change_bullet:
            bullet_count += 1
            if not refs:
                errors.append(f"Bullet missing explicit PR/commit references: {line}")
                continue

        if is_new_contributor_bullet:
            usernames = USER_HANDLE_PATTERN.findall(line)
            if len(usernames) != 1:
                errors.append(
                    "New contributor bullet must mention exactly one contributor handle: "
                    f"{line}"
                )
            else:
                username = usernames[0]
                expected_first_pr = context.expected_new_contributors.get(username)
                if username not in context.expected_new_contributors:
                    errors.append(f"Unknown new contributor @{username}: {line}")
                elif username in found_new_contributors:
                    errors.append(f"Duplicate new contributor @{username}: {line}")
                else:
                    found_new_contributors[username] = expected_first_pr
                    if expected_first_pr is not None and f"#{expected_first_pr}" not in refs:
                        errors.append(
                            f"New contributor @{username} must reference #{expected_first_pr}: {line}"
                        )

        for ref in refs:
            author = context.reference_authors.get(ref)
            if not author:
                errors.append(f"Bullet references unknown PR/commit {ref}: {line}")
                continue
            if f"@{author}" not in line:
                errors.append(f"Bullet mentioning {ref} is missing @{author}: {line}")
                continue

            covered_refs.add(ref)
            referenced_authors.add(author)
            if ref.startswith("#"):
                referenced_prs.add(int(ref[1:]))
            else:
                referenced_commits.add(ref)

        if is_new_contributor_bullet and not refs and context.expected_new_contributors:
            errors.append(f"New contributor bullet missing PR reference: {line}")

    return MentionScanResult(
        covered_refs=covered_refs,
        referenced_prs=referenced_prs,
        referenced_authors=referenced_authors,
        referenced_commits=referenced_commits,
        found_new_contributors=found_new_contributors,
        bullet_count=bullet_count,
        errors=errors,
    )


def missing_references(
    markdown: str,
    notes: ReleaseNotes,
    include_internal: bool = False,
) -> list[str]:
    """Return required refs that are not yet covered in the markdown."""
    context = build_validation_context(notes, include_internal=include_internal)
    scan = _scan_reference_mentions(markdown, context)
    return [ref for ref in context.reference_order if ref not in scan.covered_refs]


def _format_reference_token(ref: str) -> str:
    return ref if ref.startswith("#") else f"({ref})"


def append_reference_coverage_appendix(
    markdown: str,
    notes: ReleaseNotes,
    include_internal: bool = False,
) -> str:
    """Append a compact appendix covering any PRs/authors omitted by the agent."""
    context = build_validation_context(notes, include_internal=include_internal)
    scan = _scan_reference_mentions(markdown, context)
    missing_refs = [ref for ref in context.reference_order if ref not in scan.covered_refs]
    if not missing_refs:
        return markdown

    refs_by_author: dict[str, list[str]] = {}
    author_order: list[str] = []
    for ref in missing_refs:
        author = context.reference_authors[ref]
        if author not in refs_by_author:
            refs_by_author[author] = []
            author_order.append(author)
        refs_by_author[author].append(_format_reference_token(ref))

    appendix_lines = [COVERAGE_HEADING]
    for author in author_order:
        appendix_lines.append(f"- @{author}: {', '.join(refs_by_author[author])}")

    base_lines = markdown.rstrip().splitlines()
    for index, line in enumerate(base_lines):
        if line.startswith("**Full Changelog**:"):
            combined = base_lines[:index] + [""] + appendix_lines + [""] + base_lines[index:]
            return "\n".join(combined) + "\n"

    return "\n".join(base_lines + [""] + appendix_lines + [""])


def validate_release_notes_markdown(
    markdown: str,
    notes: ReleaseNotes,
    include_internal: bool = False,
) -> CoverageSummary:
    """Validate that every included change lists explicit refs and authors."""
    context = build_validation_context(notes, include_internal=include_internal)
    scan = _scan_reference_mentions(markdown, context)
    missing_refs = [ref for ref in context.reference_order if ref not in scan.covered_refs]
    missing_new_contributors = [
        username
        for username in context.expected_new_contributors
        if username not in scan.found_new_contributors
    ]

    errors = list(scan.errors)
    if missing_refs:
        errors.append(
            "Release notes are missing PR/commit coverage for: "
            + ", ".join(missing_refs)
        )
    if missing_new_contributors:
        errors.append(
            "Release notes are missing new contributor coverage for: "
            + ", ".join(f"@{username}" for username in missing_new_contributors)
        )

    if errors:
        raise ReleaseNotesValidationError("\n".join(errors))

    return CoverageSummary(
        bullet_count=scan.bullet_count,
        referenced_prs=sorted(scan.referenced_prs),
        referenced_authors=sorted(scan.referenced_authors),
        referenced_commits=sorted(scan.referenced_commits),
        required_reference_count=len(context.reference_order),
    )


def format_coverage_summary(summary: CoverageSummary) -> str:
    """Render a compact multi-line validation summary for logs and evidence."""
    prs = ", ".join(f"#{pr}" for pr in summary.referenced_prs) or "none"
    authors = ", ".join(f"@{author}" for author in summary.referenced_authors) or "none"
    commits = ", ".join(summary.referenced_commits) or "none"
    return "\n".join(
        [
            "Release notes attribution coverage validated.",
            f"- Change bullets checked: {summary.bullet_count}",
            f"- Covered references: {len(summary.referenced_prs) + len(summary.referenced_commits)}/{summary.required_reference_count}",
            f"- PRs referenced: {prs}",
            f"- Authors referenced: {authors}",
            f"- Standalone commits referenced: {commits}",
        ]
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Validate PR and author attribution in generated release notes."
    )
    parser.add_argument(
        "--markdown-file",
        default="release_notes.md",
        help="Path to the generated release notes markdown file.",
    )
    return parser.parse_args()


def main() -> None:
    """Validate generated release notes using the same GitHub metadata inputs."""
    args = parse_args()
    token = get_env("GITHUB_TOKEN", required=True)
    tag = get_env("TAG", required=True)
    previous_tag = get_env("PREVIOUS_TAG") or None
    include_internal = get_env("INCLUDE_INTERNAL", "false").lower() == "true"
    repo_name = get_env("REPO_NAME", required=True)

    notes = generate_release_notes(
        tag=tag,
        previous_tag=previous_tag,
        repo_name=repo_name,
        token=token,
        include_internal=include_internal,
    )

    with open(args.markdown_file) as file:
        markdown = file.read()

    summary = validate_release_notes_markdown(
        markdown,
        notes,
        include_internal=include_internal,
    )
    print(format_coverage_summary(summary))


if __name__ == "__main__":
    main()
