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

## Quick Start

### 1. Upload Your Code

```bash
# Create tarball
tar -czf automation.tar.gz -C /path/to/code .

# Upload (max 1MB)
curl -X POST "https://automations.all-hands.dev/api/v1/uploads?name=my-code" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/gzip" \
  --data-binary @automation.tar.gz
```

### 2. Create Automation

```bash
curl -X POST "https://automations.all-hands.dev/api/v1/automations" \
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
| `/api/v1/uploads` | POST | Upload a tarball |
| `/api/v1/uploads` | GET | List uploads |
| `/api/v1/uploads/{id}` | GET | Get upload details |
| `/api/v1/uploads/{id}` | DELETE | Delete upload |
| `/api/v1/automations` | POST | Create automation |
| `/api/v1/automations` | GET | List automations |
| `/api/v1/automations/{id}` | GET | Get automation |
| `/api/v1/automations/{id}` | PATCH | Update automation |
| `/api/v1/automations/{id}` | DELETE | Delete automation |
| `/api/v1/automations/{id}/dispatch` | POST | Trigger run |

## See Also

- [SKILL.md](SKILL.md) - Full API reference and examples
