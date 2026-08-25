# Code Review Calibration

Generate a code review skill that is calibrated to one specific repository, by investigating that repository's own history and conventions.

## What It Does

Most review guidance is generic, so the author has already heard it. This skill investigates a repo in two halves and writes what it learns to `.agents/skills/code-review.md`:

- **How the codebase breaks** - fix-density hotspots, reverts, fix-inducing commits (SZZ), and temporal coupling between files.
- **How the codebase works** - house conventions and idioms, testing strategy and regression-test discipline, what CI already enforces, and ownership/blast-radius signals.

The result is a reviewer that can say "use `scopedQuery()`, the same omission caused `9f2a1bc`" instead of "consider filtering by tenant."

## When to Use

- "Write a code review skill for this repo"
- "Recalibrate the reviewer to our codebase"
- "Where do bugs cluster here?"
- "What are our testing conventions?"
- The current review skill is producing generic feedback
- Onboarding to an unfamiliar codebase and needing to know its idioms and dangerous areas

## Requirements

- A git repository with real history. Very young or fully squash-merged repos yield weak patterns, and the skill is instructed to say so rather than pad the output.
- Optional: GitHub CLI (`gh`), authenticated. Enables the PR review-comment phase, which shows what the team already knows is easy to get wrong.

## Output

Writes or updates `.agents/skills/code-review.md`. Generated sections are wrapped in `<!-- BEGIN GENERATED -->` / `<!-- END GENERATED -->` markers so later runs can refresh the evidence without discarding hand-written content.

Ground rules the generated file must satisfy:

- Every failure pattern cites two or more commit SHAs. Uncitable observations are nits and get dropped.
- Six to twelve patterns. Beyond roughly fifteen the review loses focus.
- Patterns that a design change made impossible move to a Retired section rather than being deleted.

## Related Skills

- `code-review` - perform a code review
- `learn-from-code-review` - distill PR review feedback into guidelines
- `agent-memory` - persist repository knowledge in AGENTS.md
