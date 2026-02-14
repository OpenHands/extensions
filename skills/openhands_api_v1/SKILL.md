---
name: openhands-api-v1
description: Minimal reference skill for the OpenHands Cloud REST API (V1) (app server /api/v1 + sandbox agent-server). Use when you need to automate common OpenHands Cloud actions; don't use for general sandbox/dev tasks unrelated to the OpenHands API.
triggers:
- openhands-api-v1
- oh-cloud-api
- oh-api
- agent-server
- agent-server-api
---

This skill documents the **OpenHands Cloud API V1** and provides a small, easy-to-copy Python client.

It is intentionally minimal and focused on common operations:

- Defaults to OpenHands Cloud (`https://app.all-hands.dev`).
- Targets the **V1 app server REST API** under `/api/v1/...`.
- Includes a few **agent server** endpoints (inside a sandbox) that use `X-Session-API-Key`.

## Auth

### App server (Cloud)

Use Bearer auth:

- Header: `Authorization: Bearer <OPENHANDS_API_KEY>`
- Env var: `OPENHANDS_API_KEY`

### Agent server (inside a sandbox)

Use session auth:

- Header: `X-Session-API-Key: <session_api_key>`

How to obtain `agent_server_url` and `session_api_key`:

1. Start or fetch an app conversation via the app server (Bearer auth), e.g.:
   - `POST /api/v1/app-conversations`
   - or `GET /api/v1/app-conversations?ids=<conversation_id>`
2. In the returned JSON, look for sandbox/runtime connection fields (names vary slightly by deployment/version). Common patterns:
   - a sandbox object containing `agent_server_url` (or similar)
   - a session key such as `session_api_key` (or similar)
3. Use those values to call the agent server directly:
   - Base: `{agent_server_url}/api/...`
   - Header: `X-Session-API-Key: <session_api_key>`

If those fields are not present on the conversation record, list/search sandboxes (`GET /api/v1/sandboxes/search`) and use the sandbox referenced by the conversation to locate the agent server URL + session key.

## Common V1 app server endpoints

The following are the main endpoints implemented in the minimal client:

- `GET /api/v1/users/me` — validate auth and inspect current account
- `GET /api/v1/app-conversations/search?limit=...` — list recent conversations
- `GET /api/v1/app-conversations?ids=...` — fetch conversation records by id (batch)
- `GET /api/v1/app-conversations/count` — count conversations
- `POST /api/v1/app-conversations` — start a new conversation (creates a sandbox; can incur cost)
- `GET /api/v1/app-conversations/start-tasks?ids=...` — check async start-task status
- `GET /api/v1/conversation/{conversation_id}/events/search?limit=...` — read conversation events
- `GET /api/v1/conversation/{conversation_id}/events/count` — count events
- `GET /api/v1/sandboxes/search?limit=...` — list sandboxes
- `POST /api/v1/sandboxes/{sandbox_id}/pause` / `.../resume` — manage sandbox lifecycle
- `GET /api/v1/app-conversations/{conversation_id}/download` — download trajectory zip

## Common agent server endpoints

These run against `agent_server_url` (not the app server):

- `POST {agent_server_url}/api/bash/execute_bash_command`
- `GET  {agent_server_url}/api/file/download/<absolute_path>`
- `POST {agent_server_url}/api/file/upload/<absolute_path>` (multipart)
- `GET  {agent_server_url}/api/conversations/{conversation_id}/events/search`
- `GET  {agent_server_url}/api/conversations/{conversation_id}/events/count`


### Counting events (recommended approach)

If you need to know how many events a conversation has, you can:

1. **App server count (fastest when working)**
   - `GET /api/v1/conversation/{conversation_id}/events/count`
2. **Agent server count (reliable fallback)**
   - `GET {agent_server_url}/api/conversations/{conversation_id}/events/count`
3. **Trajectory zip fallback (heavier, but still one call + gives full payloads)**
   - `GET /api/v1/app-conversations/{conversation_id}/download`
   - Unzip and count `event_*.json` files

Do **not** rely on the last event `id` to infer the total number of events.
In the agent-server API, event IDs are UUIDs (not monotonically increasing integers).

## Quick start (Python)

```python
from skills.openhands_api_v1.scripts.openhands_api_v1 import OpenHandsV1API

api = OpenHandsV1API()  # uses OPENHANDS_API_KEY

me = api.users_me()
print(me)

recent = api.app_conversations_search(limit=5)
print(recent)

api.close()
```

## CLI examples

Search conversations:

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

## Notes for AI agents extending this client

- Prefer `.../search` endpoints with a small `limit`.
- Avoid loops that could generate many API calls.
- Start conversations only when asked: it may create sandboxes and cost money.
- For sandbox file operations and command execution, use the agent server endpoints with `X-Session-API-Key`.

See also:
- `skills/openhands_api_v1/scripts/openhands_api_v1.py`
- The original inspiration client: `enyst/llm-playground` → `openhands-api-client-v1/scripts/cloud_api_v1.py`
