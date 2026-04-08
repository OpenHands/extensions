# Provenote MCP Outcome Workflows

This skill teaches an OpenHands agent how to connect Provenote's first-party
MCP server and use it for read-first outcome workflows.

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

- how to install and launch `provenote-mcp`
- how to connect it inside OpenHands or OpenClaw
- how to inspect Provenote drafts, research threads, and auditable runs first
- how to keep write actions narrow and outcome-linked

## Best fit

- long-context to structured research workflows
- first-party MCP usage through `provenote-mcp`
- read-first validation before write-oriented automation

## Source repository

- Repo: https://github.com/xiaojiou176-open/provenote
- MCP docs: https://github.com/xiaojiou176-open/provenote/blob/main/docs/mcp.md

## Boundaries

- This skill does not replace the first-party `provenote-mcp` server.
- This skill does not imply a hosted Provenote SaaS surface.
- This skill should stay aligned with the source repo's MCP docs and demo flow.
