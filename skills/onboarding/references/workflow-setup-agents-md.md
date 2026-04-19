# Deep AGENTS.md — `setup-agents-md`

Generate a thorough, high-quality AGENTS.md by extracting real commands,
structure, conventions, and guardrails from the repository.

## Why this matters

An AGENTS.md is the single highest-impact addition for agent readiness. Without
it, agents guess at build commands, miss project conventions, run the wrong test
suite, and don't know what's dangerous.

## Step 0: Check for an existing AGENTS.md

Look for an existing `AGENTS.md` (or `.agents/AGENTS.md`) in the repo root.
If one exists, **do not rewrite it from scratch**. Instead, read the repo,
compare what you find against what's already documented, and suggest specific
additions or changes. Present the suggestions to the user and let them decide.

## Step 1: Read the repo

Before writing anything, gather the actual information:

**Commands** (most important — agents need to know how to build, test, lint):
- `Makefile` / `justfile` / `Taskfile.yml` — build/test/lint/format targets
- `package.json` `scripts` — npm/yarn/pnpm run targets
- `pyproject.toml` — Python tooling config
- `.github/workflows/*.yml` — CI steps reveal the real commands
- `Cargo.toml`, `build.gradle` / `pom.xml`, `Rakefile`, `docker-compose.yml`

**Project structure**: top-level directory listing, monorepo indicators, source vs test layout.

**Conventions**: linter/formatter configs, CONTRIBUTING.md, existing README, `.editorconfig`.

**Guardrails**: database configs (destructive commands), CI enforcement, secrets/env patterns, branch protection.

## Step 2: Write the AGENTS.md

Use this structure (include only what's relevant):

```markdown
# AGENTS.md

## Project overview
One or two sentences: what this project is, language/framework, high-level architecture.

## Commands
### Build
### Test
### Lint & format

## Project structure
What's in each top-level directory.

## Coding standards
Language-specific conventions not captured by linter config.

## Testing
Where tests live, how to run single test vs full suite, test DB setup.

## Guardrails
Things the agent must NOT do. Destructive commands, files not to edit by hand.
```

## Key principles

- **Be specific, not generic.** Write `uv run ruff check --fix <file>`, not "run the linter."
- **Commands are king.** Every command block should be copy-pasteable.
- **Link, don't repeat.** Reference CONTRIBUTING.md or architecture docs by path.
- **Include dangerous operations.** If `make db-reset` destroys the dev database, say so.
- **Keep it maintainable.** Short and accurate beats long and generic.
