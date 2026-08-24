---
name: incident-retrospective
description: >
  Create an automation that drafts incident retrospectives. Gathers
  incident-channel messages from Slack, collects linked tickets and follow-ups
  from Linear, and publishes a retrospective draft to Notion with a timeline,
  impact summary, root-cause hypotheses, and action items.
triggers:
  - /incident-retro:setup
---

# Incident Retrospective Drafter Automation

Set up an automation that drafts incident retrospectives by pulling data from
Slack, Linear, and Notion.

---

## Prerequisites

### Required integrations

All three MCP integrations must be installed in Settings → MCP:

- **Slack MCP** — to gather incident-channel messages
- **Linear MCP** — to collect linked tickets and follow-ups
- **Notion MCP** — to publish the retrospective draft

### Information to collect

Ask the user for:

1. **Incident identification** — how are incidents identified? (e.g. Slack channel naming convention like `#inc-*`, a Linear label, or manual trigger)
2. **Slack channels** — which channels contain incident chatter (e.g. `#incidents`, `#inc-*` pattern)
3. **Linear teams** — which Linear teams/projects to inspect for follow-up tickets
4. **Retrospective template** — what sections should the retro include? Default: Timeline, Impact, Root Cause, Action Items, Lessons Learned
5. **Notion destination** — which Notion database or page should receive the draft
6. **Trigger type** — manual dispatch, cron schedule, or triggered by an incident label being added

---

## Setup Workflow

### Step 1 — Verify MCP access

Test each integration:
```
Use the Slack MCP to list recent messages in an incident channel.
Use the Linear MCP to list recent issues for the target team.
Use the Notion MCP to search for the destination database.
```

If any fail, tell the user which integration needs to be installed first.

### Step 2 — Determine trigger type

Ask the user how retros should be triggered:
- **Manual** — dispatch from the automations page when an incident wraps up
- **Cron** — run daily/weekly to check for recent incidents
- **Event** — triggered by a Linear label change or Slack message

### Step 3 — Build the retro prompt

Construct a prompt that includes:
- How to identify the incident (channel pattern, label, etc.)
- Which Slack channels and Linear teams to query
- The retrospective template/sections
- Where to publish in Notion

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
    "name": "Incident Retrospective Drafter",
    "prompt": "<constructed retro prompt>",
    "trigger": <trigger config from step 2>
  }'
```

PowerShell note: use `curl.exe` for this exact flag syntax, and replace `${OPENHANDS_HOST}` / `$OPENHANDS_AUTOMATION_API_KEY` with `$env:OPENHANDS_HOST` / `$env:OPENHANDS_AUTOMATION_API_KEY` if running it natively.

### Step 5 — Confirm

Tell the user:
> ✅ **Incident Retrospective Drafter** is running!
>
> - Automation ID: `{id}`
> - Incident source: `{identification method}`
> - Slack channels: `{channels}`
> - Linear teams: `{teams}`
> - Notion destination: `{destination}`
> - Trigger: `{trigger description}`
