# Custom Automation Reference

> **⚠️ Do NOT use this reference unless the user has explicitly requested a custom automation.** Always use the preset/prompt endpoint from the main SKILL.md first. If the preset approach cannot satisfy the requirement, explain the options to the user and let them decide.

This file contains detailed documentation for creating custom automations with user-provided code, uploads, and entrypoints.

**When to use custom automation (only if the user explicitly chooses this):**
- Full control over the automation code structure is needed
- Custom dependencies or a specific runtime are required
- The user has confirmed that the prompt preset does not meet their requirements

## Table of Contents

1. [Tarball Uploads](#uploading-a-tarball)
2. [Creating Custom Automations](#creating-an-automation)
3. [Managing Automations](#managing-automations)
4. [Writing Automation Code](#writing-automation-code)
5. [Environment Variables](#environment-variables)
6. [Validation Rules](#validation-rules)

---

## Uploading a Tarball

Before creating a custom automation, you need to upload your code as a tarball. The upload endpoint streams directly to cloud storage with a **1MB size limit**.

### Create a Tarball

```bash
tar -czf automation.tar.gz -C /path/to/your/code .
```

### Tarball Structure

```
automation.tar.gz
├── main.py           # Your entrypoint script (uses SDK)
├── setup.sh          # Setup script (REQUIRED: installs uv + SDK)
├── pyproject.toml    # Optional: for uv/poetry dependency management
└── requirements.txt  # Optional: additional dependencies
```

**Note:** The `setup.sh` script is critical - it must install `uv` and the OpenHands SDK packages before your entrypoint runs.

### Upload the Tarball

First, detect the API host from the environment:

```bash
OPENHANDS_HOST="${OH_ALLOW_CORS_ORIGINS_0:-https://app.all-hands.dev}"
```

Then upload:

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/uploads?name=my-automation&description=Weekly%20report%20generator" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/gzip" \
  --data-binary @automation.tar.gz
```

### Upload Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "tarball_path": "oh-internal://uploads/550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "size_bytes": 12345
}
```

**Important:** Save the `tarball_path` value - you'll need it when creating the automation.

### Upload Status Values

| Status | Description |
|--------|-------------|
| `UPLOADING` | Upload in progress |
| `COMPLETED` | Upload successful, `tarball_path` is available |
| `FAILED` | Upload failed, check `error_message` |

---

## Creating an Automation

Once you have a tarball uploaded (or an external URL), create the automation:

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1" \
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
  "trigger": {
    "type": "cron",
    "schedule": "0 9 * * 1",
    "timezone": "UTC"
  },
  "tarball_path": "oh-internal://uploads/550e8400-e29b-41d4-a716-446655440000",
  "entrypoint": "python main.py",
  "enabled": true,
  "created_at": "2025-03-25T10:00:00Z"
}
```

---

## Managing Automations

### List Automations

```bash
curl "${OPENHANDS_HOST}/api/automation/v1?limit=20" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Get Automation Details

```bash
curl "${OPENHANDS_HOST}/api/automation/v1/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Update Automation

```bash
curl -X PATCH "${OPENHANDS_HOST}/api/automation/v1/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### Delete Automation

```bash
curl -X DELETE "${OPENHANDS_HOST}/api/automation/v1/{automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Manually Trigger a Run

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/{automation_id}/dispatch" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### List Automation Runs

```bash
curl "${OPENHANDS_HOST}/api/automation/v1/{automation_id}/runs?limit=20" \
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

# Install the OpenHands SDK packages from PyPI using uv
uv pip install -q openhands-sdk openhands-workspace openhands-tools
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
```

### Sandbox Lifecycle & Conversation Persistence

By default, the sandbox is **kept alive** after the automation run completes. This means:
- Users can view the conversation history in the OpenHands UI after the run
- Users can "continue" or "log into" the conversation to interact further
- The sandbox and its state persist until it times out or is manually deleted

The `Conversation` constructor accepts a `delete_on_close` parameter that controls whether the conversation resources are cleaned up when `close()` is called:

```python
# Default: delete_on_close=False for remote conversations (sandbox kept alive)
conversation = Conversation(agent=agent, workspace=workspace)

# Explicitly keep the conversation alive (same as default for remote)
conversation = Conversation(agent=agent, workspace=workspace, delete_on_close=False)

# Clean up conversation resources on close (sandbox still persists)
conversation = Conversation(agent=agent, workspace=workspace, delete_on_close=True)
```

The `OpenHandsCloudWorkspace` also has a `keep_alive` parameter, but in `local_agent_server_mode=True` (used by automations), sandbox lifecycle is managed by the automation service — not the workspace. The automation service defaults to keeping sandboxes alive.

---

## Environment Variables

Your automation script receives these environment variables:

| Variable | Description |
|----------|-------------|
| `OPENHANDS_API_KEY` | API key for OpenHands services |
| `OPENHANDS_CLOUD_API_URL` | Base URL for the OpenHands Cloud API |
| `AUTOMATION_EVENT_PAYLOAD` | JSON with trigger info, automation ID, and name |
| `SANDBOX_ID` | The sandbox ID where the automation is running |
| `SESSION_API_KEY` | Session API key for sandbox operations |

**Note:** The automation framework automatically handles run completion callbacks.

---

## Validation Rules

- **Name**: 1-500 characters
- **Cron schedule**: Valid 5-field cron expression
- **Entrypoint**: Relative path, no shell metacharacters (`;`, `&`, `|`, etc.)
- **Setup script path**: Relative path, no path traversal (`..`)
- **Timeout**: 1-600 seconds (10 minutes max)
- **Tarball size**: 1MB max for uploads

---

## Complete Example

```bash
# 0. Detect the API host (do this first!)
OPENHANDS_HOST="${OH_ALLOW_CORS_ORIGINS_0:-https://app.all-hands.dev}"

# 1. Create your automation code
mkdir my-automation && cd my-automation

# Create setup.sh
cat > setup.sh << 'EOF'
#!/bin/bash
set -e
pip install -q openhands-sdk openhands-workspace openhands-tools
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

payload = json.loads(os.environ.get('AUTOMATION_EVENT_PAYLOAD', '{}'))
print(f"Running: {payload.get('automation_name')}")

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
    conversation.send_message("Generate a weekly status report")
    conversation.run()
    conversation.close()

print("Automation completed!")
EOF

# 2. Create the tarball
tar -czf ../my-automation.tar.gz .

# 3. Upload the tarball
UPLOAD_RESPONSE=$(curl -s -X POST \
  "${OPENHANDS_HOST}/api/automation/v1/uploads?name=my-automation" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/gzip" \
  --data-binary @my-automation.tar.gz)

TARBALL_PATH=$(echo "$UPLOAD_RESPONSE" | jq -r '.tarball_path')

# 4. Create the automation
curl -X POST "${OPENHANDS_HOST}/api/automation/v1" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Weekly Report Generator\",
    \"trigger\": {\"type\": \"cron\", \"schedule\": \"0 9 * * 1\", \"timezone\": \"UTC\"},
    \"tarball_path\": \"$TARBALL_PATH\",
    \"entrypoint\": \"python main.py\",
    \"setup_script_path\": \"setup.sh\",
    \"timeout\": 300
  }"
```

---

## Troubleshooting

### Upload Failed: File too large
The upload limit is 1MB. Reduce your tarball size by:
- Excluding unnecessary files
- Not including `node_modules`, `.venv`, or other dependency directories

### Automation Not Running
1. Check if the automation is enabled (`enabled: true`)
2. Verify the cron schedule is correct
3. Check for validation errors in the response