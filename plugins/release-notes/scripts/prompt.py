"""Prompt template for the release notes agent."""

PROMPT = """Write official release notes for `{repo_name}` tag `{tag}`.

Use the structured release data below as your primary source of truth. You may inspect the checked-out repository if it helps you judge significance or match release-note style, but do not ask follow-up questions.

Your job is editorial, not mechanical:
- decide which PRs are important enough to mention
- group related PRs into a single bullet when they form one coherent feature or fix
- for larger releases, aggressively compress the notes into a shorter set of higher-signal bullets instead of listing one bullet per PR
- if a section would have more than 5 bullets, merge same-theme items until the section is scannable
- omit trivial, repetitive, or low-signal changes from the final notes
- prefer end-user impact over implementation detail
- prioritize public APIs, user-visible capabilities, security fixes, supported integrations/models, and operational changes users directly invoke
- treat toolkit-maintainer or contributor-facing changes as secondary unless they materially change how end users or client developers adopt, run, or integrate the project
- changes that mostly affect CI, internal prompts, benchmarks, workflow inputs, refactors, contributor ergonomics, or toolkit implementation details should stay in the small/internal appendix unless they are unusually significant
- use `### 📚 Documentation` only for notable docs/reference/policy updates that matter to users or client developers; public API additions still belong in `### ✨ New Features`
- omit prompt wording, benchmark plumbing, workflow maintenance, and similar maintainer-only changes unless they materially alter observable user behavior
- start with a short, conversational 1-2 sentence overview of the release before the categorized sections
- if you add top-level highlight bullets, keep them to at most 3 and reserve them for the biggest user-facing changes
- treat the suggested category as a hint, not a rule
- when `include_internal` is false, omit internal-only work unless it is important for users
- use imperative mood
- keep each bullet to one line
- every change bullet must end with explicit references for each included item
- format PR references as `(#123) @username`; if you group multiple PRs, include each reference explicitly, for example `(#123) @alice, (#124) @bob`
- if you mention a standalone commit instead of a PR, format it as `(abc1234) @username`
- include every new contributor listed below in the `### 👥 New Contributors` section
- for breaking changes, briefly note the migration path when the provided context makes it clear

Return markdown only. Do not wrap the result in a code fence.

Required structure:
- `## [{tag}] - {date}`
- a short conversational overview paragraph immediately after the title
- optional top-level highlight bullets (maximum 3) before the categorized sections
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
