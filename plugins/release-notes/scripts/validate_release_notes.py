#!/usr/bin/env python3
"""Validate attribution coverage in generated release notes."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass

from generate_release_notes import CATEGORIES, ReleaseNotes, generate_release_notes, get_env

PR_REF_PATTERN = re.compile(r"#(\d+)\b")
COMMIT_REF_PATTERN = re.compile(r"\(([0-9a-f]{7,40})\)")
NEW_CONTRIBUTORS_HEADING = "### 👥 New Contributors"


@dataclass
class CoverageSummary:
    """Summary of attribution coverage found in release notes."""

    bullet_count: int
    referenced_prs: list[int]
    referenced_authors: list[str]
    referenced_commits: list[str]


@dataclass
class ValidationContext:
    """Parsed validation context for a single release note run."""

    reference_authors: dict[str, str]
    change_section_headings: set[str]


class ReleaseNotesValidationError(ValueError):
    """Raised when generated release notes violate attribution rules."""


def build_validation_context(
    notes: ReleaseNotes, include_internal: bool = False
) -> ValidationContext:
    """Build the reference and section metadata used for validation."""
    del include_internal  # Validation should cover every candidate the agent may cite.

    reference_authors: dict[str, str] = {}
    change_section_headings = {
        f"### {CATEGORIES[category]['emoji']} {CATEGORIES[category]['title']}"
        for category in CATEGORIES
    }

    for category in list(CATEGORIES) + ["other"]:
        for change in notes.changes.get(category, []):
            if change.pr_number:
                reference_authors[f"#{change.pr_number}"] = change.author
            else:
                reference_authors[change.sha[:7].lower()] = change.author

    return ValidationContext(
        reference_authors=reference_authors,
        change_section_headings=change_section_headings,
    )


def _extract_bullet_references(
    bullet: str, reference_authors: dict[str, str]
) -> list[str]:
    refs = [f"#{match}" for match in PR_REF_PATTERN.findall(bullet)]

    for match in COMMIT_REF_PATTERN.findall(bullet):
        ref = match.lower()
        if ref in reference_authors and ref not in refs:
            refs.append(ref)

    return refs


def validate_release_notes_markdown(
    markdown: str,
    notes: ReleaseNotes,
    include_internal: bool = False,
) -> CoverageSummary:
    """Validate that every included change lists explicit refs and authors."""
    context = build_validation_context(notes, include_internal=include_internal)
    errors: list[str] = []
    current_heading = ""
    bullet_count = 0
    referenced_prs: set[int] = set()
    referenced_authors: set[str] = set()
    referenced_commits: set[str] = set()

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("### "):
            current_heading = line
            continue

        if not line.startswith("- "):
            continue

        if current_heading == NEW_CONTRIBUTORS_HEADING:
            continue

        if current_heading not in context.change_section_headings:
            continue

        bullet_count += 1
        refs = _extract_bullet_references(line, context.reference_authors)
        if not refs:
            errors.append(f"Bullet missing explicit PR/commit references: {line}")
            continue

        unknown_refs = [ref for ref in refs if ref not in context.reference_authors]
        if unknown_refs:
            errors.append(
                f"Bullet references unknown PR/commit {', '.join(sorted(unknown_refs))}: {line}"
            )
            continue

        for ref in refs:
            author = context.reference_authors.get(ref, "")
            if author and f"@{author}" not in line:
                errors.append(f"Bullet mentioning {ref} is missing @{author}: {line}")
                continue

            if ref.startswith("#"):
                referenced_prs.add(int(ref[1:]))
            else:
                referenced_commits.add(ref)

            if author:
                referenced_authors.add(author)

    if errors:
        raise ReleaseNotesValidationError("\n".join(errors))

    return CoverageSummary(
        bullet_count=bullet_count,
        referenced_prs=sorted(referenced_prs),
        referenced_authors=sorted(referenced_authors),
        referenced_commits=sorted(referenced_commits),
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
