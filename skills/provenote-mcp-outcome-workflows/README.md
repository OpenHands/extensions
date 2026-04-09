# Provenote MCP Outcome Workflows Public Skill

This folder is the public, self-contained skill packet for Provenote.
It is designed to carry install, config, capability, and demo material inside
the skill folder instead of pushing that burden back to repo-root docs.

## Purpose

Use it when you want one portable skill folder that teaches four things clearly:

- how to install and launch the first-party `provenote-mcp` server
- how to wire it into OpenHands or OpenClaw
- what MCP tool families Provenote exposes
- what a read-first outcome workflow looks like in practice

## What this packet includes

- `SKILL.md`
  - the agent-facing workflow prompt
- `manifest.yaml`
  - listing metadata for registry-style distribution
- `references/INSTALL.md`
  - install and host wiring guide
- `references/CAPABILITIES.md`
  - exposed MCP tools and recommended first-use path
- `references/DEMO.md`
  - exact demo prompts and success criteria
- `references/OPENHANDS_MCP_CONFIG.json`
  - host config snippet for `mcpServers`
- `references/OPENCLAW_MCP_CONFIG.json`
  - host config snippet for `mcp.servers`
- `references/TROUBLESHOOTING.md`
  - first-failure checks for launch, empty workspaces, and narrow write steps

## Best-fit hosts

- OpenHands/extensions contribution flow
- ClawHub-style skill publication
- repo-local skill import flows that expect a standalone folder with its own
  install and demo references

## Current verified state

- the ClawHub skill listing is live
- the Provenote MCP server is live in the Official MCP Registry
- the OpenHands/extensions lane is review-pending, not merged

## What this packet must not claim

- no live OpenHands/extensions listing without fresh PR/read-back
- no official marketplace or directory listing by itself
- no replacement of the first-party `provenote-mcp` server

## Source of truth

Keep this packet aligned with the source repo, but do not make reviewers depend
on repo-root docs before they can understand the skill:

- `docs/distribution.md`
- `docs/project-status.md`
- `server.json`
- `examples/hosts/openclaw/clawhub/provenote-mcp-outcome-workflows/SKILL.md`
