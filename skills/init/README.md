# init

Scaffold a concise, repo-specific `AGENTS.md` contributor guide for any
repository.

## Trigger

- `/init` — create `AGENTS.md` at the repository root
- `/init <path>` — create `AGENTS.md` scoped to a subdirectory

## What it does

1. Inspects the repo (structure, README, build files, CI configs)
2. Writes a 200–400 word `AGENTS.md` titled "Repository Guidelines"
3. Creates the file, asking before overwriting

## See also

For deeper onboarding workflows (readiness assessment, full OpenHands setup,
PR review automation), see the **onboarding** skill.
