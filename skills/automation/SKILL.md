---
name: automation
description: This skill should be used when the user asks to "create an automation", "schedule a task", "set up a cron job", or mentions automations, scheduled tasks, or cron scheduling in OpenHands Cloud.
triggers:
- automation
- automations
- scheduled task
- cron job
- cron schedule
---

# OpenHands Automations

Create and manage scheduled tasks that run in OpenHands Cloud sandboxes on a cron schedule.

> **⚠️ CRITICAL — Agent behavior rules:**
>
> 1. **ALWAYS use the preset/prompt endpoint** (`POST /v1/preset/prompt`) to create automations. It handles all SDK boilerplate, tarball packaging, and upload automatically.
> 2. **NEVER write custom SDK scripts or create tarballs.** Do not generate Python SDK code, `setup.sh` files, or tarball uploads unless the user explicitly asks for it.
> 3. **If the preset/prompt approach cannot satisfy the requirement**, do NOT silently fall back to custom automation. Instead, explain the available options to the user:
>    - **Prompt preset** (recommended) — describe what it can do and its limitations
>    - **Custom SDK script** — the user can write their own SDK code with full control; point them to `references/custom-automation.md`
>    - Let the user choose which approach to use.
> 4. **Only create custom SDK scripts if the user explicitly requests it.** Refer to `references/custom-automation.md` for the full reference.

## Authentication

All requests require Bearer authentication:

```bash
-H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

## API Endpoints

Production host: `app.all-hands.dev`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/automation/v1/preset/prompt` | POST | **Create automation from a prompt (always use this)** |
| `/api/automation/v1` | GET | List automations |
| `/api/automation/v1/{id}` | GET | Get automation details |
| `/api/automation/v1/{id}` | PATCH | Update automation |
| `/api/automation/v1/{id}` | DELETE | Delete automation |
| `/api/automation/v1/{id}/dispatch` | POST | Trigger a run manually |
| `/api/automation/v1/{id}/runs` | GET | List automation runs |

---

## Creating Automations

Use the **preset/prompt endpoint**. Provide a natural language prompt describing the task, and the service handles SDK code generation, tarball packaging, upload, and automation creation.

### How It Works

1. Send a prompt describing the task (e.g., "Generate a weekly status report")
2. The service generates SDK boilerplate that connects to the user's OpenHands Cloud account, fetches their LLM config, secrets, and MCP server configuration, creates an AI agent conversation with the prompt, and reports completion
3. The service packages the code into a tarball, uploads it, and creates the automation

### Request

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Automation Name",
    "prompt": "What the automation should do",
    "trigger": {
      "type": "cron",
      "schedule": "0 9 * * *",
      "timezone": "UTC"
    }
  }'
```

### Request Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Name of the automation (1-500 characters) |
| `prompt` | Yes | Natural language instructions (1-50,000 characters) |
| `trigger.type` | Yes | Must be `"cron"` |
| `trigger.schedule` | Yes | Cron expression (5 fields: min hour day month weekday) |
| `trigger.timezone` | No | IANA timezone (default: `"UTC"`) |
| `timeout` | No | Max execution time in seconds (default: system maximum) |

### Prompt Tips

Write the prompt as an instruction to an AI agent. The prompt executes inside a sandbox with full tool access (bash, file editing, etc.), the user's configured LLM, stored secrets, and MCP server integrations. Examples:

- `"Generate a weekly status report summarizing the team's GitHub activity and post it to Slack"`
- `"Check the production API health endpoint every hour and alert if it returns non-200"`
- `"Pull the latest data from our analytics API and update the dashboard spreadsheet"`

### Cron Schedule

| Field | Values | Description |
|-------|--------|-------------|
| Minute | 0-59 | Minute of the hour |
| Hour | 0-23 | Hour of the day (24-hour) |
| Day | 1-31 | Day of the month |
| Month | 1-12 | Month of the year |
| Weekday | 0-6 | Day of week (0=Sun, 6=Sat) |

Common schedules: `0 9 * * *` (daily 9 AM), `0 9 * * 1-5` (weekdays 9 AM), `0 9 * * 1` (Mondays 9 AM), `0 0 1 * *` (first of month), `*/15 * * * *` (every 15 min), `0 */6 * * *` (every 6 hours).

### Response (HTTP 201)

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "My Automation Name",
  "trigger": {"type": "cron", "schedule": "0 9 * * *", "timezone": "UTC"},
  "enabled": true,
  "created_at": "2025-03-25T10:00:00Z"
}
```

### Examples

**Daily report:**
```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Report",
    "prompt": "Generate a daily status report and save it to a file in the workspace",
    "trigger": {"type": "cron", "schedule": "0 9 * * 1-5", "timezone": "America/New_York"}
  }'
```

**Weekly cleanup:**
```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weekly Cleanup",
    "prompt": "Clean up temporary files older than 7 days and send a summary of what was removed",
    "trigger": {"type": "cron", "schedule": "0 2 * * 0", "timezone": "UTC"},
    "timeout": 300
  }'
```

---

## Managing Automations

### List Automations

```bash
curl "https://app.all-hands.dev/api/automation/v1?limit=20" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Get / Update / Delete

```bash
# Get details
curl "https://app.all-hands.dev/api/automation/v1/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"

# Update (fields: name, trigger, enabled, timeout)
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Delete
curl -X DELETE "https://app.all-hands.dev/api/automation/v1/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Trigger and Monitor Runs

```bash
# Manually trigger a run
curl -X POST "https://app.all-hands.dev/api/automation/v1/{automation_id}/dispatch" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"

# List runs
curl "https://app.all-hands.dev/api/automation/v1/{automation_id}/runs?limit=20" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

Run status values: `PENDING` (waiting for dispatch), `RUNNING` (in progress), `COMPLETED` (success), `FAILED` (check `error_detail`).

---

## Sandbox Lifecycle

After a run completes, the sandbox is **kept alive** by default — users can view the conversation history in the OpenHands UI and continue interacting. The sandbox persists until it times out or is manually deleted.

---

## When the Prompt Preset Is Not Enough

The prompt preset covers most use cases. It may not be sufficient when custom Python dependencies, a non-Python entrypoint, multi-file project structure, direct SDK conversation lifecycle control, or non-standard tool integrations are required.

**Do not attempt to create custom automation without explicit user request.** Instead, explain the options and let the user decide. If they choose the custom route, refer to `references/custom-automation.md`.

## Reference Files

- **`references/custom-automation.md`** — Detailed guide for custom automations: tarball uploads, SDK code structure, environment variables, validation rules, and complete examples. Only use when the user explicitly requests a custom automation.