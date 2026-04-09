# Install The Published CortexPilot MCP

Use the published PyPI package, not a repo-local checkout.

## Published package

- package: `cortexpilot-orchestrator==0.1.0a4`
- executable: `cortexpilot-readonly-mcp`
- transport: `stdio`

## OpenHands example

Use `OPENHANDS_MCP_CONFIG.json` as the starting point for your host config.

## OpenClaw example

Use `OPENCLAW_MCP_CONFIG.json` as the starting point for your host config.

## Smoke check

Use a minimal MCP handshake and `tools/list` request after the host attaches the
server.
