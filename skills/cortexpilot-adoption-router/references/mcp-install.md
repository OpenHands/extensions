# Install The Published CortexPilot MCP

Use the published PyPI package, not a repo-local checkout.

## Published package

- package: `cortexpilot-orchestrator==0.1.0a4`
- executable: `cortexpilot-readonly-mcp`
- transport: `stdio`

## OpenHands config example

Add this to `~/.openhands/config.toml`:

```toml
[mcp]
stdio_servers = [
  { name = "cortexpilot-readonly", command = "uvx", args = ["--from", "cortexpilot-orchestrator==0.1.0a4", "cortexpilot-readonly-mcp"] }
]
```

## Smoke check

After the host attaches the server, request `tools/list` and confirm the
read-only run/workflow tools are present.
