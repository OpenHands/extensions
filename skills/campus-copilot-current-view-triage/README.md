# Current View Triage

This skill is the compact read-only triage card for Campus Copilot.

It is designed to work like a lightweight plugin bundle:

- one skill prompt that tells the agent what job to do
- one install/config pack that tells the operator how to connect the runtime
- one capability map that explains which Campus Copilot tools are exposed
- one demo path that shows the shortest first-success flow
- one troubleshooting page that explains where the first failures usually live
- one manifest so the folder can travel into review-driven skill registries

Use it when you want the shortest truthful answer to:

- what should the student do first right now

## What this packet includes

- `SKILL.md`
  - the agent-facing triage workflow
- `README.md`
  - the human-facing packet overview
- `manifest.yaml`
  - registry-style metadata for host skill registries
- `references/README.md`
  - the local index for every supporting file
- `references/INSTALL.md`
  - install and host wiring guidance
- `references/OPENHANDS_MCP_CONFIG.json`
  - a ready-to-edit `mcpServers` snippet
- `references/OPENCLAW_MCP_CONFIG.json`
  - a ready-to-edit `mcp.servers` snippet
- `references/CAPABILITIES.md`
  - the read-only Campus Copilot tool surface
- `references/DEMO.md`
  - the first-success walkthrough and expected output shape
- `references/TROUBLESHOOTING.md`
  - the first places to check when setup or triage fails
