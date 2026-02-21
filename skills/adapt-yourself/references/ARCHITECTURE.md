# OpenHands extensibility architecture (CLI + SDK)

OpenHands “behavior” can be modified at multiple layers. The key is to choose the layer that matches the user’s intent.

## Components

### OpenHands CLI (`OpenHands/OpenHands-CLI`)

- Python package name: `openhands`
- Entry points: `openhands`, `openhands-acp`
- Responsibilities:
  - Terminal UI (Textual)
  - Loading config + wiring up an SDK `Agent`
  - Choosing tools and building an `AgentContext`

In the CLI codebase, look for where it creates the `AgentContext` and enables:
- project skills
- user skills
- public skills

### Software Agent SDK monorepo (`OpenHands/software-agent-sdk`)

This repo is a **uv workspace** that produces multiple packages:

- `openhands-sdk` (module: `openhands.sdk`)
  - agent runtime primitives (Agent, Conversation, Event model)
  - context loading (skills)
  - hooks system
  - plugin loader

- `openhands-tools` (module: `openhands.tools`)
  - built-in tools used by many OpenHands projects

- `openhands-workspace` (module: `openhands.workspace`)
  - workspace mounting, file sync abstractions

- `openhands-agent-server`
  - server-side runtime

## Skills

Skills are loaded from multiple locations; **project-local skills override user + public**.

Common locations:

- Project-local:
  - `<repo>/.agents/skills/`

- User-global:
  - `~/.agents/skills/`

- Public registry:
  - `https://github.com/OpenHands/extensions` (cached locally under `~/.openhands/skills-cache/`)

Skill types:

- **AgentSkills format**: a directory with `SKILL.md` (progressive disclosure)
- **Always-on instructions**: repo instruction files like `AGENTS.md` (loaded at conversation start)

## Hooks

Hooks are configured via JSON and executed on events (e.g. `pre_tool_use`).

Typical locations (depending on product / SDK config):

- `<repo>/.openhands/hooks.json`
- `~/.openhands/hooks.json`

Hook scripts receive an event payload on stdin as JSON and respond with a decision.

## Plugins

Plugins are bundles of:

- skills
- hooks
- MCP config
- optional commands and agents

They follow the Claude Code-compatible directory structure:

```
my-plugin/
├── .plugin/
│   └── plugin.json
├── skills/
├── hooks/
│   └── hooks.json
├── .mcp.json
└── README.md
```

Plugins can be:
- loaded from a local path
- fetched from GitHub/git URLs and cached under `~/.openhands/cache/plugins/`

## MCP servers (tools)

MCP servers provide tool endpoints to the agent.

They are configured via `.mcp.json` (location depends on host product). Plugins can also provide MCP config.
