---
name: github-delivery-watchdog
description: Periodically check pull requests and merge only current heads with independent review, tests, and passing CI.
triggers:
- /github-delivery-watchdog
---

# GitHub delivery watchdog

Periodically check pull requests and merge only current heads with independent review, tests, and passing CI.

Create this automation separately from implementation and review. Select an agent
profile on its definition. The profile owns the model, tools, and `secret_refs`;
this workflow does not choose a profile or discover credentials from host settings.
Use a fine-grained GitHub PAT limited to the selected repositories with
Contents: read and write; Pull requests, Actions, Commit statuses, and Metadata:
read. Store it in the Agent Server secret store and select its name in
the profile. Never put the token value in the automation definition or prompt.
The watchdog does not need Issues access. GitHub's [merge endpoint](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request)
requires Contents write; listing and reading pull requests only needs Pull requests read.

Package `scripts/worker.py` as `worker.py` and the shared
`scripts/github_client.py` as `github_client.py`.
The catalog bundle declares these exact files. Supply `config.json` with `repos`
(an array of `owner/repo` names). The entrypoint is `python3 worker.py
--github-token-secret GITHUB_PERSONAL_ACCESS_TOKEN`; if the selected profile uses
another secret name, pass that name instead. Naming a secret does not grant it:
the Agent Server only supplies secrets allowed by the profile.

The watchdog is an ordinary Automation host command and creates no agent,
conversation, or workspace. Its selected profile scopes the GitHub credential
supplied to that command. Automation owns scheduling, cancellation, and cleanup.

Set `branch_prefix` (default `openhands/issue`), `base_branch` (defaults to the repository's default branch),
and `required_workflow_ids` when particular Actions workflows must run. The
watchdog requires `software-factory/tests` and `software-factory/review` success
statuses on the exact head, all other statuses and Actions passing, a current
base, a non-draft PR, and GitHub reporting it mergeable. Missing, pending, failed,
or inaccessible evidence does not permit merge. A changed head requires fresh
review and tests. The merge request includes the expected head SHA.

Actions workflows are optional when `required_workflow_ids` is empty: some
repositories run their CI entirely in the independent reviewer sandbox. The
two acceptance statuses remain mandatory even when there are no Actions runs.
Configure required workflow IDs if GitHub Actions must also supply evidence.

The gate reads commit statuses and GitHub Actions runs; it does not inspect
third-party Check Runs directly. Require any external Check Runs through GitHub
branch protection or rulesets, and do not give the watchdog permission to bypass
those rules. Alternatively, have the CI service publish a commit status or run
through Actions. GitHub enforces its required checks on the merge request; a
rejected merge is recorded and the watchdog continues with other PRs.

Every published commit status must succeed, including third-party contexts. An
orphaned pending or failed status can therefore block that head indefinitely;
restore the responsible service or move to a new head with fresh acceptance
evidence instead of weakening the gate.
