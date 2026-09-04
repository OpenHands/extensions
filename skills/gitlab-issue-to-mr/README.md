# GitLab Issue to MR

Create an automation that implements GitLab issues when a configurable trigger
label is applied, and opens the merge request for you.

## Trigger

This skill is activated by:

- `/issue-to-mr:setup`

## Features

- Implements an issue on demand by watching for a GitLab label event
- Watches several projects from a single automation, each with its own state
- Works against gitlab.com and self-managed instances, subgroups included
- Processes each label application exactly once, with persistent state
- Re-runs on demand by removing and re-applying the label, on a fresh branch
- Clones the default branch for the agent, and removes the clone when the task
  ends, so nothing accumulates between runs
- Lets the agent open the merge request, and opens it in Python when the agent
  did not
- Opens draft merge requests by default, titled `Draft: [#42] <issue title>`,
  with the agent's summary and `Closes #42` in the description
- Comments on the issue when work starts, when it finishes, and when it does not
- Posts the agent's answer instead of a merge request when it made no changes
- Caps how many conversations one poll starts, so a labelled backlog does not
  start dozens at once

## What the agent is told, and what it can reach

The prompt names the project, the issue IID and title, and its URL. The agent
fetches the description, the discussion, and anything they link to itself - a
copy pasted at dispatch would already be stale, and it would stop where the
issue's own text stops.

Reading that needs credentials, so the conversation is handed exactly one secret,
`GITLAB_TOKEN`, and none of the deployment's MCP servers. `AGENT_SECRET_NAMES` is
an allow-list, so the rest of the secret store stays out of reach of a
conversation whose instructions came from an issue. Set it to `[]` for public
projects if you would rather it held nothing.

The agent commits, pushes its branch, and opens the merge request itself, so it
appears as soon as the agent stops instead of waiting for the next poll. The
script verifies that on GitLab rather than trusting the agent's word, and opens
the merge request itself when the agent did not - a failed push or a dead
conversation never loses the work. `origin` carries no credential, so each GitLab
command has to name `GITLAB_TOKEN`, which the SDK injects only into a command
that mentions it and masks in the output.

## Two setup paths

The `/issue-to-mr:setup` conversation substitutes the constants at the top of
`scripts/main.py` and uploads the result. The catalog entry
(`automations/catalog/gitlab-issue-to-mr/`) ships the same script unmodified as
a **bundle** and renders a `config.json` beside it from the setup form, which the
script loads over those constants. Both paths produce the same automation: a
tarball the automation service runs on a cron, not a prompt handed to an agent.

## Prerequisites

Set `GITLAB_TOKEN` in OpenHands Settings -> Secrets. It needs the `api` scope and
at least the **Developer** role on every watched project - Developer is the
lowest role that can push a branch and open a merge request. Leave the configured
branch prefix out of any protected-branch rule, or the push is rejected.

For a self-managed instance, give its API root
(`https://gitlab.example.com/api/v4`) during setup.

The automation runtime must have `git` available; the script clones, commits, and
pushes with it.

## Quick Start

Ask OpenHands:

> "Set up an issue-to-MR automation for my `myorg/backend` GitLab project using
> the `openhands` label."

After setup, apply the configured label to an issue to queue an implementation.
To ask for another attempt later, remove and re-apply the label.

## See Also

- [SKILL.md](SKILL.md) - Full setup workflow reference
- [references/state-schema.md](references/state-schema.md) - State document and
  task lifecycle
