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

- current `/api/settings` (fetched with `X-Expose-Secrets: plaintext`) as the base agent profile
- a fresh absolute workspace directory
- `initial_message.run: true`
- `worktree: false` when the workspace is already isolated
- the default tool set injected into `agent_settings.tools` (see note below)

> **Why inject tools?** The persisted profile returned by `/api/settings` stores
> `tools: []`. The UI populates the tool list at launch time; an API-created
> conversation gets exactly the `tools` array you send and the server adds no
> defaults. Without injecting the defaults, the delegated agent can only call
> built-in actions (`invoke_skill`, `think`, `finish`) and cannot run shell
> commands, edit files, or browse. Always set `agent_settings.tools` to the
> default tool list below (drop `browser_tool_set` if the agent does not need
> browser access).
>
> **Why `X-Expose-Secrets: plaintext`?** Without it, the LLM API key comes back
> redacted (`**********`). Echoing redacted settings into the new conversation
> causes an `LLMAuthenticationError`. The header is safe for backend clients
> that never log the raw response.

Template:

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

# plaintext so the LLM api_key is not redacted (**********) when echoed back.
SETTINGS_JSON="$(curl -sS -H "X-Session-API-Key: $KEY" -H "X-Expose-Secrets: plaintext" "$BASE/api/settings")"
PROMPT='Write a complete, task-specific prompt here. Include repo, branch, constraints, validation, and expected report.'

# The profile's tools field is []; inject the default tool set the UI uses.
DEFAULT_TOOLS='[
  {"name":"terminal","params":{}},
  {"name":"file_editor","params":{}},
  {"name":"task_tracker","params":{}},
  {"name":"canvas_ui","params":{}},
  {"name":"browser_tool_set","params":{}}
]'

PAYLOAD="$(jq -n --argjson settings "$SETTINGS_JSON" --argjson tools "$DEFAULT_TOOLS" --arg prompt "$PROMPT" --arg workdir "$WORKDIR" '
  def agent_settings:
    ($settings.agent_settings // {})
    | del(.schema_version)
    | . + {
        agent_context: ((.agent_context // {}) + {
          load_public_skills: true,
          load_user_skills: true,
          load_project_skills: true
        }),
        tools: $tools
      };
  ($settings.conversation_settings // {}) as $conv |
  {
    agent_settings: agent_settings,
    workspace: {kind: "LocalWorkspace", working_dir: $workdir},
    confirmation_policy: {kind: "NeverConfirm"},
    max_iterations: (($conv.max_iterations // 80) | if . == null then 80 else . end),
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
