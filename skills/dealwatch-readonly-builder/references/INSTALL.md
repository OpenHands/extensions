# Install The Published DealWatch MCP

Use the published PyPI package, not a repo-local `PYTHONPATH=src` shortcut.

## Published package

- package: `dealwatch==1.0.1`
- executable: `dealwatch-mcp`
- transport: `stdio`

## OpenHands example

Use `OPENHANDS_MCP_CONFIG.json` as the starting point for your host config.

## OpenClaw example

Use `OPENCLAW_MCP_CONFIG.json` as the starting point for your host config.

## Smoke check

```bash
uvx --from dealwatch==1.0.1 dealwatch-mcp list-tools --json
```

If that command returns the tool inventory, the published MCP package is wired
correctly.
