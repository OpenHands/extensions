# Current View Triage MCP Setup

## Fastest local setup

From the Campus Copilot repo root:

```bash
pnpm install
pnpm --filter @campus-copilot/mcp-server build
pnpm --filter @campus-copilot/mcp-server start
```

## If the host supports MCP Bundles

- registry name: `io.github.xiaojiou176-open/campus-copilot-mcp`
- release asset: `https://github.com/xiaojiou176-open/campus-copilot/releases/download/v0.1.0/campus-copilot-mcp-0.1.0.mcpb`

## Minimum handoff to the agent

- one imported snapshot or current-view export path
- whether Campus Copilot MCP is already connected
- optional student question
