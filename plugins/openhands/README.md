# OpenHands Plugin

Unified plugin for interacting with OpenHands Cloud — via CLI or REST API.

## What's included

| Component | Description |
|---|---|
| **CLI integration** | Send tasks to Cloud via `openhands cloud` with automatic install and auth |
| **Cloud REST API (V1)** | Start/inspect conversations, delegate parallel work, access sandboxes |
| **Automations API** | Create and manage scheduled cron tasks (prompt and plugin presets) |
| **Python client** | Minimal `OpenHandsAPI` class for programmatic access |
| **TypeScript client** | Minimal `OpenHandsAPI` class for Node.js/Deno environments |

## Quick start

### Via CLI (recommended)

```bash
./scripts/run.sh "Fix the broken login page CSS"
```

The script checks for the `openhands` CLI, installs it if needed, authenticates, sends the task, and opens the resulting conversation URL.

### Via REST API

```bash
curl -X POST "https://app.all-hands.dev/api/v1/app-conversations" \
  -H "Authorization: Bearer ${OPENHANDS_CLOUD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"initial_message": {"content": [{"type": "text", "text": "Fix the broken login page CSS"}]}, "selected_repository": "owner/repo"}'
```

### Via Python client

```python
from openhands_api import OpenHandsAPI

api = OpenHandsAPI()
start = api.app_conversation_start(
    initial_message="Fix the broken login page CSS",
    selected_repository="owner/repo",
)
api.close()
```

## File structure

```
plugins/openhands/
├── SKILL.md                          # Plugin entry point (agent-facing)
├── README.md                         # This file (human-facing)
├── scripts/
│   ├── run.sh                        # CLI wrapper (install, auth, send, open)
│   ├── openhands_api.py              # Minimal Python API client
│   └── openhands_api.ts              # Minimal TypeScript API client
└── references/
    ├── cloud-api.md                  # Cloud REST API reference
    ├── automations.md                # Automations API reference
    ├── custom-automation.md          # Custom automations reference (advanced)
    ├── TROUBLESHOOTING.md            # Troubleshooting — common issues and solutions
    └── example_prompt.md             # Example prompt for starting conversations
```

## Replaces

This plugin supersedes the following standalone skills:

- `skills/openhands-api` — Cloud REST API reference
- `skills/automation` — Automations API
- `skills/openhands-cloud` (from [PR #131](https://github.com/OpenHands/extensions/pull/131)) — CLI-based `/openhands-cloud` slash command

All content from those skills has been consolidated here.
