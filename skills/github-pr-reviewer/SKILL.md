---
name: github-pr-reviewer
description: Review labeled pull request heads and publish readable native GitHub reviews.
triggers:
  - /pr-reviewer:setup
---

# GitHub pull request reviewer

Create a scheduled automation that scans one or more repositories and delegates
each labeled pull request head to a durable agent conversation. The scanner is a
deterministic host command. Automation owns conversation creation, resumption,
scheduling, cancellation, and cleanup; the extension only selects work and
writes the review instruction.

## Setup

Install **GitHub code review** from the Agent Canvas automation catalog and set:

- the repositories to scan;
- the pull request label that requests review;
- the review tone;
- the name of the saved GitHub token secret; and
- the polling schedule.

Use a fine-grained PAT limited to those repositories. It needs Contents and
Actions read, plus Pull requests, Issues, and Commit statuses read/write. It does
not need Contents write because the reviewer never pushes code. Never put the
token value in the automation definition or prompt.

The catalog bundles `worker.py`, the existing reviewer prompt builder in
`main.py`, and the shared `github_client.py`. Its entrypoint is `python3
worker.py`; manual script rewriting, uploads, state files, checkouts, and
conversation polling are unnecessary.

## Selection and delivery

On each scan, the worker:

1. Finds open pull requests carrying the configured review label.
2. Reads the latest matching label event and the current head SHA.
3. Submits one idempotent subject turn keyed by that label event and exact head.
4. Leaves a changed head labeled so a later scan reviews the new revision.

Failures are isolated per pull request, so one unavailable subject does not block
other reviews. The stable subject is GitHub's immutable repository ID plus the
pull request number, which keeps revisions in one conversation while repositories
and pull requests remain independent.

## Agent contract

The delegated reviewer clones and checks out the exact head in detached mode,
uses the existing reviewer prompt, inspects current GitHub discussion and checks,
and runs appropriate focused tests. It never modifies tracked files.

Before reporting, it confirms that the head is unchanged. It publishes one
readable native review and records `software-factory/review` and
`software-factory/tests` on the exact head. Only an explicit `✅ APPROVED` verdict
sets the review status to success. It removes the trigger label only after both
statuses are visible. It never posts raw JSON artifacts or full command logs as
comments.

The prompt names the configured secret rather than embedding a credential. The
runtime decides which saved secrets are available to the agent.
