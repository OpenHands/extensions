# openhands_api_v1 (OpenHands Cloud API V1)

Use this skill when you want to automate OpenHands Cloud using the **V1 app server API** (`/api/v1/...`) and, when needed, interact with a running sandbox through the **agent server API** (`{agent_server_url}/api/...`).

This directory includes:
- **Documentation**: [`SKILL.md`](./SKILL.md)
- **Minimal Python client**: [`scripts/openhands_api_v1.py`](./scripts/openhands_api_v1.py)

## Key concepts

### Two APIs, two auth mechanisms

1. **App server (Cloud)**
   - Base: `https://app.all-hands.dev`
   - Auth: `Authorization: Bearer $OPENHANDS_API_KEY`
   - Use it to start/list conversations, manage sandboxes, download trajectories.

2. **Agent server (inside a sandbox)**
   - Base: `agent_server_url` returned by the app server
   - Auth: `X-Session-API-Key: <session_api_key>`
   - Use it to run commands and upload/download files in the sandbox.

## Quick start

```bash
export OPENHANDS_API_KEY="..."
python skills/openhands_api_v1/scripts/openhands_api_v1.py search-conversations --limit 5
```

Start a conversation from a prompt file:

```bash
python skills/openhands_api_v1/scripts/openhands_api_v1.py start-conversation \
  --prompt-file skills/openhands_api/references/example_prompt.md \
  --repo owner/repo \
  --branch main
```

## When to use V0 instead

If you specifically need the legacy `/api/conversations` endpoints (V0), use:
- [`../openhands_api/`](../openhands_api/)
