# Install The Published DealWatch MCP

Use the published PyPI package, not a repo-local checkout.

## Published package

- package: `dealwatch==1.0.1`
- executable: `dealwatch-mcp`
- transport: `stdio`

## OpenHands config example

Add this to `~/.openhands/config.toml`:

```toml
[mcp]
stdio_servers = [
  { name = "dealwatch", command = "uvx", args = ["--from", "dealwatch==1.0.1", "dealwatch-mcp", "serve"] }
]
```

## Smoke check

```bash
uvx --from dealwatch==1.0.1 dealwatch-mcp list-tools --json
```
