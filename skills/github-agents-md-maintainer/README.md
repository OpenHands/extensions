# AGENTS.md Maintainer

Create an automation that keeps `AGENTS.md` current in one or more GitHub
repositories, on a schedule.

## Trigger

This skill is activated by:

- `/agents-md:setup`

## Features

- Creates `AGENTS.md` when it is missing, updates it when the repository has
  moved on, and leaves it alone when it is accurate
- Runs weekly by default, keyed by ISO week, so extra runs inside a week are
  harmless
- Stays quiet while one of its own pull requests is still open, instead of
  stacking a pull request per week over the same file
- Maintains several repositories from one automation, each with its own state
- Clones the default branch for the agent and removes the clone when the run ends
- Lets the agent open the pull request, and opens it in Python when the agent
  did not - a failed push or a dead conversation never loses the work
- Opens draft pull requests by default, titled `docs: update AGENTS.md` or
  `docs: add AGENTS.md`

## What the agent is asked to do

Read the repository - layout, the build, test, lint and format commands as they
are actually defined, language and framework versions, contributing docs - and
edit `AGENTS.md` to match. It is told to treat an existing file as someone
else's writing: correct what is wrong, add what is missing, remove what no
longer exists, and leave the rest alone. Only knowledge that helps in most
future tasks belongs there, which is the rule the `agent-memory` skill sets out;
task-specific notes and unverified commands do not.

## Prerequisites

Set `GITHUB_PERSONAL_ACCESS_TOKEN` in OpenHands Settings -> Secrets, able to
read the repositories, **write contents** (to push the branch) and **write pull
requests**. No issue permission is needed - this automation never comments on an
issue.

The automation runtime must have `git` available.

## Quick Start

Ask OpenHands:

> "Set up an AGENTS.md maintenance automation for `myorg/backend` and
> `myorg/frontend`, weekly."

## See Also

- [SKILL.md](SKILL.md) - Full setup workflow reference
- [references/state-schema.md](references/state-schema.md) - State document and
  task lifecycle
- [../agent-memory/SKILL.md](../agent-memory/SKILL.md) - What belongs in an
  AGENTS.md, and what does not
