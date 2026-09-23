# GitHub PR Reviewer

Create an automation that reviews GitHub pull requests when a configurable
reviewer is requested or a trigger label is applied.

## Trigger

This skill is activated by:

- `/pr-reviewer:setup`

## Features

- Reviews PRs on demand from a GitHub reviewer request or label event
- Gates each review on the current head's check runs and Actions workflow runs
  before starting an agent: a completed `failure`, `cancelled`, or `timed_out`
  check blocks the review, and a `queued` or `in_progress` check exits with a
  clear waiting-on-checks outcome instead of holding a slot. Workflow runs are
  read too, so a workflow that fails before creating any check run still blocks
- Ignores checks and workflow runs recorded for an obsolete head, so a stale
  failure cannot block the push that fixed it
- Resumes an outstanding reviewer request on the next scheduled scan once the
  requested head's checks are green, so a request that arrives during CI is not
  lost; the explicit-request event path is kept for event-only deployments
- Names the retry the deployment actually has in the waiting comment: a
  scheduled scan where a cron trigger exists, and removing and re-requesting the
  bot where only the event trigger does
- Rewrites its own managed gate comment in place when the retry wording changes,
  so switching a deployment from the event trigger to a cron scan updates the
  outstanding-request explanation instead of leaving the old instruction
- Watches several repositories from a single automation, each with its own state
- Bounds a scheduled scan to a small, configurable number of new review
  conversations across all repositories (default 2), draining the oldest
  outstanding reviewer requests first and reaching the rest on later scans
- Processes each review request or label application idempotently
- Supports re-review by requesting the bot again or re-applying the label. Each
  explicit request refreshes mutable GitHub state (head, PR body, reviews,
  comments, review requests, linked issues, and current-head checks) instead of
  trusting what an earlier turn observed, so a same-head re-review sees a linked
  issue that has since gained or lost readiness, or a check that has since moved.
  Repository analysis already done, such as reading `AGENTS.md`, is retained
- Suppresses stale reviews when the PR head commit changes mid-review
- Hands the agent the reviewed commit already checked out, and removes that
  checkout when the review ends, so nothing accumulates between runs
- Publishes a real pull request review, with inline comments where a finding
  maps to a changed line, and verifies on GitHub that it landed
- Posts acknowledgement comments with AI disclosure
- Configurable review tone and polling schedule
- Optional human handoff after an exact-head approval. The scanner ranks the
  configured maintainers by recent commits to changed paths, then by their open
  GitHub review-request count, and requests one without merging the PR. Use at
  least two repository collaborators so a maintainer can author a PR without
  leaving the handoff roster empty.

## Prerequisites

Set `GITHUB_PERSONAL_ACCESS_TOKEN` in OpenHands Settings -> Secrets. The token
must be able to read the repositories and their contents, read issue events,
write issue comments, and **write pull request reviews** — the review is
published and the optional human reviewer is requested through the pull request
API, so read-only pull request access is not enough.

## Quick Start

Ask OpenHands for either trigger mode:

> "Set up a PR review automation for my `myorg/backend` and `myorg/frontend`
> repos when `all-hands-bot` is requested, using concise reviews."

After setup, request the configured bot on a pull request to queue a review. To
request another review later, request the bot again. Scheduled installations
can instead use a configured label and re-apply it for another review.

## See Also

- [SKILL.md](SKILL.md) - Full setup workflow reference
