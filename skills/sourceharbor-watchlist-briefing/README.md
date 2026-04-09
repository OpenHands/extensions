# SourceHarbor Watchlist Briefing

This skill is the OpenClaw-facing watchlist briefing card for SourceHarbor.

It is designed to behave like a self-contained operator skill package:

- one skill prompt that teaches the agent the workflow
- one install/config pack for MCP and HTTP fallback
- one capability map over the SourceHarbor operator surfaces
- one first-success demo path
- one troubleshooting page that explains where the first failures live
- one manifest so the folder can travel into review-driven skill registries

Use it when the agent should start from one watchlist, reuse the current story/briefing context, and answer one operator question with evidence.

## What this packet includes

- `SKILL.md`
  - the agent-facing watchlist briefing workflow
- `README.md`
  - the human-facing packet overview
- `manifest.yaml`
  - registry-style metadata for host skill registries
- `references/README.md`
  - the local index for every supporting file
- `references/INSTALL.md`
  - MCP and HTTP setup guidance
- `references/OPENHANDS_MCP_CONFIG.json`
  - a ready-to-edit `mcpServers` snippet
- `references/OPENCLAW_MCP_CONFIG.json`
  - a ready-to-edit `mcp.servers` snippet
- `references/CAPABILITIES.md`
  - the operator-facing MCP capability map
- `references/DEMO.md`
  - the first-success walkthrough and expected output shape
- `references/TROUBLESHOOTING.md`
  - the first places to check when MCP or HTTP access fails
