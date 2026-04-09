# OpenUI Workspace Delivery

This folder is the public, self-contained skill packet for OpenUI MCP Studio.

It is meant to teach an agent four things without sending the reviewer back to
repo-root docs first:

- how to install the local MCP server
- how to attach it to OpenHands or OpenClaw
- which UI-generation tools are safe to use first
- what the shortest proof loop looks like

## Included files

- `SKILL.md`
- `manifest.yaml`
- `references/INSTALL.md`
- `references/OPENHANDS_MCP_CONFIG.json`
- `references/OPENCLAW_MCP_CONFIG.json`
- `references/CAPABILITIES.md`
- `references/DEMO.md`
- `references/TROUBLESHOOTING.md`

## Truth boundary

- this packet has a live ClawHub listing
- it is still not a live vendor marketplace listing
- it does not claim a hosted runtime
- it does not claim vendor approval or official ClawHub placement

Use the host configs and proof loop in `references/` first. Treat the older
`commands/` and `samples/` files as supporting material, not as the primary
reviewer packet.
