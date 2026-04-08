# CortexPilot Adoption Router

Public OpenHands skill for connecting the published CortexPilot read-only MCP
package and choosing the right public lane.

## What this skill teaches

- how to install the published `cortexpilot-orchestrator==0.1.0a4` MCP package
- which read-only CortexPilot tools are safe-first
- how to choose between run/workflow inspection, queue/approval reads, and
  proof/incident reads
- which claims stay out of bounds

## Included files

- `SKILL.md` — the agent-facing prompt
- `references/mcp-install.md` — exact OpenHands install snippet
- `references/tool-map.md` — the stable CortexPilot MCP tool map
- `references/example-tasks.md` — concrete tasks this skill is meant to handle

## Hard boundaries

- no hosted operator service
- no write-capable public MCP
- no first-party marketplace claim unless the host independently confirms it
