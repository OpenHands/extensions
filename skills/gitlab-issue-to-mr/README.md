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

Reading that needs credentials, so the conversation is handed one secret,
`GITLAB_TOKEN`. `AGENT_SECRET_NAMES` is an allow-list, so the rest of the secret
store stays out of reach of a conversation whose instructions came from an issue.
Set it to `[]` for public projects if you would rather it held nothing.

The deployment's MCP servers are forwarded whole, as `github-pr-reviewer` does,
so a connected GitLab server gives the agent typed tools instead of curl. That
cuts both ways: everything reachable through those servers is reachable from a
prompt written by whoever opened the issue. Connect only servers you are willing
to have driven by untrusted text.

The agent commits, pushes its branch, and opens the merge request itself, so it
appears as soon as the agent stops instead of waiting for the next poll. The
script verifies that on GitLab rather than trusting the agent's word, and opens
the merge request itself when the agent did not - a failed push or a dead
conversation never loses the work. `origin` carries no credential, so each GitLab
command has to name `GITLAB_TOKEN`, which the SDK injects only into a command
that mentions it and masks in the output.

On OpenHands Cloud and Enterprise the conversation is started through the
OpenHands API in a sandbox of its own, which changes three things:

- The agent clones the project itself; the script keeps no clone.
- The conversation runs with the user's own settings, so the secret allow-list
  above does not apply: it holds the user's secrets and MCP servers.
- A conversation that ends without a merge request is reported on the issue. The
  script cannot finish the work, because it has no copy of it.

A GitLab token is used whenever there is one: a `GITLAB_TOKEN` secret, or else the
token of the user's GitLab sign-in or connected integration. Without a token, a
connected GitLab MCP server is used directly, by the script and by the
conversation. Calling GitLab MCP directly needs GitLab 19.4 or later, because the
tools it uses arrived in 19.3 and 19.4, while a token works with any GitLab.

## Two setup paths

The `/issue-to-mr:setup` conversation substitutes the constants at the top of
`scripts/main.py` and uploads the result. The catalog entry
(`automations/catalog/gitlab-issue-to-mr/`) ships the same script unmodified as
a **bundle** and renders a `config.json` beside it from the setup form, which the
script loads over those constants. Both paths produce an automation tarball,
not a prompt handed to an agent. The catalog offers a schedule or a signed
webhook event; the conversation setup path uses a schedule.

### Signed webhook event trigger (GitLab 19.0+)

In Automations > Templates, choose **Event** to start from a GitLab issue open,
reopen or label-change update instead of periodically scanning for labelled issues.
The worker authenticates to GitLab to confirm the exact project, open state,
trigger label and latest label-application ID, then starts only that issue.
The run waits up to 1600 seconds for the conversation to finish and the merge
request (or completion note) to be verified and posted; it fails if the issue
has not finished by then. A schedule is useful for backlog or for work that
outlasts an event run. Removing and reapplying the label requests another pass.

Before selecting Event, ask the user to register a signed custom webhook source
and configure GitLab **Issue events** on the project or parent group with the
returned URL and the same signing token. Follow the [signed custom webhook
instructions](../gitlab-mr-reviewer/README.md#event-trigger-prerequisite-gitlab-190),
selecting **Issue events** instead of **Merge request events** in GitLab while
keeping `event_key_expr: object_kind`. The same source can serve the reviewer
and refiner if one webhook sends both issue and MR events. Different project
webhooks with different signing tokens need separate sources and automations.
Use a schedule if GitLab does not provide signing tokens (pre-19.0) or the
OpenHands webhook endpoint is not publicly reachable; the older plain-text
`X-Gitlab-Token` is not a substitute. Do not share signing tokens in chat.

## Prerequisites

On OpenHands Cloud and Enterprise, connect GitLab under Settings - its MCP server
or the built-in integration, which signing in with GitLab connects - and no secret
is needed. Calling GitLab MCP directly needs GitLab 19.4 or later, so on an older
GitLab use the integration. Otherwise set
`GITLAB_TOKEN` in OpenHands Settings -> Secrets. It needs the `api` scope and
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
