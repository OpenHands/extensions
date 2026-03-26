# Automation Skill

Create and manage OpenHands automations - scheduled tasks that run SDK scripts in sandboxes on a cron schedule.

## Triggers

This skill is activated by keywords:
- `automation` / `automations`
- `scheduled task`
- `cron job` / `cron schedule`

## Features

- **Tarball Upload**: Upload your code (up to 1MB) for use in automations
- **Automation Creation**: Create cron-scheduled automations
- **Automation Management**: List, update, enable/disable, and delete automations
- **Manual Dispatch**: Trigger automation runs on-demand

## API Base URL

All automation endpoints are at: `https://app.all-hands.dev/api/automation/v1`

## Quick Start

### 1. Upload Your Code

```bash
# Create tarball
tar -czf automation.tar.gz -C /path/to/code .

# Upload (max 1MB)
curl -X POST "https://app.all-hands.dev/api/automation/v1/uploads?name=my-code" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/gzip" \
  --data-binary @automation.tar.gz
```

### 2. Create Automation

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Automation",
    "trigger": {"type": "cron", "schedule": "0 9 * * 1"},
    "tarball_path": "oh-internal://uploads/{upload_id}",
    "entrypoint": "python main.py"
  }'
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/automation/v1/uploads` | POST | Upload a tarball |
| `/api/automation/v1/uploads` | GET | List uploads |
| `/api/automation/v1/uploads/{id}` | GET | Get upload details |
| `/api/automation/v1/uploads/{id}` | DELETE | Delete upload |
| `/api/automation/v1` | POST | Create automation |
| `/api/automation/v1` | GET | List automations |
| `/api/automation/v1/{id}` | GET | Get automation |
| `/api/automation/v1/{id}` | PATCH | Update automation |
| `/api/automation/v1/{id}` | DELETE | Delete automation |
| `/api/automation/v1/{id}/dispatch` | POST | Trigger run |
| `/api/automation/v1/{id}/runs` | GET | List runs |

## See Also

- [SKILL.md](SKILL.md) - Full API reference and examples
