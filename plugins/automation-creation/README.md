# Automation Creation Plugin

Create and manage OpenHands automations - scheduled tasks that run SDK scripts in sandboxes on a cron schedule.

## Features

- **Slash command**: `/automation:create` - Create a new automation interactively
- **Tarball uploads**: Upload your SDK code as a tarball (up to 1MB)
- **Cron scheduling**: Schedule automations to run on any cron schedule
- **Configurable timeout**: Set execution timeout (up to 10 minutes)
- **Setup scripts**: Optional setup.sh for environment preparation

## Usage

### Create an Automation

```
/automation:create
```

The agent will guide you through:
1. Uploading your code as a tarball (if needed)
2. Providing a name for your automation
3. Setting up a cron schedule (e.g., `0 9 * * 5` for every Friday at 9 AM)
4. Defining the entrypoint command
5. Optionally setting a timeout and setup script

### Example Interaction

```
User: /automation:create

Agent: I'll help you create a new automation. First, do you:
1. Have local code that needs to be uploaded?
2. Already have a tarball URL (S3, GCS, HTTPS)?

User: I have local code in ./my-automation/

Agent: I'll help you upload that. Let me create and upload the tarball...

[Creates tarball and uploads]

✅ Upload successful!
- Tarball path: oh-internal://uploads/550e8400-e29b-41d4-a716-446655440000

Now let's configure the automation:

1. **Name**: What would you like to call this automation?

User: Weekly Report Generator

Agent: 2. **Cron Schedule**: When should this run? (e.g., "0 9 * * 5" for Fridays at 9 AM UTC)

User: 0 9 * * 1

Agent: 3. **Entrypoint**: What command runs your automation? (e.g., "uv run main.py")

User: python generate_report.py

Agent: Creating your automation...

✅ Automation created successfully!
- ID: 123e4567-e89b-12d3-a456-426614174000
- Name: Weekly Report Generator
- Schedule: Every Monday at 9:00 AM UTC
- Status: Enabled
```

---

## API Base URL

All automation endpoints are available through the OpenHands Cloud API:
- **Automations**: `https://app.all-hands.dev/api/automation/v1`
- **Uploads**: `https://app.all-hands.dev/api/automation/v1/uploads`

---

## Uploading Tarballs

Before creating an automation with local code, you must upload it as a tarball.

### Upload Endpoint

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/uploads?name=my-code&description=My%20automation%20code" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/gzip" \
  --data-binary @automation.tar.gz
```

### Upload Constraints

| Constraint | Value |
|------------|-------|
| Max file size | 1 MB |
| Content types | `application/gzip`, `application/x-tar`, `application/x-gzip`, `application/x-compressed-tar`, `application/octet-stream` |

### Upload Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "...",
  "org_id": "...",
  "name": "my-code",
  "description": "My automation code",
  "status": "COMPLETED",
  "error_message": null,
  "size_bytes": 12345,
  "tarball_path": "oh-internal://uploads/550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-03-25T10:00:00Z",
  "updated_at": "2025-03-25T10:00:00Z"
}
```

**Important:** Use the `tarball_path` value when creating your automation.

### List Uploads

```bash
curl "https://app.all-hands.dev/api/automation/v1/uploads" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Delete Upload

```bash
curl -X DELETE "https://app.all-hands.dev/api/automation/v1/uploads/{upload_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

---

## Automation API Reference

The automation service exposes a REST API at `https://app.all-hands.dev/api/automation/v1`:

### Create Automation

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Automation",
    "trigger": {
      "type": "cron",
      "schedule": "0 9 * * 5",
      "timezone": "UTC"
    },
    "tarball_path": "s3://bucket/code.tar.gz",
    "entrypoint": "uv run main.py",
    "timeout": 300
  }'
```

### Request Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Name of the automation (1-500 characters) |
| `trigger.type` | Yes | Must be `"cron"` |
| `trigger.schedule` | Yes | Cron expression (e.g., `"0 9 * * 5"`) |
| `trigger.timezone` | No | IANA timezone (default: `"UTC"`) |
| `tarball_path` | Yes | Path to code tarball (`oh-internal://`, `s3://`, `gs://`, `https://`) |
| `entrypoint` | Yes | Command to execute (e.g., `"uv run main.py"`) |
| `setup_script_path` | No | Relative path to setup script inside tarball |
| `timeout` | No | Max execution time in seconds (1-600, default: 600) |

### List Automations

```bash
curl "https://app.all-hands.dev/api/automation/v1" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### Update Automation

```bash
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/{id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false
  }'
```

### Manually Trigger a Run

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/{id}/dispatch" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

### List Automation Runs

```bash
curl "https://app.all-hands.dev/api/automation/v1/{id}/runs" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

## Cron Schedule Examples

| Schedule | Description |
|----------|-------------|
| `0 9 * * *` | Every day at 9:00 AM |
| `0 9 * * 1` | Every Monday at 9:00 AM |
| `0 9 * * 5` | Every Friday at 9:00 AM |
| `0 0 1 * *` | First day of each month at midnight |
| `*/15 * * * *` | Every 15 minutes |
| `0 */6 * * *` | Every 6 hours |

## Writing Automation Code

Automations must use the **OpenHands Software Agent SDK** to create conversations and interact with OpenHands Cloud.

**SDK Documentation:** https://docs.openhands.dev/sdk

### Tarball Structure

Your automation tarball should contain:

```
my-automation/
├── main.py           # Your entrypoint script (uses SDK)
├── setup.sh          # REQUIRED: installs SDK dependencies
├── pyproject.toml    # Optional: for uv/poetry
└── requirements.txt  # Optional: additional dependencies
```

### Setup Script (Required)

Your `setup.sh` must install the OpenHands SDK packages:

```bash
#!/bin/bash
set -e
pip install openhands-sdk openhands-workspace openhands-tools
```

### Example Entrypoint

```python
import os
from openhands.sdk import Conversation
from openhands.tools.preset.default import get_default_agent
from openhands.workspace import OpenHandsCloudWorkspace

with OpenHandsCloudWorkspace(
    local_agent_server_mode=True,
    cloud_api_url=os.environ["OPENHANDS_CLOUD_API_URL"],
    cloud_api_key=os.environ["OPENHANDS_API_KEY"],
) as workspace:
    llm = workspace.get_llm()
    agent = get_default_agent(llm=llm, cli_mode=True)
    
    conversation = Conversation(agent=agent, workspace=workspace)
    conversation.send_message("Your automation prompt")
    conversation.run()
    conversation.close()
```

For a complete working example, see the [test_tarball](https://github.com/OpenHands/automation/tree/main/scripts/test_tarball) in the automation repository.

### Environment Variables

Your script receives these environment variables:

| Variable | Description |
|----------|-------------|
| `OPENHANDS_API_KEY` | API key for OpenHands services |
| `OPENHANDS_CLOUD_API_URL` | Base URL for the OpenHands Cloud API |
| `AUTOMATION_EVENT_PAYLOAD` | JSON with trigger info, automation ID, and name |
| `SANDBOX_ID` | The sandbox ID where the automation is running |
| `SESSION_API_KEY` | Session API key for sandbox operations |

**Note:** The automation framework automatically handles run completion callbacks.

## Validation Rules

- **Name**: 1-500 characters, required
- **Cron schedule**: Must be a valid cron expression
- **Entrypoint**: Must be a relative path, no shell metacharacters (`;&|` etc.)
- **Setup script path**: Must be relative, no path traversal (`..`)
- **Timeout**: 1-600 seconds (10 minutes max)

## Plugin Structure

```
automation-creation/
├── .claude-plugin/
│   └── plugin.json      # Plugin manifest
├── commands/
│   └── create.md        # Slash command definition
└── README.md            # This file
```

## Related Resources

- [OpenHands SDK Documentation](https://docs.openhands.dev/sdk)
- [OpenHands Cloud](https://app.all-hands.dev)
- [Cron Expression Reference](https://crontab.guru/)
