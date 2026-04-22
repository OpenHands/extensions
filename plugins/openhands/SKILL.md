---
name: openhands
description: >-
  Unified OpenHands plugin — bundles the OpenHands Cloud CLI, Cloud REST API
  (openhands-api), and Automations (openhands-automation) into a single plugin.
  Use this when you need to interact with OpenHands Cloud in any way.
triggers:
- /openhands-cloud
---

# OpenHands — Cloud, API & Automations

This plugin bundles all OpenHands Cloud capabilities under one roof:

| Capability | Skill | When to use |
|---|---|---|
| **CLI** (`openhands cloud`) | — (plugin-only) | Send a task to Cloud and get a conversation URL |
| **Cloud REST API (V1)** | `openhands-api` | Start/inspect conversations, delegate work, access sandboxes |
| **Automations API** | `openhands-automation` | Create and manage scheduled cron tasks |

Each capability is also available as a standalone skill under `skills/`.
This plugin provides a unified entry point and the CLI integration script.

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

## Bundled skills

For full API references, see the individual skills:

- **`skills/openhands-api`** — Cloud REST API: endpoints, polling, delegation, events, debugging, Python/TypeScript clients
- **`skills/openhands-automation`** — Automations API: presets, CRUD, cron schedules, plugin preset, custom automations
