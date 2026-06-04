# Polling GitHub PR Review Plugin

An OpenHands plugin that deploys a cron automation to poll a GitHub repository every 5 minutes for new labeled pull requests and automatically start a code review conversation for each one.

## Overview

This plugin is designed for teams that want automated code review on labeled pull requests without requiring a publicly reachable webhook endpoint. It works with local OpenHands deployments and cloud deployments alike.

When invoked, the plugin's SKILL walks you through three setup questions and then deploys a fully configured automation.

## How It Works

```
Every 5 minutes:
  1. Query GitHub API for open PRs with the configured label
     created since the previous run
  2. For each new matching PR:
     - Start an OpenHands conversation
     - Prompt the agent to load the code review skill
     - Agent reviews the PR and posts findings via GitHub API
  3. Update state (advance timestamp, record reviewed PR numbers)
```

### First Run Behavior

On the very first run the automation records the current timestamp as a baseline and exits without triggering any reviews. This prevents a flood of reviews for all open PRs that existed before the automation was created. Reviews begin on the second run (approximately 5 minutes later).

## Quick Start

Load this plugin in an OpenHands conversation. The SKILL will guide you through setup interactively:

1. **Repository to monitor** - which `owner/repo` to poll
2. **Label filter** - only PRs with this label are reviewed (e.g. `needs-review`)
3. **Code review skill URL** - the skill the agent uses to perform the review

Then the SKILL packages and deploys the automation automatically.

## Configuration

| Parameter | Description | Default |
|---|---|---|
| Repository | GitHub repository in `owner/repo` format | Required |
| Label | PR label that triggers a code review | Required |
| Code review skill | URL to the skill used for code review | `https://github.com/OpenHands/extensions/tree/main/skills/code-review` |

## Required Secret

Set `GITHUB_PERSONAL_ACCESS_TOKEN` in **OpenHands Settings -> Secrets** before deploying:

| Token type | Required scope |
|---|---|
| Classic PAT | `repo` (private repos) or `public_repo` (public repos) |
| Fine-grained PAT | Pull requests: Read and Write |

## Automation Details

| Property | Value |
|---|---|
| Trigger | Cron, every 5 minutes (`*/5 * * * *`) |
| Entrypoint | `python3 main.py` |
| Timeout | 270 seconds |
| State file | `{WORKSPACE_BASE}/automation-state/github_pr_poller_{id}.json` |

## State File

The automation persists state to a JSON file between runs:

```json
{
  "last_run_ts": "2025-06-01T12:00:00Z",
  "reviewed_prs": [101, 102, 105]
}
```

- `last_run_ts` - ISO 8601 timestamp of the last successful run; used to filter new PRs
- `reviewed_prs` - list of PR numbers already reviewed; prevents duplicate reviews if a PR is still open on subsequent polls

To reset the automation (e.g. after changing the label), delete the state file. The next run will re-record the baseline timestamp.

## Script Template

The automation script (`scripts/main.py`) has three configuration constants near the top that the SKILL fills in at deployment time:

```python
REPO = "owner/repo"
LABEL = "needs-review"
CODE_REVIEW_SKILL = "https://github.com/OpenHands/extensions/tree/main/skills/code-review"
```

## Troubleshooting

**No reviews triggered after 10+ minutes**
- Verify `GITHUB_PERSONAL_ACCESS_TOKEN` is set and valid
- Check that new PRs are being opened *after* the baseline timestamp (delete the state file and restart if needed)

**PRs found but no conversations created**
- Check the automation run logs in the OpenHands UI for error details
- Ensure the agent server URL is reachable from the automation sandbox

**Wrong PRs being reviewed**
- Confirm the label name exactly matches what's applied to the PRs (case-sensitive)
- Delete the state file and re-deploy with the corrected label

## License

MIT - See repository root for full license text.
