# DealWatch Read-only Builder

Public OpenHands skill for connecting the published DealWatch MCP package and
using its read-only tools safely.

## What this skill teaches

- how to install the published `dealwatch==1.0.1` MCP package
- which DealWatch MCP tools are safe-first
- how to move from runtime readiness into compare preview and then into deeper
  detail reads
- which claims stay out of bounds

## Included files

- `SKILL.md` — the agent-facing prompt
- `references/mcp-install.md` — exact OpenHands install snippet
- `references/tool-map.md` — the stable DealWatch MCP tool map
- `references/example-tasks.md` — concrete tasks this skill is meant to handle

## Hard boundaries

- no hosted DealWatch control plane
- no write-side MCP surface
- no first-party marketplace claim unless the host independently confirms it
