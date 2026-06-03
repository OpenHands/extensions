# Generate AGENTS.md

Generate a high-quality, repo-specific AGENTS.md file that tells AI agents how to work effectively in a repository.

## Triggers

This skill is activated by the following keywords:

- `setup-agents-md`

## What This Does

Reads the actual repository — Makefiles, CI configs, package.json scripts, linter configs, directory structure — and produces an AGENTS.md with real commands, real paths, and real conventions. Never generates generic boilerplate.

Sections are included only when relevant: project overview, build/test/lint commands, project structure, coding standards, testing setup, and guardrails for things the agent must not do.
