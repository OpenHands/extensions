# iterate

Iterate on a GitHub pull request — drive it through CI, code review, and QA
until it is merge-ready. The agent monitors PR state, diagnoses and fixes
problems, retries flaky failures, and keeps looping until the PR is green
or a blocker requires human help.

## Trigger

`/iterate`

## How it works

1. **Snapshot** PR state using a watcher script (`scripts/gh_pr_watch.py`).
2. **Evaluate** the recommended actions: fix CI failures, address review
   feedback, retry flaky checks, or wait.
3. **Fix and push** — then loop back to step 1.
4. **Stop** when the PR is merge-ready, closed, or blocked.

## Requirements

- GitHub CLI (`gh`) — authenticated with repo access
- A GitHub PR (or a branch to create one from)
