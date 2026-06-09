# GitHub PR Reviewer

Create an automation that reviews GitHub pull requests on open or update.

## Triggers

This skill is activated by keywords:

- `review pull requests`
- `PR review automation`
- `auto-review PRs`

## Features

- **Inspects PR diff, changed files, and test coverage**
- **Posts review with correctness risks, security issues, missing tests**
- **Supports event-based (webhook) or cron-based (polling) triggers**
- **Configurable review tone (thorough, concise, friendly)**
- **Auto-post or draft mode for human approval**
- **Uses shell-neutral JSON request bodies so setup works across Windows, macOS, and Linux**

## Prerequisites

GitHub MCP installed in Settings → MCP

## Quick Start

Ask OpenHands:

> "Set up a PR review automation for my myorg/backend repo that posts
> concise reviews when PRs are opened"

## See Also

- [SKILL.md](SKILL.md) — Full setup workflow reference
