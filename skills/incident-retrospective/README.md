# Incident Retrospective Drafter

Create an automation that drafts incident retrospectives from Slack, Linear, and Notion.

## Triggers

This skill is activated by keywords:

- `draft incident retrospective`
- `incident postmortem`
- `retro automation`

## Features

- **Gathers incident-channel messages from Slack**
- **Collects linked tickets and follow-ups from Linear**
- **Publishes retrospective draft to Notion**
- **Customizable template**: timeline, impact, root cause, action items
- **Supports manual, cron, or event-based triggers**

## Prerequisites

Slack MCP, Linear MCP, and Notion MCP installed in Settings → MCP

## Quick Start

Ask OpenHands:

> "Set up an incident retro automation that pulls from #incidents in
> Slack, checks Linear for follow-ups, and publishes to our Notion retro database"

## See Also

- [SKILL.md](SKILL.md) — Full setup workflow reference
