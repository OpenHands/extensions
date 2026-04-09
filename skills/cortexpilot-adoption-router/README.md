# CortexPilot Adoption Router

This bundle teaches an agent how to connect the published CortexPilot read-only
MCP package and choose the right public adoption lane.

## What the agent learns here

- how to install the published `cortexpilot-orchestrator==0.1.0a4` MCP package
- which read-only CortexPilot tools exist and which are safe-first
- how to choose between run/workflow inspection, queue/approval reads, and
  proof/incident reads
- which hosted or write-capable claims stay out of bounds

## Included files

- `SKILL.md` — the progressive-disclosure prompt for the agent
- `README.md` — the human-facing overview for reviewers and operators
- `manifest.yaml` — listing metadata for host skill registries
- `references/README.md` — the local index for every supporting file
- `references/INSTALL.md` — exact install snippets for OpenHands/OpenClaw
- `references/OPENHANDS_MCP_CONFIG.json` — a ready-to-edit `mcpServers` snippet
- `references/OPENCLAW_MCP_CONFIG.json` — a ready-to-edit `mcp.servers` snippet
- `references/CAPABILITIES.md` — the stable read-only tool inventory
- `references/DEMO.md` — the first-success walkthrough and expected return shape
- `references/TROUBLESHOOTING.md` — the first checks when launch or inspection fails

## The shortest install path

Use the published package, not a repo-local checkout:

```bash
uvx --from cortexpilot-orchestrator==0.1.0a4 cortexpilot-readonly-mcp
```

If the host needs a saved MCP config snippet, use the host-specific examples in
`references/INSTALL.md`.

## Hard boundaries

- no hosted operator service
- no write-capable public MCP
- no first-party marketplace claim unless that host independently confirms it
