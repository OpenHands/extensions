# verify

Orchestrate repo-level verification of a GitHub PR by polling CI checks,
PR review, and QA workflows using `gh` CLI — then driving the
fix → push → re-verify loop until everything passes.

## Triggers

This skill is activated by:

- `/verify`
- the agent may activate it when it needs to "verify a PR", "check if CI/review/QA passed", or "push and verify"

## How It Works

1. You push changes to a PR branch.
2. You poll GitHub for three verification signals using `gh` commands:
   - **CI checks** — `gh pr checks` (pass/fail/pending)
   - **PR review** — `gh pr view --json reviews` (APPROVED / CHANGES_REQUESTED / COMMENTED)
   - **QA report** — `gh api .../issues/{number}/comments` (PASS / FAIL / PARTIAL)
3. You decide what to do: fix code, retry flaky CI, wait, or celebrate.
4. If a fix is needed, you commit, push, and re-poll.

No custom scripts or Python dependencies — just `gh` and `git`.

## Requirements

- GitHub CLI (`gh`) — authenticated with repo access
- A GitHub PR to verify

## Relationship to babysit-pr

- **babysit-pr** is a passive monitor — watches an existing PR via a Python script and surfaces issues.
- **verify** is an active orchestrator — the agent itself drives the push → verify → fix → repeat cycle using only `gh` commands, with awareness of CI, review, and QA layers.
