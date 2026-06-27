---
name: agent-canvas-environment
description: Work effectively inside a local Agent Canvas environment, including local agent-server auth, frontend/backend port discovery, safe workspace hygiene, and delegating work to a new local conversation through POST /api/conversations.
triggers:
- agent canvas
- agent-canvas
- local conversation
- delegate local conversation
- session api key
- X-Session-API-Key
- localhost:8001
---

# Agent Canvas Environment

Use this skill when running inside or alongside a local Agent Canvas stack, especially when the user asks to inspect the local backend, create or monitor local conversations, or delegate work to another local conversation.

## Core rules

- Treat the local Agent Canvas backend as an agent-server API, usually `http://localhost:8001`.
- Treat the local UI as a separate frontend, usually `http://localhost:8000`.
- Do not print session API keys. Pass them directly in `X-Session-API-Key`.
- Trust any runtime-services block or explicit user-provided host over default ports.
- Before mutating a repository, check `git status -sb`. If a worktree has unrelated changes, use a separate worktree or clone.
- When delegating, write a self-contained prompt. The new conversation does not inherit the current chat context.

## Find the session key

Use the first available value, without echoing it:

```bash
KEY="${SESSION_API_KEY:-${OH_SESSION_API_KEYS_0:-${LOCAL_BACKEND_API_KEY:-}}}"
if [ -z "$KEY" ] && [ -f "$HOME/.openhands/agent-canvas/api-key.txt" ]; then
  KEY="$(tr -d '\n' < "$HOME/.openhands/agent-canvas/api-key.txt")"
fi
test -n "$KEY" || { echo "No Agent Canvas session API key found" >&2; exit 1; }
```

Validate backend access:

```bash
curl -sS -o /tmp/agent-canvas-conversations.json -w '%{http_code}\n' \
  -H "X-Session-API-Key: $KEY" \
  http://localhost:8001/api/conversations/search
```

HTTP `200` means the backend and key work.

## Delegate to a local conversation

Use `POST /api/conversations` with:

- `agent_settings` carrying `agent_kind`, the tool set, and an `llm` whose `api_key` is the **encrypted Fernet token** from the active LLM profile file
- `secrets_encrypted: true` so the agent-server decrypts that token server-side
- `tool_module_qualnames` for any non-SDK tools (e.g. `canvas_ui`)
- a fresh absolute workspace directory
- `initial_message.run: true`
- `worktree: false` when the workspace is already isolated

### Credential handling — important

`GET /api/settings`, `GET /api/agent-profiles`, and `GET /api/profiles/{name}` **mask** every credential (e.g. `llm.api_key` comes back as the literal string `"**********"` or reports `api_key_set: true` with no value). The real key is stored **encrypted** (a Fernet token starting with `gAAAAA`) in `~/.openhands/profiles/<profile>.json` under `api_key`. Never forward the masked `"**********"` — the new conversation will authenticate with the placeholder and fail with `LLMAuthenticationError` (`You must provide an API key`).

Two working ways to get credentials into the delegated conversation:

1. **`agent_profile_id` (simplest, but no tools)** — send only `agent_profile_id: "<uuid>"` (from `GET /api/agent-profiles` → the profile whose `id` equals `active_agent_profile_id` from `/api/settings`). The server resolves the LLM key + agent kind from the profile. Mutually exclusive with `agent`/`agent_settings`, and the `openhands` agent-profile schema forbids `tools`/`include_default_tools`, so the conversation gets **zero exec tools** this way. Use only when the task needs no tools.

2. **`agent_settings` + encrypted `api_key` (full tools)** — read the encrypted `api_key` Fernet token from `~/.openhands/profiles/<active_llm_profile>.json`, send it in `agent_settings.llm.api_key`, and set `secrets_encrypted: true` so the server's `decrypt_incoming_llm_secrets` decrypts it. This lets `agent_settings.tools` carry the full tool set. Use this for real work.

Template (full tools):

```bash
set -euo pipefail

BASE="${AGENT_CANVAS_BACKEND:-http://localhost:8001}"
KEY="${SESSION_API_KEY:-${OH_SESSION_API_KEYS_0:-${LOCAL_BACKEND_API_KEY:-}}}"
if [ -z "$KEY" ] && [ -f "$HOME/.openhands/agent-canvas/api-key.txt" ]; then
  KEY="$(tr -d '\n' < "$HOME/.openhands/agent-canvas/api-key.txt")"
fi
test -n "$KEY" || { echo "No Agent Canvas session API key found" >&2; exit 1; }

WORKDIR="${WORKDIR:-$HOME/workspace/delegated/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$WORKDIR"

# Resolve the active LLM profile name and read its ENCRYPTED api_key + model
# from the on-disk profile file (the API masks these). The agent-server
# decrypts the Fernet token when secrets_encrypted=true.
SETTINGS_JSON="$(curl -sS -H "X-Session-API-Key: $KEY" "$BASE/api/settings")"
LLM_PROFILE="$(printf '%s' "$SETTINGS_JSON" | jq -r '.active_profile // empty')"
LLM_PROFILE_FILE="$HOME/.openhands/profiles/${LLM_PROFILE}.json"
ENC_KEY="$(jq -r '.api_key' "$LLM_PROFILE_FILE")"
LLM_MODEL="$(jq -r '.model' "$LLM_PROFILE_FILE")"
test -n "$ENC_KEY" && test "${ENC_KEY:0:6}" = "gAAAAA" || {
  echo "Could not read encrypted api_key from $LLM_PROFILE_FILE" >&2; exit 1; }

PROMPT='Write a complete, task-specific prompt here. Include repo, branch, constraints, validation, and expected report. Request skill loading explicitly in the prompt if needed.'

PAYLOAD="$(jq -n --arg prompt "$PROMPT" --arg workdir "$WORKDIR" --arg model "$LLM_MODEL" --arg key "$ENC_KEY" '
  {
    secrets_encrypted: true,
    agent_settings: {
      agent_kind: "openhands",
      llm: { model: $model, api_key: $key, usage_id: "default" },
      tools: [
        {name: "terminal", params: {}},
        {name: "file_editor", params: {}},
        {name: "task_tracker", params: {}},
        {name: "browser_tool_set", params: {}},
        {name: "canvas_ui", params: {}}
      ],
      enable_sub_agents: true,
      tool_concurrency_limit: 1
    },
    tool_module_qualnames: { canvas_ui: "canvas_ui_tool" },
    workspace: {kind: "LocalWorkspace", working_dir: $workdir},
    confirmation_policy: {kind: "NeverConfirm"},
    max_iterations: 1000,
    stuck_detection: true,
    autotitle: true,
    worktree: false,
    initial_message: {
      role: "user",
      content: [{type: "text", text: $prompt}],
      run: true
    }
  }
')"

curl -sS -X POST "$BASE/api/conversations" \
  -H "Content-Type: application/json" \
  -H "X-Session-API-Key: $KEY" \
  --data-binary "$PAYLOAD" | jq '{id, title, execution_status, workspace}'
```

Verify the new conversation actually has tools and is running (not errored):

```bash
CID="<conversation_id>"
curl -sS -H "X-Session-API-Key: $KEY" "$BASE/api/conversations/$CID" \
  | jq '{execution_status, tools: [.agent.tools[]?.name]}'
curl -sS -H "X-Session-API-Key: $KEY" "$BASE/api/conversations/$CID/events/search?limit=20" \
  | jq '[.events[]? | select(.kind=="ConversationErrorEvent") | .code] // []'
```

`execution_status` should be `running`/`idle`/`finished` (not `error`), `tools` should list the exec tools, and there should be no `ConversationErrorEvent`.

If MCP servers configured in the profile are unreachable, conversation creation can fail with `MCP Connection Failure`; `agent_settings` (unlike `agent_profile_id`) lets you omit `mcp_config` to avoid that.

Report both links:

- UI: `http://localhost:8000/conversations/<conversation_id>`
- API: `http://localhost:8001/api/conversations/<conversation_id>`

## Monitor a delegated conversation

```bash
CID="<conversation_id>"
curl -sS -H "X-Session-API-Key: $KEY" "$BASE/api/conversations/$CID" \
  | jq '{id, title, execution_status, updated_at, workspace, agent_kind: .agent.kind, current_model_id, current_model_name}'

curl -sS -H "X-Session-API-Key: $KEY" "$BASE/api/conversations/$CID/events/search?limit=20" \
  | jq '.events // .items // .'
```

Terminal statuses commonly include `idle`, `running`, `finished`, `error`, `stuck`, and `stopped`.

## Prompt checklist for delegation

Include:

- repository owner/name and local path if relevant
- branch, PR, issue, or Linear ticket identifiers
- current status and known blockers
- exact files or subsystems in scope
- dirty-worktree warnings and paths not to touch
- whether to push, open a PR, or only report
- checks/tests to run
- expected final report format

Do not rely on the new conversation knowing anything from the current thread.
