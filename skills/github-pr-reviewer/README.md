# GitHub PR Reviewer

Create an automation that reviews GitHub pull requests when a configurable
trigger label is applied.

## Trigger

This skill is activated by:

- `/pr-reviewer:setup`

## Features

- Reviews PRs on demand by watching for a GitHub label event
- Watches several repositories from a single automation, each with its own state
- Processes each label application exactly once, with persistent state
- Re-review support by removing and re-applying the label
- Suppresses stale reviews when the PR head commit changes mid-review
- Hands the agent the reviewed commit already checked out, and removes that
  checkout when the review ends, so nothing accumulates between runs
- Publishes a real pull request review, with inline comments where a finding
  maps to a changed line, and verifies on GitHub that it landed
- Posts acknowledgement comments with AI disclosure
- Configurable review tone and polling schedule

## Prerequisites

Set `GITHUB_PERSONAL_ACCESS_TOKEN` in OpenHands Settings -> Secrets. The token
must be able to read the repositories and their contents, read issue events,
write issue comments, and **write pull request reviews** — the review is
published through the pull request reviews API, so read-only pull request access
is not enough.

## Quick Start

Ask OpenHands:

> "Set up a PR review automation for my `myorg/backend` and `myorg/frontend`
> repos using the `openhands-review` label and concise reviews."

After setup, apply the configured label to a pull request to queue a review. To
request another review later, remove and re-apply the label.

## See Also

- [SKILL.md](SKILL.md) - Full setup workflow reference
