---
name: github-delivery-watchdog
description: Periodically check pull requests and merge only current heads with independent review, tests, and passing CI.
triggers:
- /github-delivery-watchdog
---

# GitHub delivery watchdog

This is a deterministic scheduled host command. It creates no agent or
conversation and needs no agent profile. Configure a repository-scoped
fine-grained PAT with Contents and Issues read/write plus Pull requests, Actions,
Commit statuses, and Metadata read. Contents write permits merge; Issues write
retains the review label when the branch is updated. Never put the token value in
the automation definition.

Package `scripts/worker.py` as `worker.py` and the shared
`scripts/github_client.py` as `github_client.py`.
The catalog bundle declares these exact files. Its `config.json` supplies
`repos`, `branch_prefix`, and the saved secret name. The shared GitHub client
resolves only that named secret. Automation owns scheduling and cancellation.

Set `branch_prefix` (default `openhands/issue`), `base_branch` (defaults to the repository's default branch),
and `required_workflow_ids` when particular Actions workflows must run. The
watchdog requires `software-factory/tests` and `software-factory/review` success
statuses on the exact head, all other statuses and Actions passing, a current
base, a non-draft PR, and GitHub reporting it mergeable. Missing, pending, failed,
or inaccessible evidence does not permit merge. A changed head requires fresh
review and tests. When an accepted branch is behind the base, the watchdog asks
GitHub to update it and retains the review trigger label; it considers the new
head only on a later run. The merge request includes the expected head SHA.

Actions are optional when `required_workflow_ids` is empty; the two acceptance
statuses remain mandatory. Configure workflow IDs when GitHub Actions must also
supply evidence. Branch protection remains GitHub's final merge gate.
