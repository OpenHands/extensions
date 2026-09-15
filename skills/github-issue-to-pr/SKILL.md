---
name: github-issue-to-pr
description: Implement ready GitHub issues and revise pull requests that fail automated review.
triggers:
  - /issue-to-pr:setup
---

# GitHub issue to pull request

Create a scheduled automation that scans one or more repositories and delegates
each eligible issue to its own durable agent conversation. The scanner is a
deterministic host command. Automation owns conversation creation, resumption,
scheduling, cancellation, and cleanup; the extension only selects work and
writes the agent instruction.

## Setup

Install **GitHub issue to PR** from the Agent Canvas automation catalog and set:

- the repositories to scan;
- the issue label that means work is ready;
- the branch prefix and whether new pull requests are drafts;
- the name of the saved GitHub token secret; and
- the polling schedule.

Use a fine-grained PAT limited to those repositories. It needs Contents, Issues,
and Pull requests read/write plus Metadata and Commit statuses read. Grant
Workflows read/write only when the agent is expected to change workflow files.
Never put the token value in the automation definition or prompt.

The catalog bundles `worker.py`, the existing issue-to-PR prompt builder in
`main.py`, and the shared `github_client.py`. Its entrypoint is `python3
worker.py`; manual script rewriting, uploads, state files, and conversation
polling are unnecessary.

## Selection and delivery

On each scan, the worker:

1. Finds open issues carrying the configured label whose declared dependencies
   are complete.
2. Excludes an issue that already has an open branch using the configured prefix.
3. Submits one idempotent subject turn for each remaining issue, ordered with
   `priority:high` first.
4. Reuses the same issue subject when an existing pull request's exact head has a
   failed `software-factory/review` status.

One failed submission is reported without blocking the other eligible issues.
The stable subject is GitHub's immutable repository ID plus the issue number, so
revisions return to the existing conversation while different repositories and
issues remain independent.

## Agent contract

The delegated agent clones the repository into its empty workspace, checks out
the issue branch, implements the issue, runs the repository's tests, pushes the
branch, and opens or updates the pull request. A new pull request receives the
configured review label. After a revision, the agent removes and reapplies that
label so an independent reviewer checks the exact new head.

The prompt names the configured secret rather than embedding a credential. The
runtime decides which saved secrets are available to the agent.
