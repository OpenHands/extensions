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
- The watcher can surface review comments from approved review bots by matching keywords in the bot login.
  - Defaults include: `openhands`, `openhands-agent`, `all_hands_bot`, `smolpaws`, `claude`.
  - Optional: set `BABYSIT_PR_REVIEW_BOT_KEYWORDS` (comma-separated) to allow additional bot keywords.
