# Prompt Switchboard Compare Workflows

This skill teaches an OpenHands agent how to connect Prompt Switchboard's local
MCP sidecar and use it for compare-first browser workflows.

## What this package includes

- `SKILL.md`
  - the agent-facing workflow prompt
- `references/INSTALL.md`
  - install and host wiring guide
- `references/CAPABILITIES.md`
  - exposed MCP tools and the recommended first-use path
- `references/DEMO.md`
  - exact demo prompt and success criteria
- `references/OPENHANDS_MCP_CONFIG.json`
  - ready-to-edit `mcpServers` config
- `references/OPENCLAW_MCP_CONFIG.json`
  - equivalent OpenClaw config

## What this skill teaches

- how to install the local Prompt Switchboard MCP sidecar
- how to connect it inside OpenHands or OpenClaw
- how to start with bridge and readiness checks before bigger automation
- how to turn one compare run into an inspectable artifact

## Best fit

- compare-first browser review workflows
- local MCP sidecar usage
- read-first verification before broader automation

## Source repository

- Repo: https://github.com/xiaojiou176-open/multi-ai-sidepanel
- MCP docs: https://github.com/xiaojiou176-open/multi-ai-sidepanel/blob/main/docs/mcp-coding-agents.html

## Boundaries

- This skill does not imply a hosted Prompt Switchboard backend.
- This skill should stay aligned with the source repo's MCP surface and demo flow.
