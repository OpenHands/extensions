"""Prompt template for the release notes agent."""

PROMPT = """Write official release notes for `{repo_name}` tag `{tag}`.

Use the structured release data below as your primary source of truth. You may inspect the checked-out repository if it helps you judge significance or match release-note style, but do not ask follow-up questions.

Your job is editorial, not mechanical:
- decide which PRs are important enough to mention
- group related PRs into a single bullet when they form one coherent feature or fix
- omit trivial, repetitive, or low-signal changes from the final notes
- prefer user impact over implementation detail
- treat the suggested category as a hint, not a rule
- when `include_internal` is false, omit internal-only work unless it is important for users
- use imperative mood
- keep each bullet to one line
- format bullet references as `(#123) @username`; if you group multiple PRs, include each reference explicitly, for example `(#123) @alice, (#124) @bob`
- include every new contributor listed below in the `### 👥 New Contributors` section
- for breaking changes, briefly note the migration path when the provided context makes it clear

Return markdown only. Do not wrap the result in a code fence.

Required structure:
- `## [{tag}] - {date}`
- `### ⚠️ Breaking Changes` when applicable
- `### ✨ New Features` when applicable
- `### 🐛 Bug Fixes` when applicable
- `### 📚 Documentation` only when notable
- `### 🏗️ Internal/Infrastructure` only when `include_internal` is true and the changes are worth mentioning
- `### 👥 New Contributors` when there are any
- `**Full Changelog**: {full_changelog_url}` at the end

Release metadata:
- Repository: {repo_name}
- Current tag: {tag}
- Previous tag: {previous_tag}
- Release date: {date}
- Commits in range: {commit_count}
- Include internal section: {include_internal}
- Output format: {output_format}

Candidate changes:
{change_candidates}

New contributors:
{new_contributors}

Full changelog URL:
{full_changelog_url}
"""


def format_prompt(
    *,
    repo_name: str,
    tag: str,
    previous_tag: str,
    date: str,
    commit_count: int,
    include_internal: bool,
    output_format: str,
    full_changelog_url: str,
    change_candidates: str,
    new_contributors: str,
) -> str:
    """Format the release-notes prompt."""
    return PROMPT.format(
        repo_name=repo_name,
        tag=tag,
        previous_tag=previous_tag,
        date=date,
        commit_count=commit_count,
        include_internal=str(include_internal).lower(),
        output_format=output_format,
        full_changelog_url=full_changelog_url,
        change_candidates=change_candidates,
        new_contributors=new_contributors,
    )
