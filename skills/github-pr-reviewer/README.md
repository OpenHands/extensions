# GitHub PR Reviewer

Create an automation that reviews GitHub pull requests when a configurable
trigger label is applied.

## Trigger

This skill is activated by:

- `/pr-reviewer:setup`

## Features

- Reviews PRs on demand by watching for a GitHub label event
- Processes each label application exactly once, with persistent state
- Re-review support by removing and re-applying the label
- Suppresses stale reviews when the PR head commit changes mid-review
- Uses a real cloned checkout and full PR context instead of only a truncated diff
- Posts acknowledgement and final review comments with AI disclosure
- Configurable review tone and polling schedule
- Uses reusable helper scripts for packaging and automation creation
- Keeps generated build files in the system temporary directory instead of the repository

## Prerequisites

Set `GITHUB_PERSONAL_ACCESS_TOKEN` in OpenHands Settings -> Secrets. The token
must be able to read the repository, read pull requests, read issue events, and
write issue comments.

## Quick Start

Ask OpenHands:

> "Set up a PR review automation for my `myorg/backend` repo using the
> `openhands-review` label and concise reviews."

After setup, apply the configured label to a pull request to queue a review. To
request another review later, remove and re-apply the label.

## Helper Scripts

- `scripts/main.py` - automation script template to customize before upload
- `scripts/package_upload.py` - packages and uploads a prepared build directory
- `scripts/create_automation.py` - creates the cron automation from the uploaded tarball

## See Also

- [SKILL.md](SKILL.md) - Full setup workflow reference
