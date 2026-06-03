# Improve Agent Readiness

Take an agent readiness report and turn its gaps into concrete, repo-appropriate fixes.

## Triggers

This skill is activated by the following keywords:

- `improve-agent-readiness`

## Prerequisites

An agent readiness report must already exist — either from running `agent-readiness-report` on the target repo or provided directly by the user. If no report exists, run the readiness report skill first.

## What This Does

1. **Reads the report** — identifies every missing feature across all five pillars
2. **Proposes 5–10 high-impact fixes** — ranked by how directly each change helps an agent complete coding tasks, not by checklist coverage
3. **Implements on request** — applies approved fixes with atomic commits, then updates the readiness report to reflect the new state
