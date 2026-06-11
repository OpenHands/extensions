---
name: linear-triage
description: >
  Create an automation that triages new Linear issues. Inspects the issue
  title, description, team, customer, priority, and recent related issues via
  Linear MCP. Suggests labels, priority, likely owner, duplicates, and posts
  a clarifying comment.
triggers:
  - /linear-triage:setup
---

# Linear Issue Triage Automation

Set up an automation that triages new Linear issues — classifying, labeling,
and suggesting owners automatically.

---

## Prerequisites

### Required integration

- **Linear MCP** must be installed in Settings → MCP.

### Information to collect

Ask the user for:

1. **Teams/projects** — which Linear teams or projects should be triaged (e.g. `Engineering`, `Support`)
2. **Label taxonomy** — what labels are used for classification? (e.g. `bug`, `feature`, `support`, `chore`)
3. **Priority conventions** — how does the team use priority levels? Any mapping rules?
4. **Auto-apply or suggest** — should the automation apply labels/priority/assignee directly, or post a triage comment with suggestions for human approval?
5. **Duplicate detection** — should it search for and flag potential duplicate issues?

---

## Setup Workflow

### Step 1 — Verify Linear MCP access

Confirm the Linear MCP integration is working:
```
Use the Linear MCP to list recent issues for one of the target teams.
```

If it fails, tell the user to install the Linear MCP integration first.

### Step 2 — Determine trigger type

**Event-based (recommended if publicly reachable):**
Check `<RUNTIME_SERVICES>` for deployment reachability. If public, recommend an event trigger on Linear `Issue` create events.

**Cron-based (local/private deployments):**
Poll for recently created issues on a schedule (e.g. every 5 minutes).

### Step 3 — Build the triage prompt

Construct a prompt that includes:
- Target teams/projects
- Label taxonomy and classification rules
- Priority mapping conventions
- Whether to auto-apply or suggest
- Duplicate detection preference

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
    "name": "Linear Issue Triage",
    "prompt": "<constructed triage prompt>",
    "trigger": <trigger config from step 2>
  }'
```

PowerShell note: use `curl.exe` for this exact flag syntax, and replace `${OPENHANDS_HOST}` / `$OPENHANDS_AUTOMATION_API_KEY` with `$env:OPENHANDS_HOST` / `$env:OPENHANDS_AUTOMATION_API_KEY` if running it natively.

### Step 5 — Confirm

Tell the user:
> ✅ **Linear Issue Triage** is running!
>
> - Automation ID: `{id}`
> - Teams: `{team list}`
> - Mode: `{auto-apply or suggest}`
> - Trigger: `{trigger description}`
