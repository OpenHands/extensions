# OpenHands Plugin

Unified plugin that bundles all OpenHands capabilities — CLI, REST API, Automations, and Software Agent SDK.

## What's included

| Component | Source | Description |
|---|---|---|
| **CLI integration** | `scripts/run.sh` | Send tasks to Cloud via `openhands cloud` with automatic install and auth |
| **Cloud REST API (V1)** | `skills/openhands-api` | Start/inspect conversations, delegate parallel work, access sandboxes |
| **Automations API** | `skills/openhands-automation` | Create and manage scheduled cron tasks (prompt and plugin presets) |
| **Software Agent SDK** | `skills/openhands-sdk` | Build agents with the Python SDK — custom tools, LLMs, conversations, delegation |

## Quick start

### Via CLI (recommended)

```bash
./scripts/run.sh "Fix the broken login page CSS"
```

The script checks for the `openhands` CLI, installs it if needed, authenticates, sends the task, and opens the resulting conversation URL.

### Via REST API

See `skills/openhands-api` for the full Cloud REST API reference.

### Via Automations

See `skills/openhands-automation` for the full Automations API reference.

## File structure

```
plugins/openhands/
├── SKILL.md                          # Plugin entry point (agent-facing)
├── README.md                         # This file (human-facing)
├── scripts/
│   └── run.sh                        # CLI wrapper (install, auth, send, open)
└── skills/
    ├── openhands-api -> skills/openhands-api         # Cloud REST API skill
    ├── openhands-automation -> skills/openhands-automation  # Automations skill
    └── openhands-sdk -> skills/openhands-sdk         # Software Agent SDK skill
```

## Bundled skills

The individual skills are also usable standalone:

- **`skills/openhands-api`** — Cloud REST API, Python/TypeScript clients, event debugging
- **`skills/openhands-automation`** — Automations presets, CRUD, cron scheduling
- **`skills/openhands-sdk`** — Software Agent SDK: building agents, custom tools, LLM config, sub-agents, MCP, security
