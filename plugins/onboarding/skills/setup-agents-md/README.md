# Generate AGENTS.md

Generate a high-quality, repo-specific AGENTS.md file that tells AI agents how to work effectively in a repository.

## Triggers

This skill is activated by the following keywords:

- `/agents-md`

## What This Does

Reads the actual repository — Makefiles, CI configs, package.json scripts, linter configs, directory structure — and produces an AGENTS.md with real commands, real paths, and real conventions. Never generates generic boilerplate.

## Why AGENTS.md Matters

An AGENTS.md is the single highest-impact addition for agent readiness. Without it, agents guess at build commands, miss project conventions, run the wrong test suite, and don't know what's dangerous.

## Generated Sections

All sections are optional — only what's relevant to the repo is included:

| Section | Contents |
|---------|----------|
| **Project overview** | What the project is, language/framework, high-level architecture |
| **Commands** | Build, test, lint, and format commands copied from the repo's actual configs |
| **Project structure** | What's in each top-level directory |
| **Coding standards** | Conventions not captured by linter config |
| **Testing** | Where tests live, how to run them, any setup needed |
| **Guardrails** | Things the agent must NOT do — destructive commands, protected files |

## Key Principles

- **Be specific, not generic** — `uv run ruff check --fix <file>`, not "run the linter"
- **Commands are king** — every command block is copy-pasteable
- **Link, don't repeat** — reference existing docs rather than duplicating them
- **Include dangerous operations** — agents are literal and need explicit guardrails
- **Keep it maintainable** — a short, accurate file beats a long one that drifts

## Monorepo Support

For monorepos, the root AGENTS.md covers repo-wide commands and conventions. Per-package files are created only when a package has substantially different commands or conventions.

## Real-World Examples

The skill references patterns from studied AGENTS.md files:

- **CopilotKit** (32 lines) — concise essentials with links to detailed docs
- **airflow** (215 lines) — thorough command reference with real placeholders
- **grafana** (480 lines) — categorized frontend/backend commands with sub-directory links
- **swc** (75 lines) — performance-first philosophy anchoring every decision
- **Lychee** (122 lines) — safety-critical guardrails with explicit "never run" section
