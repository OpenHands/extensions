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

First, determine the API host. Look for a `<HOST>` value in the system prompt. If present, use that URL. Otherwise, default to `https://app.all-hands.dev`.

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

### How Execution Works

When a run is triggered, the automation service uploads your tarball to the agent server, which unpacks it, runs `setup.sh` to install dependencies, then executes your entrypoint. Your script therefore runs **inside the agent server** — not in a separate process.

The agent server exposes an HTTP API (at `OH_INTERNAL_SERVER_URL`) for managing conversations. A **conversation** is an AI agent interaction that can use tools: bash commands, file editing, web browsing, and so on. Your script uses the SDK's `RemoteWorkspace` (pointing to `OH_INTERNAL_SERVER_URL`) to start, monitor, and stop conversations running in that same agent server.

Key points:
- **Your script and its conversations share the same agent server.** There is no network hop to a remote service.
- **Conversations are asynchronous.** You can fire one and continue, fire several concurrently, or start none at all (e.g. if your script fetches external data and decides no action is needed).
- **The completion callback** is sent by `RemoteWorkspace.__exit__` when the `with` block exits, telling the automation service the run is done. For async patterns, defer exiting until the conversation is in the desired state.
- **LLM config and secrets** are fetched from the agent server (`workspace.get_llm()`, `workspace.get_secrets()`), so your script does not need to supply its own credentials.

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
from openhands.sdk.workspace import RemoteWorkspace
from openhands.tools.preset.default import get_default_agent

# OH_INTERNAL_SERVER_URL points to the agent server this script is running inside.
# SESSION_API_KEY / OH_SESSION_API_KEYS_0 authenticate against that server.
api_key = os.environ.get("SESSION_API_KEY") or os.environ.get("OH_SESSION_API_KEYS_0", "")
host = os.environ.get("OH_INTERNAL_SERVER_URL", "http://localhost:60000")

# RemoteWorkspace connects back to the agent server to manage conversations.
# __exit__ sends the completion callback to the automation service.
with RemoteWorkspace(
    host=host,
    api_key=api_key,
    working_dir="/workspace",
) as workspace:
    # LLM config and secrets come from the agent server's persisted settings —
    # no credentials need to be embedded in the script.
    llm = workspace.get_llm()
    secrets = workspace.get_secrets()

    # Start a conversation (AI agent with tool access) in the agent server.
    agent = get_default_agent(llm=llm, cli_mode=True)
    conversation = Conversation(agent=agent, workspace=workspace)

    if secrets:
        conversation.update_secrets(secrets)

    # Run the conversation synchronously and wait for it to finish.
    conversation.send_message("Your automation prompt here")
    conversation.run()
    conversation.close()
# RemoteWorkspace.__exit__ fires the completion callback here.
```

### Conversation Persistence

Conversations started during a run remain accessible in the OpenHands UI after the run completes — users can view the history and continue interacting. By default, `Conversation` does not delete the conversation on close:

```python
# Default: conversation persists after close (users can view/continue it)
conversation = Conversation(agent=agent, workspace=workspace)

# Explicitly persist (same as default)
conversation = Conversation(agent=agent, workspace=workspace, delete_on_close=False)

# Delete conversation resources on close
conversation = Conversation(agent=agent, workspace=workspace, delete_on_close=True)
```

The agent server itself persists until it times out or is manually deleted; this is managed by the automation service, not by the workspace.

### Conversation Patterns

#### Pattern 1: Synchronous (run and wait)

The simplest pattern — start a conversation, block until it finishes, then exit (firing the callback).

```python
conversation.send_message("Analyze the latest deployment logs and summarise any errors")
conversation.run()   # blocks until the agent finishes or times out
conversation.close()
```

#### Pattern 2: Conditional (fetch data first, then decide)

A common pattern where the script queries an external source and only starts a conversation if needed.

```python
import httpx

response = httpx.get("https://api.example.com/alerts", headers={"Authorization": f"Bearer {token}"})
alerts = response.json().get("alerts", [])

if not alerts:
    print("No alerts — nothing to do.")
else:
    # Only now do we spin up an agent conversation
    with RemoteWorkspace(host=host, api_key=api_key, working_dir="/workspace") as workspace:
        llm = workspace.get_llm()
        agent = get_default_agent(llm=llm, cli_mode=True)
        conversation = Conversation(agent=agent, workspace=workspace)
        conversation.send_message(f"Investigate these alerts and open GitHub issues: {alerts}")
        conversation.run()
        conversation.close()
```

#### Pattern 3: Wait for conversation completion (polling)

Start a conversation without blocking, do other work, then poll until the conversation reaches a terminal state before exiting. The callback fires only after the conversation is done.

`ConversationExecutionStatus.is_terminal()` returns `True` for `FINISHED`, `ERROR`, and `STUCK`. Call `refresh_from_server()` before checking status — `execution_status` uses a cached value and won't update automatically.

```python
import time
from openhands.sdk.conversation.state import ConversationExecutionStatus

with RemoteWorkspace(host=host, api_key=api_key, working_dir="/workspace") as workspace:
    llm = workspace.get_llm()
    agent = get_default_agent(llm=llm, cli_mode=True)
    conversation = Conversation(agent=agent, workspace=workspace)
    conversation.send_message("Run a long analysis task")
    # Conversation is now running asynchronously in the agent server.

    # Do other work here while conversation runs...

    # Wait until the conversation reaches a terminal state.
    while True:
        time.sleep(5)
        conversation.refresh_from_server()
        if conversation.execution_status.is_terminal():
            break

    conversation.close()
# Callback fires here — after the conversation has finished.
```

#### Pattern 4: Deferred callback via stop hook

For cases where the automation script needs to exit while a conversation is still running, use a `stop` hook to fire the completion callback from within the agent server when the conversation finishes.

The `stop` hook runs a shell command when the agent stops. The agent server's environment includes `AUTOMATION_CALLBACK_URL`, `AUTOMATION_CALLBACK_API_KEY`, and `AUTOMATION_RUN_ID`, so the hook can call the automation service directly.

```python
from openhands.sdk.hooks import HookConfig, HookDefinition, HookMatcher

# Shell command that fires the completion callback when the agent stops.
# Runs inside the agent server — env vars are available at hook execution time.
stop_hook = HookConfig(
    stop=[
        HookMatcher(hooks=[
            HookDefinition(
                command=(
                    'curl -sf -X POST "$AUTOMATION_CALLBACK_URL" '
                    '-H "Authorization: Bearer $AUTOMATION_CALLBACK_API_KEY" '
                    '-H "Content-Type: application/json" '
                    '-d \'{"status":"COMPLETED","run_id":"$AUTOMATION_RUN_ID"}\' || true'
                )
            )
        ])
    ]
)

with RemoteWorkspace(host=host, api_key=api_key, working_dir="/workspace") as workspace:
    llm = workspace.get_llm()
    agent = get_default_agent(llm=llm, cli_mode=True)
    conversation = Conversation(agent=agent, workspace=workspace, hook_config=stop_hook)
    conversation.send_message("Do some long-running work")
    # Don't call run() — the conversation runs asynchronously.
    # When the agent stops, the stop hook will fire the callback.
# RemoteWorkspace.__exit__ also fires a callback here (on script exit).
# The automation service should handle receiving two callbacks for the same run.
```

> **Note:** When using the stop hook pattern, the automation service receives two completion callbacks — one from `RemoteWorkspace.__exit__` when the script exits, and one from the stop hook when the conversation finishes. Ensure your automation service handles duplicate callbacks gracefully.

---

## Environment Variables

The automation service injects these environment variables into every run:

| Variable | Alt name | Description |
|----------|----------|-------------|
| `OH_INTERNAL_SERVER_URL` | — | URL of the agent server the script is running inside. Use as `host` for `RemoteWorkspace` (fallback: `http://localhost:60000`) |
| `OH_SESSION_API_KEYS_0` | `SESSION_API_KEY` | Session API key for authenticating with the agent server. Use as `api_key` for `RemoteWorkspace` |
| `AUTOMATION_EVENT_PAYLOAD` | — | JSON object with trigger context: `automation_id`, `automation_name`, `trigger` type, and (for webhook runs) the raw event payload |
| `AUTOMATION_CALLBACK_URL` | — | URL that `RemoteWorkspace.__exit__` POSTs to, marking the run complete. Also available to stop hooks for deferred callbacks |
| `AUTOMATION_CALLBACK_API_KEY` | — | Bearer token for authenticating the completion callback POST |
| `AUTOMATION_RUN_ID` | — | Unique ID for this run, included in the completion callback payload |

> **Note:** `OH_*` variable names are used in local/dev deployments; the plain aliases (`SESSION_API_KEY`) are used in cloud deployments. Always read both with `.get()` — see the code examples above.

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
# 0. Set the API host (use value from <HOST> in system prompt, or default)
OPENHANDS_HOST="https://app.all-hands.dev"

# 1. Create your automation code
mkdir my-automation && cd my-automation

# Create setup.sh
cat > setup.sh << 'EOF'
#!/bin/bash
set -e
uv venv .venv --quiet
uv pip install --quiet \
  openhands-sdk \
  openhands-workspace \
  openhands-tools
EOF
chmod +x setup.sh

# Create main.py using the SDK
cat > main.py << 'EOF'
"""Weekly report automation using OpenHands SDK."""
import os
import json

from openhands.sdk import Conversation
from openhands.sdk.workspace import RemoteWorkspace
from openhands.tools.preset.default import get_default_agent

payload = json.loads(os.environ.get('AUTOMATION_EVENT_PAYLOAD', '{}'))
print(f"Running: {payload.get('automation_name')}")

api_key = os.environ.get("SESSION_API_KEY") or os.environ.get("OH_SESSION_API_KEYS_0", "")
host = os.environ.get("OH_INTERNAL_SERVER_URL", "http://localhost:60000")

with RemoteWorkspace(
    host=host,
    api_key=api_key,
    working_dir="/workspace",
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
    \"entrypoint\": \".venv/bin/python main.py\",
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