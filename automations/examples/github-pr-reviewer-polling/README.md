# GitHub PR reviewer polling example

This example shows the local cron polling pattern for a PR review automation.
It is intentionally a custom script instead of a prompt preset so the polling
run can exit without creating an OpenHands conversation when there is no work.

Runtime flow:

1. Load persisted state from `automation-state/github_pr_reviewer_{id}.json`.
2. Poll the GitHub REST API for open PRs updated since `last_poll`.
3. Filter out drafts, already-reviewed head SHAs, and PRs that do not match the
   optional label gate.
4. If no PRs remain, save state, fire the completion callback, and exit without
   creating a conversation.
5. For each actionable PR, create an OpenHands conversation with review context.

Customize the constants at the top of `main.py` before packaging:

- `REPO`
- `IGNORE_DRAFTS`
- `REQUIRED_LABELS`
- `MAX_CONVERSATIONS_PER_RUN`
- `DEFAULT_OPENHANDS_URL`

Required OpenHands secret:

- `GITHUB_TOKEN`

Optional OpenHands secret:

- `OPENHANDS_URL`
