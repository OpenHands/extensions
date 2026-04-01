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

This skill provides comprehensive API documentation for creating and managing OpenHands automations - scheduled tasks that run your code in sandboxes on a cron schedule.

**Interactive Setup:** For a guided slash command experience, use the [automation-creation plugin](../../plugins/automation-creation/README.md) with `/automation:create`.

**Important:** Automation code must use the [OpenHands Software Agent SDK](https://docs.openhands.dev/sdk) to create conversations and interact with OpenHands Cloud services. See the [SDK Documentation](https://docs.openhands.dev/sdk) for complete API reference.

## API Base URL

All automation endpoints are available through the OpenHands Cloud API:
- **Automations**: `https://app.all-hands.dev/api/automation/v1`
- **Uploads**: `https://app.all-hands.dev/api/automation/v1/uploads`

## Authentication

Use Bearer authentication with your OpenHands API key:

```bash
-H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

The `OPENHANDS_API_KEY` environment variable should be available in your session.

---

## Writing Automation Code

Automations run inside OpenHands Cloud sandboxes and use the **Software Agent SDK** to:
- Create and run AI agent conversations
- Access your configured LLM settings
- Use your stored secrets

**SDK Documentation:** https://docs.openhands.dev/sdk

### Required Dependencies

Your automation must install the OpenHands SDK packages. Use a `setup.sh` script:

```bash
#!/bin/bash
set -e

# Install uv for fast dependency management (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Install the OpenHands SDK packages from PyPI
pip install -q openhands-sdk openhands-workspace openhands-tools
```

### Basic Automation Structure

```python
"""Example automation using the OpenHands SDK."""
import os

from openhands.sdk import Conversation
from openhands.tools.preset.default import get_default_agent
from openhands.workspace import OpenHandsCloudWorkspace

# Environment variables are automatically injected by the dispatcher
api_key = os.environ["OPENHANDS_API_KEY"]
api_url = os.environ["OPENHANDS_CLOUD_API_URL"]

# Use OpenHandsCloudWorkspace to connect to your OpenHands Cloud account
with OpenHandsCloudWorkspace(
    local_agent_server_mode=True,
    cloud_api_url=api_url,
    cloud_api_key=api_key,
) as workspace:
    # Get your configured LLM from OpenHands Cloud
    llm = workspace.get_llm()
    
    # Optionally get your stored secrets
    secrets = workspace.get_secrets()
    
    # Create an agent and conversation
    agent = get_default_agent(llm=llm, cli_mode=True)
    conversation = Conversation(agent=agent, workspace=workspace)
    
    # Inject secrets if available
    if secrets:
        conversation.update_secrets(secrets)
    
    # Send a prompt and run the conversation
    conversation.send_message("Your automation prompt here")
    conversation.run()
    conversation.close()

# The workspace context manager automatically reports completion status
```

---

## Uploading a Tarball

Before creating an automation, you need to upload your code as a tarball. The upload endpoint streams directly to cloud storage with a **1MB size limit**.

### Create a Tarball

```bash
# Create a tarball from your automation code
tar -czf automation.tar.gz -C /path/to/your/code .
```

### Tarball Structure

Your tarball should contain:
```
automation.tar.gz
├── main.py           # Your entrypoint script (uses SDK)
├── setup.sh          # Setup script (REQUIRED: installs uv + SDK)
├── pyproject.toml    # Optional: for uv/poetry dependency management
└── requirements.txt  # Optional: additional dependencies
```

**Note:** The `setup.sh` script is critical - it must install `uv` and the OpenHands SDK packages before your entrypoint runs.

### Upload the Tarball

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/uploads?name=my-automation&description=Weekly%20report%20generator" \
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
curl "https://app.all-hands.dev/api/automation/v1/uploads?limit=10" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Get Upload Details

```bash
curl "https://app.all-hands.dev/api/automation/v1/uploads/{upload_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Delete Upload

```bash
curl -X DELETE "https://app.all-hands.dev/api/automation/v1/uploads/{upload_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

---

## Creating an Automation

Once you have a tarball uploaded (or an external URL), create the automation:

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1" \
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
  "user_id": "...",
  "org_id": "...",
  "name": "Weekly Report Generator",
  "trigger": {
    "type": "cron",
    "schedule": "0 9 * * 1",
    "timezone": "UTC"
  },
  "tarball_path": "oh-internal://uploads/550e8400-e29b-41d4-a716-446655440000",
  "entrypoint": "python main.py",
  "setup_script_path": null,
  "timeout": 300,
  "enabled": true,
  "last_triggered_at": null,
  "created_at": "2025-03-25T10:00:00Z",
  "updated_at": "2025-03-25T10:00:00Z"
}
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
| `AUTOMATION_EVENT_PAYLOAD` | JSON with trigger info, automation ID, and name |
| `SANDBOX_ID` | The sandbox ID where the automation is running |
| `SESSION_API_KEY` | Session API key for sandbox operations |

**Note:** The automation framework automatically handles run completion callbacks. Your script does not need to manage these manually.

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

# Create setup.sh to install dependencies
cat > setup.sh << 'EOF'
#!/bin/bash
set -e
echo "[setup] Installing OpenHands SDK..."
pip install -q openhands-sdk openhands-workspace openhands-tools
echo "[setup] Done"
EOF
chmod +x setup.sh

# Create main.py using the SDK
cat > main.py << 'EOF'
"""Weekly report automation using OpenHands SDK."""
import os
import json

from openhands.sdk import Conversation
from openhands.tools.preset.default import get_default_agent
from openhands.workspace import OpenHandsCloudWorkspace

# Log trigger info
payload = json.loads(os.environ.get('AUTOMATION_EVENT_PAYLOAD', '{}'))
print(f"Running: {payload.get('automation_name')}")

# Connect to OpenHands Cloud
api_key = os.environ["OPENHANDS_API_KEY"]
api_url = os.environ["OPENHANDS_CLOUD_API_URL"]

with OpenHandsCloudWorkspace(
    local_agent_server_mode=True,
    cloud_api_url=api_url,
    cloud_api_key=api_key,
) as workspace:
    llm = workspace.get_llm()
    agent = get_default_agent(llm=llm, cli_mode=True)
    
    conversation = Conversation(agent=agent, workspace=workspace)
    conversation.send_message("Generate a weekly status report and save it to report.txt")
    conversation.run()
    conversation.close()
    
print("Automation completed!")
EOF

# 2. Create the tarball
tar -czf ../my-automation.tar.gz .
cd ..

# 3. Upload the tarball
UPLOAD_RESPONSE=$(curl -s -X POST \
  "https://app.all-hands.dev/api/automation/v1/uploads?name=my-automation" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/gzip" \
  --data-binary @my-automation.tar.gz)

TARBALL_PATH=$(echo "$UPLOAD_RESPONSE" | jq -r '.tarball_path')
echo "Uploaded: $TARBALL_PATH"

# 4. Create the automation
curl -X POST "https://app.all-hands.dev/api/automation/v1" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Weekly Report Generator\",
    \"trigger\": {
      \"type\": \"cron\",
      \"schedule\": \"0 9 * * 1\",
      \"timezone\": \"UTC\"
    },
    \"tarball_path\": \"$TARBALL_PATH\",
    \"entrypoint\": \"python main.py\",
    \"setup_script_path\": \"setup.sh\",
    \"timeout\": 300
  }"
```

For a complete working example, see the [test_tarball](https://github.com/OpenHands/automation/tree/main/scripts/test_tarball) in the automation repository.

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
