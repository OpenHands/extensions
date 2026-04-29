---
name: setup-agents-md
description: Generate a high-quality, repo-specific AGENTS.md file that tells AI agents how to work effectively in a repository. Reads the actual repo to extract commands, structure, conventions, and guardrails — never generates generic boilerplate. Use when a user wants to create or improve their AGENTS.md, or after a readiness report identifies a missing agent instruction file.
triggers:
- setup-agents-md
- agents-md
---

# Generate AGENTS.md

Create a repo-specific AGENTS.md that gives AI agents the context they need to
work effectively.  Every section should reference real commands, real paths, and
real conventions from the repository — not generic advice.

## Why this matters

An AGENTS.md is the single highest-impact addition for agent readiness.  It
directly addresses features across multiple pillars:

- **Agent Instructions**: agent instruction file, README with build/run/test,
  contributing guide, environment variable documentation
- **Feedback Loops**: test run documentation — agents need exact commands
- **Policy & Governance**: guardrails the agent must follow

Without it, agents guess at build commands, miss project conventions, run the
wrong test suite, and don't know what's dangerous.  The best AGENTS.md files
share the same core pattern: real commands, clear structure, explicit boundaries.

## How to run

### Step 0: Check for an existing AGENTS.md

Look for an existing `AGENTS.md` (or `.agents/AGENTS.md`) in the repo root.
If one exists, **do not rewrite it from scratch**. Instead, read the repo
(Step 1), compare what you find against what's already documented, and suggest
specific additions or changes. Present the suggestions to the user and let them
decide what to incorporate.

If no file exists, proceed to create one.

### Step 1: Read the repo

Before writing anything, gather the actual information.  Check these sources:

**Commands** (most important — agents need to know how to build, test, lint):
- `Makefile` / `justfile` / `Taskfile.yml` — look for build/test/lint/format targets
- `package.json` `scripts` — npm/yarn/pnpm run targets
- `pyproject.toml` `[tool.prek]` / `[tool.pytest]` — Python tooling config
- `.github/workflows/*.yml` — CI steps reveal the real commands
- `Cargo.toml` — Rust build/test commands
- `build.gradle` / `pom.xml` — Java/Kotlin build commands
- `Rakefile` — Ruby task definitions
- `docker-compose.yml` — service orchestration commands

**Project structure**:
- Top-level directory listing — what's in each major directory
- Monorepo indicators: workspace configs, multiple package.json/Cargo.toml/pyproject.toml
- Source vs test layout (where does code live, where do tests live)

**Conventions**:
- Existing linter/formatter configs (.eslintrc, .prettierrc, rustfmt.toml, .rubocop.yml, ruff.toml)
- CONTRIBUTING.md — often contains coding standards
- Existing README — architecture descriptions, setup instructions
- `.editorconfig` — indentation/style basics

**Guardrails**:
- Database configs — identify destructive commands to warn about
- CI enforcement — what must pass before merge
- Secrets/env patterns — `.env.example`, vault configs
- Branch protection or merge requirements

### Step 2: Write the AGENTS.md

Use this structure.  Every section is optional — include only what's relevant to
this repo.  A 30-line file with real commands beats a 200-line file with generic
advice.

```markdown
# AGENTS.md

## Project overview

One or two sentences: what this project is, what language/framework, and the
high-level architecture (monorepo? client-server? library?).

## Commands

Organized by category.  Use the exact commands from the repo — copy from
Makefile/CI/package.json, don't invent them.

### Build
### Test
### Lint & format

## Project structure

What's in each top-level directory.  Focus on what an agent needs to navigate
the codebase — not an exhaustive tree.

## Coding standards

Language-specific conventions that aren't captured by linter config.  Things
like: naming patterns, import ordering preferences, test file location
conventions, preferred patterns over anti-patterns.

## Testing

Where tests live, how they're organized, how to run a single test vs the full
suite, any test database setup needed.

## Guardrails

Things the agent must NOT do.  Destructive commands, files that shouldn't be
edited by hand, operations that require human approval.
```

### Key principles

**Be specific, not generic.**  Don't write "run the linter before committing" —
write `uv run ruff check --fix <file>`.  Don't write "follow the project's
coding standards" — write "use `snake_case` for variables, no `assert` in
production code."

**Commands are king.**  If the agent only reads one section, it should be
Commands.  Every command block should be copy-pasteable.

**Link, don't repeat.**  If there's a detailed CONTRIBUTING.md or architecture
doc, link to it rather than duplicating the content.  The AGENTS.md is an index
and quick reference, not a manual.

**Include dangerous operations.**  If `make db-reset` destroys the dev database,
say so.  If `git push -f` to main is forbidden, say so.  Agents are literal —
they need explicit guardrails.

**Keep it maintainable.**  A short, accurate AGENTS.md is better than a long one
that drifts out of date.  Reference CI configs and Makefiles by path so a human
(or agent) can update the AGENTS.md when the underlying commands change.

### What to leave out

- Generic software engineering advice ("write clean code", "use meaningful names")
- Process documentation that belongs in CONTRIBUTING.md
- Full API documentation that belongs in doc comments or a docs site
- Operational runbooks that belong in an ops directory

### Monorepo considerations

If the repo is a monorepo, the root AGENTS.md should cover repo-wide commands
and conventions.  Consider sub-directory AGENTS.md files only for packages with
substantially different commands or conventions, and link to them from the root.
