# GitHub PR Reviewer

Create an automation that reviews GitHub pull requests when a configurable
reviewer is requested or a trigger label is applied.

## Trigger

This skill is activated by:

- `/pr-reviewer:setup`

## Features

- Reviews PRs on demand from a GitHub reviewer request or label event
- Gates each scheduled review on the current head's GitHub-required checks
  before starting an agent, read through the `isRequired` signal, so an optional
  workflow that fails cannot block a mergeable head: a completed `failure`,
  `cancelled`, or `timed_out` required check blocks the review, and a `queued`,
  `in_progress`, or not-yet-reported required check exits with a clear
  waiting-on-checks outcome instead of holding a slot. If the required-check
  signal is unavailable the gate falls back to every current-head check run and
  workflow run, including a workflow that fails before creating any check run
- Dispatches an explicit `all-hands-bot` review request even when required CI is
  red or pending; the CI gate applies to scheduled discovery
- Ignores checks and workflow runs recorded for an obsolete head, so a stale
  failure cannot block the push that fixed it
- Explicit reviewer requests include draft PRs in both event mode and scheduled
  scans; drafts without a request or trigger label remain excluded
- Resumes an outstanding reviewer request on the next scheduled scan once the
  requested head's checks are green, so a request that arrives during CI is not
  lost; the explicit-request event path is kept for event-only deployments
- Reviews open, non-draft PRs that nobody requested on a scheduled scan once
  their current head is green and carries no review yet, keyed by
  repository/PR/head so a repeat scan never duplicates a conversation or review
  and a changed head becomes eligible again
- Examines the whole unrequested backlog on each scheduled scan, while the
  global `max_new_per_run` quota limits only newly created review conversations;
  blocked or pending heads consume no launch slot
- Posts no managed gate comment for an unrequested PR that is merely red or
  pending - the comment answers an explicit request, so a scan over a large
  backlog cannot storm the PRs with comments
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
- Requires live evidence from the real app before approving a user-visible UI
  change when the repository's guidance demands it: unit tests, CSS-token
  assertions, generated mockups, and reconstructed captures cannot substitute.
  Missing evidence yields a COMMENT review that names the gap, so no approval
  and no maintainer handoff
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

## Opt-in worker-owned structured publication

`structured_publication: true` replaces direct agent publication in `worker.py`
with a JSON final-response artifact. The worker validates `head_sha`,
`code_assessment` (`clean`, `material_findings`, `inconclusive`),
`merge_readiness` (`ready`, `blocked`, `unknown`), summary, findings, and evidence.
It derives the event and footer. Only clean, ready artifacts approve;
self-authored clean reviews use COMMENT. Clean-but-blocked is not a code defect.
Findings currently appear in the body, not inline threads. Legacy is the default.

Deployment prerequisites (not automatically provisioned):

- Include `publication.py` in the bundle and run a periodic scan alongside event
  intake. Both paths reconcile finished conversations before selecting new work.
- Set `REVIEW_COORDINATION_AUTOMATION_ID` to one common namespace for both
  automations, `REVIEW_COORDINATION_API_KEY` to a user-authorized automation API
  key, and `AUTOMATION_API_URL`. The API must support `automation_id` user auth,
  metadata versions, create-if-absent, and conditional version writes. A run's
  automation-scoped KV JWT is **not** sufficient. Unsupported APIs fail closed.
- Configure `review_read_token_secret` and `review_profile_read_only: true` only
  after independently verifying profile/sandbox isolation. The flag is an
  operator assertion, **not enforced credential isolation**. Agents must have
  only read-only GitHub access, no publisher/coordination credentials and no
  write-capable MCP tools. Do not put the coordination key in the agent profile.
- Verify the deployed Agent Server supports conversation execution status and
  `/api/conversations/{id}/agent_final_response` returning `response`. Only
  `finished` results are consumed; there is no workspace-file transport.
- Enable `scan_window: true` for the VM's rotating ten-unrequested-PR discovery
  window. Explicit candidates bypass it. Linked low-priority closing issues
  suppress automatic maintainer handoff.

Leases protect the common repository/PR/reviewer subject. Head, latest request
and label events, and latest non-bot clarification identify generations across
triggers. Intent precedes POST. Lost responses or receipt writes are reconciled
by exact marker, account and head; an empty read never causes reposting.
Completed and rejected generations are retained. Missing/error starts are
quarantined; invalid/stale artifacts are retired until new work arrives.
Handoff intent is retained too: a crash during handoff needs operator
reconciliation. Inspect shared `review-work-*` records before manual repair.
Never delete uncertain POST intents merely because a review is not yet visible.

This is **not exactly-once GitHub publication**: GitHub has no external fencing
or conditional-head review POST. The worker pins `commit_id` and rechecks the
head before posting, but a concurrent push can still race the POST. Structural
validation does not prove natural-language evidence claims. Keep the feature
disabled until deployment prerequisites are verified.
