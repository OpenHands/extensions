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

- the **encrypted** `agent_settings` from `GET /api/settings` (with `X-Expose-Secrets: encrypted`), which carries the real Fernet-encrypted `llm.api_key`, the existing `agent_context`, and the agent kind — so you never handle plaintext credentials and you don't drop the caller's skill/context config
- `secrets_encrypted: true` so the agent-server decrypts that `api_key` server-side
- the exec tool set merged into `agent_settings.tools` (and `task_tool_set` when you enable sub-agents)
- `tool_module_qualnames` for any non-SDK tools (e.g. `canvas_ui`)
- `agent_context.load_public_skills`/`load_user_skills`/`load_project_skills` set to `true` if the delegated agent should inherit bundled/user/project skills
- a fresh absolute workspace directory
- `initial_message.run: true`
- `worktree: false` when the workspace is already isolated

### Credential handling — important

`GET /api/settings` (default) **masks** every credential — `llm.api_key` comes back as the literal string `"**********"`. If you forward that verbatim, the new conversation authenticates with the placeholder and fails immediately with `LLMAuthenticationError` (`You must provide an API key`).

The supported way to obtain forwardable credentials is the **`X-Expose-Secrets: encrypted`** request header. With it, `/api/settings` returns the real `llm.api_key` as a **Fernet-encrypted token** (starts with `gAAAAA`) intended to be sent back to the server with `secrets_encrypted: true`; the agent-server's `decrypt_incoming_llm_secrets` decrypts it server-side. Do **not** read `~/.openhands/profiles/*.json` directly — that is brittle (the caller may not share the backend's home directory, `active_profile` may be null, the profile store may live elsewhere).

Two working approaches:

1. **`agent_profile_id` (simplest, but no tools)** — send only `agent_profile_id: "<uuid>"` (from `GET /api/agent-profiles` → the profile whose `id` equals `active_agent_profile_id` from `/api/settings`). The server resolves the LLM key + agent kind from the profile. Mutually exclusive with `agent`/`agent_settings`, and the `openhands` agent-profile schema forbids `tools`/`include_default_tools`, so the conversation gets **zero exec tools** this way. Use only when the task needs no tools.

2. **Encrypted `agent_settings` (full tools, preserves context)** — start from the encrypted `/api/settings` `agent_settings` payload, drop `schema_version` and `mcp_config` (to avoid MCP-connection failures at creation time), merge in the exec tool set and `load_*_skills` flags, and send with `secrets_encrypted: true`. This is the pattern for real delegated work.

Template (full tools, preserves context):

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

# Fetch the agent_settings with ENCRYPTED secrets exposed. This returns the
# real llm.api_key as a Fernet token (gAAAAA...) plus the existing
# agent_context/agent kind, so we preserve the caller's config and never
# handle plaintext credentials.
SETTINGS_JSON="$(curl -sS -H "X-Session-API-Key: $KEY" -H "X-Expose-Secrets: encrypted" "$BASE/api/settings")"

PROMPT='Write a complete, task-specific prompt here. Include repo, branch, constraints, validation, and expected report.'

PAYLOAD="$(jq -n --argjson settings "$SETTINGS_JSON" --arg prompt "$PROMPT" --arg workdir "$WORKDIR" '
  # Start from the encrypted agent_settings so llm.api_key (Fernet token),
  # agent_kind, and agent_context are preserved. Drop schema_version and
  # mcp_config (MCP servers can fail to connect at creation time; the profile
  # can be re-resolved later if needed).
  def base_agent_settings:
    ($settings.agent_settings // {})
    | del(.schema_version)
    | del(.mcp_config);

  # Merge the exec tool set into the existing tools list. Include task_tool_set
  # when sub-agents are enabled — enable_sub_agents alone does not expose the
  # delegation tool; Agent Canvas adds task_tool_set for that.
  def with_tools:
    .tools = ((.tools // []) + [
      {name: "terminal", params: {}},
      {name: "file_editor", params: {}},
      {name: "task_tracker", params: {}},
      {name: "browser_tool_set", params: {}},
      {name: "canvas_ui", params: {}}
    ] + (if .enable_sub_agents then [{name: "task_tool_set", params: {}}] else [] end)
    | unique_by(.name));

  # Preserve the existing agent_context and enable skill loading for the
  # delegated agent (defaults are false, so set these explicitly).
  def with_skill_loading:
    .agent_context = ((.agent_context // {}) + {
      load_public_skills: true,
      load_user_skills: true,
      load_project_skills: true
    });

  ($settings.conversation_settings // {}) as $conv |
  {
    secrets_encrypted: true,
    agent_settings: (base_agent_settings | with_tools | with_skill_loading),
    tool_module_qualnames: { canvas_ui: "canvas_ui_tool" },
    workspace: {kind: "LocalWorkspace", working_dir: $workdir},
    confirmation_policy: {kind: "NeverConfirm"},
    # Delegated tasks usually need more than the SDK default of 80 iterations;
    # default to the caller's conversation_settings value (1000 in Agent Canvas)
    # so long-running tasks aren't cut off prematurely. Override per-task if needed.
    max_iterations: (($conv.max_iterations // 1000) | if . == null then 1000 else . end),
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

If MCP servers configured in the profile are unreachable, conversation creation can fail with `MCP Connection Failure`; the template drops `mcp_config` from the forwarded `agent_settings` to avoid that.

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
