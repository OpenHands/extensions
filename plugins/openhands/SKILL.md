---
name: openhands
description: >-
  Unified OpenHands plugin — interact with OpenHands Cloud via CLI or REST API.
  Send tasks, manage conversations, create automations, and delegate work to
  parallel agents. Covers the CLI, the V1 Cloud API, and the Automations API.
triggers:
- openhands-cloud
- openhands-api
- openhands-api-v1
- oh-api-v1
- oh-cloud-api-v1
- openhands-cloud-api-v1
- /openhands-cloud
- automation
- automations
- scheduled task
- cron job
- cron schedule
- /automation:create
---

# OpenHands — Cloud, API & Automations

This plugin is the single entry point for everything OpenHands Cloud:

| Capability | When to use | Reference |
|---|---|---|
| **CLI** (`openhands cloud`) | Send a task to Cloud and get a conversation URL | [scripts/run.sh](scripts/run.sh) |
| **Cloud REST API (V1)** | Start/inspect conversations, delegate work, access sandboxes | [references/cloud-api.md](references/cloud-api.md) |
| **Automations API** | Create and manage scheduled cron tasks | [references/automations.md](references/automations.md) |

## Authentication — try CLI first

1. **Check if the OpenHands CLI is installed:**

```bash
command -v openhands &>/dev/null && echo "CLI available" || echo "CLI not found"
```

2. **If CLI is available**, use it — it manages auth and API keys automatically.
3. **If CLI is not available**, check for an API key:
   - Preferred env var: `OPENHANDS_CLOUD_API_KEY`
   - Backward-compatible: `OPENHANDS_API_KEY`
   - Header: `Authorization: Bearer <key>`
4. **If neither exists**, ask the user whether they'd like to install the CLI:
   ```bash
   uv tool install openhands --python 3.12
   openhands cloud  # starts auth flow
   ```

## Quick start — send a task via CLI

```bash
./scripts/run.sh "Investigate flaky tests in tests/test_api.py"
```

The script checks for the CLI, installs it if needed, sends the task, and opens the resulting conversation URL.

If the script exits with code `2` (`AUTH_REQUIRED`), ask the user to complete authentication in the browser, then re-run.

## Quick start — send a task via REST API

```bash
curl -X POST "https://app.all-hands.dev/api/v1/app-conversations" \
  -H "Authorization: Bearer ${OPENHANDS_CLOUD_API_KEY:-$OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "initial_message": {
      "content": [{"type": "text", "text": "Fix the broken login page CSS"}]
    },
    "selected_repository": "owner/repo"
  }'
```

For the full API reference (endpoints, polling, delegation, events), see [references/cloud-api.md](references/cloud-api.md).

## Quick start — create an automation

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/preset/prompt" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Report",
    "prompt": "Generate a daily status report summarizing GitHub activity",
    "trigger": {"type": "cron", "schedule": "0 9 * * 1-5", "timezone": "America/New_York"}
  }'
```

For full automations docs (presets, plugins, management, custom automations), see [references/automations.md](references/automations.md).

## Python / TypeScript clients

Minimal API clients are in `scripts/`:
- **Python**: `scripts/openhands_api.py` — importable `OpenHandsAPI` class
- **TypeScript**: `scripts/openhands_api.ts` — importable `OpenHandsAPI` class

```python
from openhands_api import OpenHandsAPI

api = OpenHandsAPI()  # prefers OPENHANDS_CLOUD_API_KEY
me = api.users_me()
start = api.app_conversation_start(
    initial_message="Fix the flaky test",
    selected_repository="owner/repo",
)
api.close()
```

## Reference files

| File | Contents |
|---|---|
| [references/cloud-api.md](references/cloud-api.md) | Full V1 Cloud API — endpoints, auth, delegation, events, debugging |
| [references/automations.md](references/automations.md) | Automations API — presets, CRUD, cron, plugin preset |
| [references/custom-automation.md](references/custom-automation.md) | Custom SDK automations (advanced — tarball uploads, env vars) |
| [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md) | Common issues and solutions |
| [scripts/run.sh](scripts/run.sh) | CLI wrapper — install, auth, send task, open URL |
| [scripts/openhands_api.py](scripts/openhands_api.py) | Minimal Python client |
| [scripts/openhands_api.ts](scripts/openhands_api.ts) | Minimal TypeScript client |
