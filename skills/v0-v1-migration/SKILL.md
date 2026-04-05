---
name: v0-v1-migration
description: >
  Comprehensive toolkit for migrating from OpenHands V0 API to V1 API.
  Detects V0 call sites, generates migration plans, provides transformation
  guidance, and includes test fixtures. Use when upgrading API integrations
  before the V0 deprecation deadline (April 1, 2026).
triggers:
  - migrate v0 to v1
  - v0 api migration
  - openhands api migration
  - find v0 api calls
  - v0 to v1
  - api migration plan
  - v0 deprecation
  - deprecated api
---

# V0 to V1 API Migration Assistant

You are helping migrate an OpenHands integration from the deprecated V0 API to V1.

## Quick Context

**Deadline**: V0 API deprecated, removal scheduled for **April 1, 2026**.

**Key Changes in V1**:
1. **Decoupled architecture**: Conversations and sandboxes are independent resources
2. **Async conversation start**: Creation returns a start task; poll or stream for readiness
3. **Agent Server**: File/workspace operations moved to per-sandbox URLs
4. **New endpoints**: `/api/v1/app-conversations`, `/api/v1/sandboxes`, `/api/v1/conversation/{id}/events`

## Migration Workflow

Follow these steps systematically:

### Step 1: Detect V0 API Calls

Scan the codebase for V0 patterns:

```bash
# Find V0 endpoint URLs
grep -rn --include="*.py" --include="*.ts" --include="*.js" --include="*.tsx" --include="*.jsx" \
  -E "/api/conversations[^/]|/api/conversations/[^v]" .

# Find V0-specific field names
grep -rn --include="*.py" --include="*.ts" --include="*.js" \
  -E "initial_user_msg|\"repository\":" .

# Find curl commands with V0 endpoints
grep -rn --include="*.sh" --include="*.md" \
  "/api/conversations" .
```

**V0 Patterns to Identify**:

| Pattern | Type | Example |
|---------|------|---------|
| `/api/conversations` (no `/v1/`) | URL | `POST https://app.all-hands.dev/api/conversations` |
| `initial_user_msg` | Request field | `{"initial_user_msg": "Hello"}` |
| `/api/conversations/{id}/messages` | URL | Send message endpoint |
| `/api/conversations/{id}/list-files` | URL | File listing (moved to Agent Server) |
| `/api/conversations/{id}/select-file` | URL | File download (moved to Agent Server) |

### Step 2: Categorize Each Call Site

For each V0 call found, categorize by complexity:

| Complexity | Description | Examples |
|------------|-------------|----------|
| **Simple** | Path/field rename only | GET conversations, DELETE conversation |
| **Moderate** | Structural changes needed | Create conversation (async), send message (content format) |
| **Complex** | Architecture change | File operations → Agent Server |

### Step 3: Generate Migration Plan

Create a checklist of all changes needed:

```markdown
## Migration Plan for [project-name]

### Summary
- V0 call sites found: X
- Files affected: Y  
- Complexity breakdown: A simple, B moderate, C complex

### Changes Required

#### Simple Changes
- [ ] `src/api.py:42` - Update path `/api/conversations` → `/api/v1/app-conversations/search`
- [ ] `src/api.py:67` - Update path for DELETE

#### Moderate Changes  
- [ ] `src/client.py:15` - Conversation creation: implement async polling
- [ ] `src/client.py:89` - Message format: wrap in content array

#### Complex Changes
- [ ] `src/files.py:23` - File listing: migrate to Agent Server bash command
- [ ] `src/files.py:45` - File download: migrate to Agent Server file endpoint

### Testing Checklist
- [ ] Update unit test mocks for V1 response shapes
- [ ] Verify async conversation flow in integration tests
- [ ] Test Agent Server connectivity and auth
```

### Step 4: Apply Transformations

#### Simple Transformations (Direct Replace)

```python
# Path updates
"/api/conversations"           → "/api/v1/app-conversations/search"  # for listing
"/api/conversations/{id}"      → "/api/v1/app-conversations?id={id}" # for get by ID
"/api/conversations/{id}"      → "/api/v1/app-conversations/{id}"    # for PATCH/DELETE
```

#### Moderate Transformations (Code Changes)

**Conversation Creation (V0 → V1)**:

```python
# ❌ V0 (deprecated) - synchronous
response = requests.post(
    f"{base_url}/api/conversations",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "initial_user_msg": "Check the README",
        "repository": "user/repo"
    }
)
conversation_id = response.json()["conversation_id"]  # Available immediately

# ✅ V1 - asynchronous with polling
response = requests.post(
    f"{base_url}/api/v1/app-conversations",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "initial_message": {
            "content": [{"type": "text", "text": "Check the README"}]
        },
        "selected_repository": "user/repo"
    }
)
start_task_id = response.json()["id"]

# Poll until ready
import time
while True:
    status_response = requests.get(
        f"{base_url}/api/v1/app-conversations/start-tasks?id={start_task_id}",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    status = status_response.json()
    
    if status["status"] == "READY":
        conversation_id = status["conversation_id"]
        sandbox_id = status["sandbox_id"]
        break
    elif status["status"] == "ERROR":
        raise Exception(f"Conversation start failed: {status.get('error')}")
    
    time.sleep(2)  # Poll every 2 seconds
```

**Sending Messages (V0 → V1)**:

```python
# ❌ V0 (deprecated)
requests.post(
    f"{base_url}/api/conversations/{conv_id}/messages",
    json={"message": "Hello world"}
)

# ✅ V1
requests.post(
    f"{base_url}/api/v1/conversation/{conv_id}/events",
    json={
        "content": [{"type": "text", "text": "Hello world"}]
    }
)
```

#### Complex Transformations (Agent Server)

**File Operations** require getting the Agent Server URL first:

```python
# Step 1: Get sandbox info
sandbox_response = requests.get(
    f"{base_url}/api/v1/sandboxes?id={sandbox_id}",
    headers={"Authorization": f"Bearer {api_key}"}
)
sandbox = sandbox_response.json()["results"][0]
agent_server_url = sandbox["exposed_urls"]["AGENT_SERVER"]
session_api_key = sandbox["session_api_key"]

# Step 2: Use Agent Server for file operations
# ❌ V0: GET /api/conversations/{id}/list-files
# ✅ V1: Execute ls command via Agent Server
files_response = requests.post(
    f"{agent_server_url}/api/bash/execute_bash_command",
    headers={"X-Session-API-Key": session_api_key},
    json={"command": "ls -la /workspace"}
)

# ❌ V0: GET /api/conversations/{id}/select-file?file=README.md  
# ✅ V1: Download via Agent Server
file_content = requests.get(
    f"{agent_server_url}/api/file/download/workspace/README.md",
    headers={"X-Session-API-Key": session_api_key}
)
```

### Step 5: Update Tests

Use the fixtures provided in this skill for test data:

- `fixtures/v0/` - Original V0 request/response shapes
- `fixtures/v1/` - New V1 request/response shapes
- `fixtures/mapping.json` - Maps V0 fixtures to V1 equivalents

## Endpoint Quick Reference

| Operation | V0 Endpoint | V1 Endpoint |
|-----------|-------------|-------------|
| Create conversation | `POST /api/conversations` | `POST /api/v1/app-conversations` |
| Check start status | N/A | `GET /api/v1/app-conversations/start-tasks?id={id}` |
| Stream start | `POST /api/conversations/{id}/start` | `POST /api/v1/app-conversations/stream-start` |
| List conversations | `GET /api/conversations` | `GET /api/v1/app-conversations/search` |
| Get conversation | `GET /api/conversations/{id}` | `GET /api/v1/app-conversations?id={id}` |
| Update conversation | `PATCH /api/conversations/{id}` | `PATCH /api/v1/app-conversations/{id}` |
| Delete conversation | `DELETE /api/conversations/{id}` | `DELETE /api/v1/app-conversations/{id}` |
| Send message | `POST /api/conversations/{id}/messages` | `POST /api/v1/conversation/{id}/events` |
| Get events | `GET /api/conversations/{id}/events` | `GET /api/v1/conversation/{id}/events/search` |
| List files | `GET /api/conversations/{id}/list-files` | Agent Server: `POST /api/bash/execute_bash_command` |
| Download file | `GET /api/conversations/{id}/select-file` | Agent Server: `GET /api/file/download/{path}` |
| Upload files | `POST /api/conversations/{id}/upload-files` | Agent Server: `POST /api/file/upload/{path}` |

## Authentication Summary

| API | Header |
|-----|--------|
| App Server (V0 & V1) | `Authorization: Bearer {api_key}` |
| Agent Server | `X-Session-API-Key: {session_api_key}` |

## Resources

**Online Documentation**:
- [Full Migration Guide](https://docs.openhands.dev/openhands/usage/api/migration)
- [V1 API Swagger Docs](https://app.all-hands.dev/docs)
- [V1 API OpenAPI Spec](https://app.all-hands.dev/openapi.json)
- [Agent Server OpenAPI](https://docs.openhands.dev/openhands/usage/api/migration#accessing-agent-server-api-documentation) (requires running sandbox)

**Embedded in This Skill** (in `openapi/` directory, last updated 2026-03-02):
- `app-server.json` - Full App Server OpenAPI spec (V0 + V1 endpoints, ~450KB)
- `agent-server.json` - Agent Server OpenAPI spec (per-sandbox API, ~420KB)

Use these for offline reference, code generation, or building migration tooling.

**If specs seem outdated**, fetch fresh copies:

```bash
# App Server - fetch from live endpoint (no auth required)
curl -s "https://app.all-hands.dev/openapi.json" > openapi/app-server.json

# Agent Server - fetch from a running sandbox
# First get the agent server URL and session key from your sandbox:
curl -s "https://app.all-hands.dev/api/v1/sandboxes?id={sandbox_id}" \
  -H "Authorization: Bearer YOUR_API_KEY"
# Then fetch the spec:
curl -s "{agent_server_url}/openapi.json" \
  -H "X-Session-API-Key: {session_api_key}" > openapi/agent-server.json
```

## Common Pitfalls

1. **Forgetting async handling**: V1 conversation creation is async—always poll or stream
2. **Wrong auth header for Agent Server**: Use `X-Session-API-Key`, not `Authorization: Bearer`
3. **Missing content wrapper**: Messages now use `{"content": [{"type": "text", "text": "..."}]}`
4. **Sandbox vs conversation ID**: V1 has separate IDs; file ops need sandbox_id, not conversation_id
