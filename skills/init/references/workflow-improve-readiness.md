# Improve Agent Readiness — `improve-agent-readiness`

Take a readiness report and turn its gaps into concrete, repo-appropriate fixes.

## Prerequisites

This expects an agent readiness report to already exist — either from running
`agent-readiness-report` or provided by the user.

## Step 1: Read the report

Identify every **✗** (missing) feature across all five pillars.

## Step 2: Propose high-impact fixes

Pick the **5–10 changes that would help agents the most**, ranked by impact:

1. Things that unblock agents from working at all (AGENTS.md, build commands,
   bootstrap scripts, dev environment setup)
2. Things that give agents faster feedback (pre-commit hooks, test docs, PR templates)
3. Things that improve quality or process (CI caching, label automation)
4. Things that improve governance or compliance (SECURITY.md, CODEOWNERS)

Proposals should fit the specific repo — look at languages, frameworks, tools,
and existing conventions.

## Step 3: Implement on request

When the user approves fixes, implement them, then update the readiness report
to reflect the new state. Follow these rules:

- **Don't generate boilerplate** — content should be specific to this repo
- **Match existing style** — if the repo uses tabs, use tabs
- **Don't over-generate** — concise and accurate beats long and generic
- **Commit atomically** — one commit per logical fix
