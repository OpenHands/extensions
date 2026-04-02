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

This skill provides documentation for creating and managing OpenHands automations - scheduled tasks that run in sandboxes on a cron schedule.

**Quick Start:** Use the prompt endpoint to create automations with a simple natural language prompt.

## API Endpoints

All automation endpoints use the OpenHands Cloud API. Replace `{host}` with your API host (e.g., `staging.all-hands.dev` or `app.all-hands.dev`).

| Endpoint | Method | Description |
|----------|--------|-------------|
| `{host}/api/automation/v1/preset/prompt` | POST | Create automation from a prompt (recommended) |
| `{host}/api/automation/v1` | POST | Create custom automation |
| `{host}/api/automation/v1` | GET | List automations |
| `{host}/api/automation/v1/{id}` | GET | Get automation details |
| `{host}/api/automation/v1/{id}` | PATCH | Update automation |
| `{host}/api/automation/v1/{id}` | DELETE | Delete automation |
| `{host}/api/automation/v1/{id}/dispatch` | POST | Trigger a run manually |
| `{host}/api/automation/v1/{id}/runs` | GET | List automation runs |
| `{host}/api/automation/v1/uploads` | POST | Upload a tarball |

## Authentication

All requests require Bearer authentication with your OpenHands API key:

```bash
-H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

The `OPENHANDS_API_KEY` environment variable should be available in your session.

---

## Creating Automations (Recommended)

Use the **preset/prompt endpoint** to create automations with a simple natural language prompt. This is the recommended approach for most use cases.

### Request

```bash
curl -X POST "https://{host}/api/automation/v1/preset/prompt" \
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
| `prompt` | Yes | Natural language instructions for what the automation should do |
| `trigger.schedule` | Yes | Cron expression (5 fields: min hour day month weekday) |
| `trigger.timezone` | No | IANA timezone (default: `"UTC"`) |

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

### Example: Generic Automation

```bash
curl -X POST "https://staging.all-hands.dev/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Report",
    "prompt": "generate a daily status report and save it to a file in the workspace",
    "trigger": {
      "type": "cron",
      "schedule": "0 9 * * 1",
      "timezone": "UTC"
    }
  }'
```

---

## Managing Automations

### List Automations

```bash
curl "https://{host}/api/automation/v1?limit=20" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Get Automation Details

```bash
curl "https://{host}/api/automation/v1/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Update Automation

```bash
curl -X PATCH "https://{host}/api/automation/v1/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### Delete Automation

```bash
curl -X DELETE "https://{host}/api/automation/v1/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Manually Trigger a Run

```bash
curl -X POST "https://{host}/api/automation/v1/{automation_id}/dispatch" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### List Automation Runs

```bash
curl "https://{host}/api/automation/v1/{automation_id}/runs?limit=20" \
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

## Custom Automation Reference

For advanced use cases where you need full control over your automation code, you may need to create a custom automation with your own tarball and entrypoint.

**When to use custom automation:**
- You need full control over the automation code structure
- You want to use custom dependencies or runtime
- The prompt endpoint doesn't meet your requirements

See [CUSTOM.md](./CUSTOM.md) for:
- Tarball uploads and structure
- Creating custom automations with your own code
- Writing automation code with the OpenHands SDK
- Environment variables
- Validation rules
- Complete examples

---

## Sandbox Lifecycle

After an automation run completes, the sandbox is **kept alive** by default. This means:
- Users can view the full conversation history in the OpenHands UI
- Users can continue or resume the conversation interactively
- The sandbox persists until it times out or is manually deleted

When writing custom automation code, the `Conversation` class accepts a `delete_on_close` parameter (defaults to `False` for remote conversations). See [CUSTOM.md](./CUSTOM.md) for details on controlling sandbox and conversation lifecycle.

---

## SDK Documentation

Automation code uses the **OpenHands Software Agent SDK**. See https://docs.openhands.dev/sdk for complete API reference.

### Required SDK Packages

```bash
pip install openhands-sdk openhands-workspace openhands-tools
```