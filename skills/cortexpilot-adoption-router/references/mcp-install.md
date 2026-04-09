# Install The Published CortexPilot MCP

Use the published PyPI package, not a repo-local checkout.

## Published package

- package: `cortexpilot-orchestrator==0.1.0a4`
- executable: `cortexpilot-readonly-mcp`
- transport: `stdio`

## OpenHands example

Add the server to `~/.openhands/config.toml`:

```toml
[mcp]
stdio_servers = [
  { name = "cortexpilot-readonly", command = "uvx", args = ["--from", "cortexpilot-orchestrator==0.1.0a4", "cortexpilot-readonly-mcp"] }
]
```

## OpenClaw example

Add the server to your saved MCP server config:

```json
{
  "mcp": {
    "servers": {
      "cortexpilot-readonly": {
        "command": "uvx",
        "args": ["--from", "cortexpilot-orchestrator==0.1.0a4", "cortexpilot-readonly-mcp"]
      }
    }
  }
}
```

## Smoke check

Use a minimal MCP handshake and `tools/list` request after the host attaches the
server.
