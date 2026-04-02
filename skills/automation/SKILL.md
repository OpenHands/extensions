---
name: automation
description: Create and manage OpenHands automations - scheduled tasks that run in sandboxes. Use for cron-scheduled automations.
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
> 1. **ALWAYS use the preset/prompt endpoint** (`POST /v1/preset/prompt`) to create automations. This is the only approach the agent should use by default. It handles all SDK boilerplate, tarball packaging, and upload automatically.
> 2. **NEVER write custom SDK scripts or create tarballs yourself.** Do not generate Python SDK code, `setup.sh` files, or tarball uploads on behalf of the user unless they explicitly ask for it.
> 3. **If the preset/prompt approach cannot satisfy the user's requirement**, do NOT silently fall back to custom automation. Instead, explain the available options to the user:
>    - **Prompt preset** (recommended) — describe what it can do and its limitations
>    - **Custom SDK script** — explain that the user can write their own SDK code with full control, and point them to the [Custom Automation Reference](./CUSTOM.md)
>    - Let the user choose which approach to use.
> 4. **Only create custom SDK scripts if the user explicitly requests it.** When they do, refer to [CUSTOM.md](./CUSTOM.md) for the full reference.

## Authentication

All requests require Bearer authentication with your OpenHands API key:

```bash
-H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

The `OPENHANDS_API_KEY` environment variable should be available in your session.

## API Endpoints

All automation endpoints use the OpenHands Cloud API. The production host is `app.all-hands.dev`.

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

Use the **preset/prompt endpoint** to create automations. You provide a natural language prompt describing what the automation should do, and the service handles everything else — SDK code generation, tarball packaging, upload, and automation creation.

### How It Works

1. You send a prompt describing the task (e.g., "Generate a weekly status report")
2. The service generates SDK boilerplate that will:
   - Connect to the user's OpenHands Cloud account
   - Fetch their LLM config, secrets, and MCP server configuration
   - Create an AI agent conversation with the prompt
   - Run the conversation and report completion
3. The service packages the code into a tarball, uploads it, and creates the automation

### Request

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Automation Name",
    "prompt": "What you want the automation to do",
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
| `prompt` | Yes | Natural language instructions for what the automation should do (1-50,000 characters) |
| `trigger.type` | Yes | Must be `"cron"` |
| `trigger.schedule` | Yes | Cron expression (5 fields: min hour day month weekday) |
| `trigger.timezone` | No | IANA timezone (default: `"UTC"`) |
| `timeout` | No | Max execution time in seconds (default: system maximum) |

### Prompt Tips

Write the prompt as if you are instructing an AI agent. The prompt is executed inside a sandbox with full tool access (bash, file editing, etc.), the user's configured LLM, their stored secrets, and their MCP server integrations. Examples:

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

### Common Schedules

| Schedule | Description |
|----------|-------------|
| `0 9 * * *` | Every day at 9:00 AM |
| `0 9 * * 1-5` | Weekdays at 9:00 AM |
| `0 9 * * 1` | Every Monday at 9:00 AM |
| `0 0 1 * *` | First day of month at midnight |
| `*/15 * * * *` | Every 15 minutes |
| `0 */6 * * *` | Every 6 hours |

### Response (HTTP 201)

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "My Automation Name",
  "trigger": {
    "type": "cron",
    "schedule": "0 9 * * *",
    "timezone": "UTC"
  },
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

### Get Automation Details

```bash
curl "https://app.all-hands.dev/api/automation/v1/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Update Automation

```bash
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

Updatable fields: `name`, `trigger`, `enabled`, `timeout`.

### Delete Automation

```bash
curl -X DELETE "https://app.all-hands.dev/api/automation/v1/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Manually Trigger a Run

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/{automation_id}/dispatch" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### List Automation Runs

```bash
curl "https://app.all-hands.dev/api/automation/v1/{automation_id}/runs?limit=20" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

**Run Status Values:**

| Status | Description |
|--------|-------------|
| `PENDING` | Run scheduled, waiting for dispatch |
| `RUNNING` | Execution in progress |
| `COMPLETED` | Run finished successfully |
| `FAILED` | Run failed, check `error_detail` |

---

## Sandbox Lifecycle

After an automation run completes, the sandbox is **kept alive** by default. This means:
- Users can view the full conversation history in the OpenHands UI
- Users can continue or resume the conversation interactively
- The sandbox persists until it times out or is manually deleted

---

## When the Prompt Preset Is Not Enough

The prompt preset covers most use cases. However, if the user needs any of the following, the preset may not be sufficient:

- Custom Python dependencies beyond what the SDK provides
- A specific runtime environment or non-Python entrypoint
- Multi-file project structure with complex logic
- Direct control over the SDK conversation lifecycle
- Integration with tools not available through the standard agent

**In these cases, do not attempt to create custom automation yourself.** Instead, explain the options to the user and let them decide. If they choose the custom route, refer them to the [Custom Automation Reference](./CUSTOM.md) which covers tarball uploads, SDK code structure, environment variables, and complete examples.