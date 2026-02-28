---
name: openhands-api-v1
description: Minimal reference skill for the OpenHands Cloud REST API (V1) (app server /api/v1 + sandbox agent-server). Use when you need to automate common OpenHands Cloud actions; don't use for general sandbox/dev tasks unrelated to the OpenHands API.
triggers:
- openhands-api-v1
- openhands api v1
- openhands cloud api v1
- openhands cloud api
- conversation events
- agent-server
- X-Session-API-Key
- session_api_key
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

Example (common field names; adjust to your deployment):

```python
# using the minimal Python client (`OpenHandsV1API`)
conv = api.app_conversation_get(app_conversation_id)

session_api_key = conv.get("session_api_key")
conversation_url = conv.get("conversation_url", "")

# `conversation_url` often looks like: https://<runtime-host>/api/conversations/<id>
agent_server_url = conversation_url.rsplit("/api/conversations", 1)[0]
```


If those fields are not present on the conversation record, list/search sandboxes (`GET /api/v1/sandboxes/search`) and use the sandbox referenced by the conversation to locate the agent server URL + session key.

## Common V1 app server endpoints

The following are the main endpoints implemented in the minimal client:

- `GET /api/v1/users/me` — validate auth and inspect current account
- `GET /api/v1/app-conversations/search?limit=...` — list recent conversations
- `GET /api/v1/app-conversations?ids=...` — fetch conversation records by id (batch)
- `GET /api/v1/app-conversations/count` — count conversations
- `POST /api/v1/app-conversations` — start a new conversation (creates a sandbox)
- `GET /api/v1/app-conversations/start-tasks?ids=...` — check async start-task status
- `GET /api/v1/conversation/{app_conversation_id}/events/search?limit=...` — read conversation events
- `GET /api/v1/conversation/{app_conversation_id}/events/count` — count events
- `GET /api/v1/sandboxes/search?limit=...` — list sandboxes
- `POST /api/v1/sandboxes/{sandbox_id}/pause` / `.../resume` — manage sandbox lifecycle
- `GET /api/v1/app-conversations/{app_conversation_id}/download` — download trajectory zip

### Start-task vs `app_conversation_id` (common pitfall)

In many deployments, `POST /api/v1/app-conversations` is **asynchronous** and returns a **start-task** object:

- `id` is the **start_task_id**
- `app_conversation_id` is the id you should use for conversation operations like:
  - `GET /api/v1/app-conversations/{app_conversation_id}/download`
  - `GET /api/v1/conversation/{app_conversation_id}/events/...`

If `app_conversation_id` is not present in the initial response, fetch it via:

- `GET /api/v1/app-conversations/start-tasks?ids=<start_task_id>`

If you pass a **start_task_id** to `/download`, you will get `404 Not Found`.

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
   - `GET /api/v1/conversation/{app_conversation_id}/events/count`
2. **Agent server count (reliable fallback)**
   - `GET {agent_server_url}/api/conversations/{app_conversation_id}/events/count`
3. **Trajectory zip fallback (heavier, but still one call + gives full payloads)**
   - `GET /api/v1/app-conversations/{app_conversation_id}/download`
   - Unzip and count `event_*.json` files

Do **not** rely on the last event `id` to infer the total number of events.
In the agent-server API, event IDs are UUIDs (not monotonically increasing integers).

## Troubleshooting

For common issues and solutions, see [TROUBLESHOOTING.md](references/TROUBLESHOOTING.md).

## Event structure (for debugging)

Events returned by:

- app server: `GET /api/v1/conversation/{id}/events/search`
- agent server: `GET {agent_server_url}/api/conversations/{id}/events/search`

…share the same high-level shape.

Each event typically includes:

- `id` (UUID)
- `timestamp`
- `kind`
- `source`

Common `kind` values:

| kind | source (typical) | key fields (common) | purpose |
|---|---|---|---|
| `ActionEvent` | `agent` | `tool_name`, `tool_call_id`, `action` | tool call requested by the agent |
| `ObservationEvent` | `environment` | `tool_name`, `tool_call_id`, `action_id`, `observation` | tool result produced by the sandbox/environment |
| `MessageEvent` | `user` / `assistant` | `message` (or similar) | user/assistant chat messages |
| `ConversationStateUpdateEvent` | `environment` | `key`, `value` | state transitions/metadata |

Linking tool calls:

- `ActionEvent.tool_call_id` == `ObservationEvent.tool_call_id`
- `ObservationEvent.action_id` == `ActionEvent.id`

Example (simplified):

```json
{
  "id": "<action-event-uuid>",
  "kind": "ActionEvent",
  "source": "agent",
  "tool_name": "terminal",
  "tool_call_id": "toolu_...",
  "action": {"command": "ls"}
}
```

```json
{
  "id": "<observation-event-uuid>",
  "kind": "ObservationEvent",
  "source": "environment",
  "tool_name": "terminal",
  "tool_call_id": "toolu_...",
  "action_id": "<action-event-uuid>",
  "observation": {"exit_code": 0, "stdout": "..."}
}
```

## Debugging one-liners (events)

These assume you're querying the **app server** endpoint. For agent-server queries, swap the URL base + use `X-Session-API-Key`.

### Print a quick timeline

```bash
curl -s "${BASE_URL:-https://app.all-hands.dev}/api/v1/conversation/${APP_CONVERSATION_ID}/events/search?limit=100" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Accept: application/json" | \
python3 - <<'PY'
import json, sys
items = (json.load(sys.stdin) or {}).get("items", [])
for i, e in enumerate(items):
    print(f"{i:04d}  {e.get('timestamp','')}  {e.get('source','')}  {e.get('kind','')}")
PY
```

### Find error-like events

```bash
curl -s "${BASE_URL:-https://app.all-hands.dev}/api/v1/conversation/${APP_CONVERSATION_ID}/events/search?limit=200" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Accept: application/json" | \
python3 - <<'PY'
import json, sys
items = (json.load(sys.stdin) or {}).get("items", [])
for i, e in enumerate(items):
    if e.get("kind") == "ErrorEvent" or ("code" in e and "detail" in e):
        print(i, e.get("kind"), e.get("code"), str(e.get("detail", ""))[:400])
PY
```

### Check tool-call matching (unmatched actions / duplicate observations)

```bash
curl -s "${BASE_URL:-https://app.all-hands.dev}/api/v1/conversation/${APP_CONVERSATION_ID}/events/search?limit=200" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Accept: application/json" | \
python3 - <<'PY'
import json, sys
from collections import Counter
items = (json.load(sys.stdin) or {}).get("items", [])
action_ids = {e.get("id") for e in items if e.get("kind") == "ActionEvent"}
obs_action_ids = [e.get("action_id") for e in items if e.get("kind") == "ObservationEvent" and e.get("action_id")]
observed = set(obs_action_ids)
print("actions:", len(action_ids))
print("observations:", len(observed))
unmatched = action_ids - observed
print("unmatched actions:", list(unmatched)[:20] if unmatched else "none")
dups = [aid for aid, c in Counter(obs_action_ids).items() if c > 1]
print("duplicate observation action_ids:", list(dups)[:20] if dups else "none")
PY
```


## Quick start (Python)

```python
# Copy `skills/openhands-api-v1/scripts/openhands_api_v1.py` into your project (e.g. as `openhands_api_v1.py`),
# then import it normally:
from openhands_api_v1 import OpenHandsV1API

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
python skills/openhands-api-v1/scripts/openhands_api_v1.py search-conversations --limit 5
```

Start a conversation from a prompt file:

```bash
python skills/openhands-api-v1/scripts/openhands_api_v1.py start-conversation \
  --prompt-file skills/openhands-api-v1/references/example_prompt.md \
  --repo owner/repo \
  --branch main
```

## Notes for AI agents extending this client

- Prefer `.../search` endpoints with a small `limit`.
- Avoid loops that could generate many API calls.
- Start conversations only when asked: it may create sandboxes and cost money.
- For sandbox file operations and command execution, use the agent server endpoints with `X-Session-API-Key`.

See also:
- `skills/openhands-api-v1/scripts/openhands_api_v1.py`
- The original inspiration client: `enyst/llm-playground` → `openhands-api-client-v1/scripts/cloud_api_v1.py`
- Troubleshooting content and real-world usage feedback → `https://github.com/jpshackelford/.openhands/`
