# Templates

Use these as starting points when implementing a “self-modification” without changing OpenHands code.

## AgentSkills (`SKILL.md`) template

Create a directory:

```
<repo>/.agents/skills/<skill-name>/
└── SKILL.md
```

Example `SKILL.md`:

```md
---
name: my-team-workflow
description: Our team’s workflow for X. Use when the user asks about X.
triggers:
- team x workflow
- how do we do x
---

# Our workflow for X

## When to use

Use this workflow when...

## Steps

1. ...
2. ...

## Verification

- Run: `...`
```

Notes:
- Keep triggers distinctive.
- Keep the file focused; put deep details in `references/`.

## Always-on repo instructions (`AGENTS.md`) template

Create `<repo>/AGENTS.md`:

```md
# Project rules

## Build / run
- `make install`
- `make test`

## Code style
- Ruff formatting

## Safety
- Never run destructive commands without asking
```

## Hooks (`.openhands/hooks.json`) template

Create `<repo>/.openhands/hooks.json`:

```json
{
  "pre_tool_use": [
    {
      "command": "bash .openhands/hooks/block-dangerous.sh",
      "matchers": {
        "tool_name": "terminal"
      }
    }
  ]
}
```

Then create the script `<repo>/.openhands/hooks/block-dangerous.sh`:

```bash
#!/usr/bin/env bash

# stdin: HookEvent JSON
payload="$(cat)"

# Example: block `rm -rf ...` for Terminal tool calls.
# Requires: jq
cmd="$(echo "$payload" | jq -r '.tool_input.command // ""')"

if echo "$cmd" | grep -Eq '(^|[[:space:]])rm[[:space:]]+-rf([[:space:]]|$)'; then
  # HookExecutor parses JSON on stdout; "decision" must be "allow" or "deny".
  jq -n --arg reason "Blocked destructive command" '{"decision":"deny","reason":$reason}'
  exit 0
fi

jq -n '{"decision":"allow"}'
```

Notes:
- Prefer parsing the structured fields (like `.tool_input.command`) rather than grepping raw JSON.
- The exact `tool_input` shape is tool-specific; inspect the SDK `HookEvent` schema and your tool inputs.

## Plugin template

Plugin structure:

```
my-plugin/
├── .plugin/
│   └── plugin.json
├── skills/
│   └── my-skill/
│       └── SKILL.md
├── hooks/
│   └── hooks.json
├── .mcp.json
└── README.md
```

Minimal `.plugin/plugin.json` (fields vary by plugin schema):

```json
{
  "name": "my-plugin",
  "version": "0.1.0",
  "description": "My custom OpenHands behavior",
  "author": {
    "name": "Example",
    "email": "dev@example.com"
  }
}
```

## MCP template (`.mcp.json`)

Minimal example:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["-m", "my_mcp_server"],
      "env": {
        "MY_SERVER_TOKEN": "$MY_SERVER_TOKEN"
      }
    }
  }
}
```

Notes:
- Never hardcode real secrets in files.
- Prefer environment variables.
