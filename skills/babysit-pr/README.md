# babysit-pr

Babysit a GitHub pull request by monitoring CI checks/workflow runs, review comments, and mergeability until the PR is ready to merge (or merged/closed).

## Triggers

This skill is activated by:

- `/babysit-pr`
- `/babysit`
- keywords like “babysit PR”, “watch PR”, “monitor CI”, or “check GitHub Actions”

## Details

- Requires the GitHub CLI (`gh`) to be available and authenticated.
- Uses `scripts/gh_pr_watch.py` to emit one-shot snapshots (`--once`) or a continuous JSONL stream (`--watch`).
- Optional: set `BABYSIT_PR_REVIEW_BOT_KEYWORDS` (comma-separated) to allow surfacing review comments from additional bot accounts.
