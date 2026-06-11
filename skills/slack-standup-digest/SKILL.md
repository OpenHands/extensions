---
name: slack-standup-digest
description: >
  Create an automation that generates an async standup digest from Slack.
  Searches selected channels for messages since the previous workday, groups
  updates by project, highlights blockers and decisions, and posts a summary
  to a target channel.
triggers:
  - /standup-digest:setup
---

# Slack Standup Digest Automation

Set up a recurring automation that summarizes Slack activity into an async
standup digest.

---

## Prerequisites

### Required integration

- **Slack MCP** must be installed in Settings → MCP.

### Information to collect

Ask the user for:

1. **Source channels** — which Slack channels to scan for updates (e.g. `#engineering`, `#frontend`, `#backend`)
2. **Target channel** — where the digest should be posted (e.g. `#standup`, `#team-updates`)
3. **Schedule** — when should the digest run? Default: weekday mornings at 9 AM
4. **Timezone** — user's timezone (e.g. `America/New_York`, `Europe/London`)
5. **Auto-post or draft** — should the digest post automatically, or be saved for the user to review and approve first?
6. **Grouping** — how should updates be organized? Default: by project/channel, with sections for shipped work, active work, blockers, and decisions

---

## Setup Workflow

### Step 1 — Verify Slack MCP access

Confirm the Slack MCP integration is working:
```
Use the Slack MCP to search for recent messages in one of the source channels.
```

If it fails, tell the user to install the Slack MCP integration first.

### Step 2 — Configure the schedule

Build a cron schedule from the user's preferences:
- Weekday mornings at 9 AM ET: `0 9 * * 1-5` with timezone `America/New_York`
- Daily at 8 AM UTC: `0 8 * * *`

### Step 3 — Build the digest prompt

Construct a prompt that includes:
- Source channels to scan
- Target channel for posting
- Lookback window (typically "since previous workday" — Friday→Monday for Monday digests)
- Grouping structure (by project, by channel, etc.)
- Whether to auto-post or draft
- What to highlight: blockers, decisions, shipped items, unanswered questions

### Step 4 — Create the automation

Read the Automation backend URL and auth from `<RUNTIME_SERVICES>`:
- Use the **Automation backend** `url_from_agent` as `OPENHANDS_HOST`
- Auth: `X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY`

Use the **prompt preset** endpoint:
```bash
curl -s -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/prompt" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Slack Standup Digest",
    "prompt": "<constructed digest prompt>",
    "trigger": {"type": "cron", "schedule": "<schedule>", "timezone": "<tz>"}
  }'
```

PowerShell note: use `curl.exe` for this exact flag syntax, and replace `${OPENHANDS_HOST}` / `$OPENHANDS_AUTOMATION_API_KEY` with `$env:OPENHANDS_HOST` / `$env:OPENHANDS_AUTOMATION_API_KEY` if running it natively.

### Step 5 — Confirm

Tell the user:
> ✅ **Slack Standup Digest** is running!
>
> - Automation ID: `{id}`
> - Source channels: `{channel list}`
> - Target channel: `{target}`
> - Schedule: `{cron description}`
> - Mode: `{auto-post or draft}`
