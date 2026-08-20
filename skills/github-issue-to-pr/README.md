# GitHub Issue to PR

Create an automation that implements GitHub issues when a configurable trigger
label is applied, and opens the pull request for you.

## Trigger

This skill is activated by:

- `/issue-to-pr:setup`

## Features

- Implements an issue on demand by watching for a GitHub label event
- Watches several repositories from a single automation, each with its own state
- Processes each label application exactly once, with persistent state
- Re-runs on demand by removing and re-applying the label, on a fresh branch
- Clones the default branch for the agent, and removes the clone when the task
  ends, so nothing accumulates between runs
- Commits, pushes, and opens the pull request in Python, after the agent stops
- Opens draft pull requests by default, titled `[#42] <issue title>`, with the
  agent's summary and `Closes #42` in the body
- Comments on the issue when work starts, when it finishes, and when it does not
- Posts the agent's answer instead of a pull request when it made no changes
- Caps how many conversations one poll starts, so a labelled backlog does not
  start dozens at once

## Credentials the agent does not get

The agent's workspace is a clone whose `origin` carries no token, and it is
handed only the secrets named in `AGENT_SECRET_NAMES` - none, by default - and
none of the deployment's MCP servers. Every GitHub write happens in the
automation script, after the conversation has stopped.

This matters because the prompt is built from an issue title, body, and comment
thread, which anyone able to file an issue can write. A conversation driven by
that text should not also hold a token that can push branches, comment as you, or
read the rest of your secrets.

## Prerequisites

Set `GITHUB_PERSONAL_ACCESS_TOKEN` in OpenHands Settings -> Secrets. The token
must be able to read the repositories, read and write issues (for the progress
comments), **write contents** (to push the branch), and **write pull requests**.

The automation runtime must have `git` available; the script clones, commits, and
pushes with it.

## Quick Start

Ask OpenHands:

> "Set up an issue-to-PR automation for my `myorg/backend` repo using the
> `openhands` label."

After setup, apply the configured label to an issue to queue an implementation.
To ask for another attempt later, remove and re-apply the label.

## See Also

- [SKILL.md](SKILL.md) - Full setup workflow reference
- [references/state-schema.md](references/state-schema.md) - State document and
  task lifecycle
