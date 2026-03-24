# Agent Onboarding

Take an agent readiness report and turn its gaps into concrete, repo-appropriate fixes.

## Triggers

This skill is activated by the following keywords:

- `improve-agent-readiness`

## Prerequisites

An agent readiness report must already exist — either from running `agent-readiness-report` on the target repo or provided directly by the user. If no report exists, run the readiness report skill first.

## How It Works

1. **Read the report** — identify every missing (✗) feature across all five pillars
2. **Propose 5–10 high-impact fixes** — ranked by how directly each change helps an agent complete coding tasks, not by checklist coverage
3. **Implement on request** — apply approved fixes with atomic commits, then update the readiness report to reflect the new state

## Ranking Heuristic

Proposals are ranked by agent impact:

1. **Unblocking** — things that let agents work at all (AGENTS.md, build commands, bootstrap scripts)
2. **Fast feedback** — things that tell agents whether their changes are correct (pre-commit hooks, test documentation)
3. **Quality & process** — things that improve agent output quality (CI caching, label automation)
4. **Governance** — things that define boundaries (SECURITY.md, CODEOWNERS, CodeQL)

A single change that lets an agent build and test a project outranks a two-for-one that addresses minor gaps.

## Pillar-Specific Guidance

The skill includes targeted advice for each pillar:

- **Agent Instructions** — AGENTS.md, AI IDE config, contributing guides, `.env.example`
- **Feedback Loops** — pre-commit hooks, test run documentation, linter/formatter setup
- **Workflows & Automation** — PR templates, issue templates, CI concurrency control
- **Policy & Governance** — CODEOWNERS, security policy, agent-aware `.gitignore`
- **Build & Dev Environment** — dependency lockfiles, tool version pinning, single-command setup

## Implementation Rules

- Content is specific to the target repo — no boilerplate
- Matches existing style (tabs/spaces, doc format, naming conventions)
- One commit per logical fix
- Readiness report is updated after implementation

## References

- `references/criteria.md` — full 74-feature evaluation criteria with descriptions and evidence examples
