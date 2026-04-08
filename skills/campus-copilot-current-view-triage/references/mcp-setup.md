# Campus Copilot MCP Setup

Use this when the host runtime does not already have Campus Copilot MCP connected.

## Quickest local setup

1. Clone the public repo:

```bash
git clone https://github.com/xiaojiou176-open/campus-copilot.git
cd campus-copilot
pnpm install
```

2. Build the read-only MCP server:

```bash
pnpm --filter @campus-copilot/mcp-server build
```

3. Start the MCP server directly:

```bash
pnpm --filter @campus-copilot/mcp-server start
```

## If your host supports MCP Bundles

Campus Copilot also ships a release-hosted MCP Bundle:

- registry name: `io.github.xiaojiou176-open/campus-copilot-mcp`
- release asset: `https://github.com/xiaojiou176-open/campus-copilot/releases/download/v0.1.0/campus-copilot-mcp-0.1.0.mcpb`

## What the operator should hand back to the agent

- whether Campus Copilot MCP is connected
- whether only a snapshot/current-view export is available
- the path to the snapshot or current-view file if MCP is not connected
