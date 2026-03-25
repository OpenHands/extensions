---
name: automation
description: Create and manage OpenHands automations - scheduled tasks that run SDK scripts in sandboxes. Use when creating cron-scheduled automations, uploading tarballs, or managing automation runs.
triggers:
- automation
- automations
- scheduled task
- cron job
- cron schedule
---

# OpenHands Automations

This skill helps you create and manage OpenHands automations - scheduled tasks that run your code in sandboxes on a cron schedule.

## API Base URL

All automation endpoints are at: `https://automations.all-hands.dev/api/v1/`

## Authentication

Use Bearer authentication with your OpenHands API key:

```bash
-H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

The `OPENHANDS_API_KEY` environment variable should be available in your session.

---

## Uploading a Tarball

Before creating an automation, you need to upload your code as a tarball. The upload endpoint streams directly to cloud storage with a **1MB size limit**.

### Create a Tarball

```bash
# Create a tarball from your automation code
tar -czf automation.tar.gz -C /path/to/your/code .
```

Your tarball should contain:
```
automation.tar.gz
├── main.py           # Your entrypoint script
├── setup.sh          # Optional setup script (install deps, etc.)
├── requirements.txt  # Dependencies (if using pip)
└── pyproject.toml    # Or use uv/poetry for dependency management
```

### Upload the Tarball

```bash
curl -X POST "https://automations.all-hands.dev/api/v1/uploads?name=my-automation&description=Weekly%20report%20generator" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/gzip" \
  --data-binary @automation.tar.gz
```

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `name` | Yes | Name for the upload (1-255 characters) |
| `description` | No | Description (max 2000 characters) |

**Allowed Content-Types:**
- `application/x-tar`
- `application/gzip`
- `application/x-gzip`
- `application/x-compressed-tar`
- `application/octet-stream`

**Response (HTTP 201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "...",
  "org_id": "...",
  "name": "my-automation",
  "description": "Weekly report generator",
  "status": "COMPLETED",
  "error_message": null,
  "size_bytes": 12345,
  "tarball_path": "oh-internal://uploads/550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-03-25T10:00:00Z",
  "updated_at": "2025-03-25T10:00:00Z"
}
```

**Important:** Save the `tarball_path` value - you'll need it when creating the automation.

### Upload Status Values

| Status | Description |
|--------|-------------|
| `UPLOADING` | Upload in progress |
| `COMPLETED` | Upload successful, `tarball_path` is available |
| `FAILED` | Upload failed, check `error_message` |

### List Uploads

```bash
curl "https://automations.all-hands.dev/api/v1/uploads?limit=10" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Get Upload Details

```bash
curl "https://automations.all-hands.dev/api/v1/uploads/{upload_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Delete Upload

```bash
curl -X DELETE "https://automations.all-hands.dev/api/v1/uploads/{upload_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

---

## Creating an Automation

Once you have a tarball uploaded (or an external URL), create the automation:

```bash
curl -X POST "https://automations.all-hands.dev/api/v1/automations" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weekly Report Generator",
    "trigger": {
      "type": "cron",
      "schedule": "0 9 * * 1",
      "timezone": "UTC"
    },
    "tarball_path": "oh-internal://uploads/550e8400-e29b-41d4-a716-446655440000",
    "entrypoint": "python main.py",
    "timeout": 300
  }'
```

### Request Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Name of the automation (1-500 characters) |
| `trigger.type` | Yes | Must be `"cron"` |
| `trigger.schedule` | Yes | Cron expression (5 fields: min hour day month weekday) |
| `trigger.timezone` | No | IANA timezone (default: `"UTC"`) |
| `tarball_path` | Yes | Path to code tarball (see Tarball Path Formats below) |
| `entrypoint` | Yes | Command to execute (e.g., `"python main.py"`, `"uv run script.py"`) |
| `setup_script_path` | No | Relative path to setup script inside tarball |
| `timeout` | No | Max execution time in seconds (1-600, default: 600) |

### Tarball Path Formats

| Format | Example | Description |
|--------|---------|-------------|
| Internal upload | `oh-internal://uploads/{uuid}` | Uploaded via `/api/v1/uploads` |
| S3 | `s3://bucket/path/file.tar.gz` | AWS S3 bucket |
| GCS | `gs://bucket/path/file.tar.gz` | Google Cloud Storage |
| HTTPS | `https://example.com/file.tar.gz` | Public HTTPS URL |

### Response (HTTP 201)

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Weekly Report Generator",
  "triggers": {
    "type": "cron",
    "schedule": "0 9 * * 1",
    "timezone": "UTC"
  },
  "tarball_path": "oh-internal://uploads/550e8400-e29b-41d4-a716-446655440000",
  "entrypoint": "python main.py",
  "setup_script_path": null,
  "timeout": 300,
  "enabled": true,
  "created_at": "2025-03-25T10:00:00Z",
  "updated_at": "2025-03-25T10:00:00Z"
}
```

---

## Managing Automations

### List Automations

```bash
curl "https://automations.all-hands.dev/api/v1/automations?limit=20" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Get Automation Details

```bash
curl "https://automations.all-hands.dev/api/v1/automations/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Update Automation

```bash
curl -X PATCH "https://automations.all-hands.dev/api/v1/automations/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false
  }'
```

**Updatable Fields:**
- `name`
- `trigger` (schedule, timezone)
- `tarball_path`
- `entrypoint`
- `setup_script_path`
- `timeout`
- `enabled`

### Delete Automation

```bash
curl -X DELETE "https://automations.all-hands.dev/api/v1/automations/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Manually Trigger a Run

```bash
curl -X POST "https://automations.all-hands.dev/api/v1/automations/{automation_id}/dispatch" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

---

## Cron Schedule Reference

| Field | Values | Description |
|-------|--------|-------------|
| Minute | 0-59 | Minute of the hour |
| Hour | 0-23 | Hour of the day (24-hour) |
| Day | 1-31 | Day of the month |
| Month | 1-12 | Month of the year |
| Weekday | 0-6 | Day of week (0=Sun, 6=Sat) |

### Common Patterns

| Schedule | Description |
|----------|-------------|
| `0 9 * * *` | Every day at 9:00 AM |
| `0 9 * * 1-5` | Weekdays at 9:00 AM |
| `0 9 * * 1` | Every Monday at 9:00 AM |
| `0 0 1 * *` | First day of month at midnight |
| `*/15 * * * *` | Every 15 minutes |
| `0 */6 * * *` | Every 6 hours |

---

## Environment Variables in Your Script

Your automation script receives these environment variables:

| Variable | Description |
|----------|-------------|
| `OPENHANDS_API_KEY` | API key for OpenHands services |
| `OPENHANDS_CLOUD_API_URL` | Base URL for the OpenHands Cloud API |
| `AUTOMATION_RUN_ID` | Unique ID for this run |
| `AUTOMATION_EVENT_PAYLOAD` | JSON with trigger info, automation ID, and name |
| `AUTOMATION_CALLBACK_URL` | URL to POST completion status |

---

## Validation Rules

- **Name**: 1-500 characters
- **Cron schedule**: Valid 5-field cron expression
- **Entrypoint**: Relative path, no shell metacharacters (`;`, `&`, `|`, etc.)
- **Setup script path**: Relative path, no path traversal (`..`)
- **Timeout**: 1-600 seconds (10 minutes max)
- **Tarball size**: 1MB max for uploads

---

## Complete Example: Create Automation from Scratch

```bash
# 1. Create your automation code
mkdir my-automation && cd my-automation

cat > main.py << 'EOF'
import os
import json

print("Running automation!")
print(f"Run ID: {os.environ.get('AUTOMATION_RUN_ID')}")

payload = json.loads(os.environ.get('AUTOMATION_EVENT_PAYLOAD', '{}'))
print(f"Automation: {payload.get('automation_name')}")
EOF

# 2. Create the tarball
tar -czf ../my-automation.tar.gz .
cd ..

# 3. Upload the tarball
UPLOAD_RESPONSE=$(curl -s -X POST \
  "https://automations.all-hands.dev/api/v1/uploads?name=my-automation" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/gzip" \
  --data-binary @my-automation.tar.gz)

TARBALL_PATH=$(echo "$UPLOAD_RESPONSE" | jq -r '.tarball_path')
echo "Uploaded: $TARBALL_PATH"

# 4. Create the automation
curl -X POST "https://automations.all-hands.dev/api/v1/automations" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"My First Automation\",
    \"trigger\": {
      \"type\": \"cron\",
      \"schedule\": \"0 9 * * 1\",
      \"timezone\": \"UTC\"
    },
    \"tarball_path\": \"$TARBALL_PATH\",
    \"entrypoint\": \"python main.py\",
    \"timeout\": 60
  }"
```

---

## Troubleshooting

### Upload Failed: File too large
The upload limit is 1MB. Reduce your tarball size by:
- Excluding unnecessary files
- Not including `node_modules`, `.venv`, or other dependency directories
- Using `.tar.gz` compression

### Upload Failed: Unsupported media type
Ensure your Content-Type header is one of:
- `application/gzip`
- `application/x-tar`
- `application/x-gzip`
- `application/x-compressed-tar`
- `application/octet-stream`

### Automation Not Running
1. Check if the automation is enabled (`enabled: true`)
2. Verify the cron schedule is correct
3. Check for validation errors in the response
