# Install And Attach ProofTrail MCP

## Local repo setup

```bash
git clone https://github.com/xiaojiou176-open/prooftrail.git
cd prooftrail
pnpm install
```

## Start the current repo-native MCP server

```bash
pnpm mcp:start
```

Before loading the host config snippets in this folder, replace
`/absolute/path/to/prooftrail` with the real path to your local clone.

## Verification commands

```bash
pnpm mcp:check
pnpm mcp:test
pnpm mcp:smoke
```

Use `pnpm test:mcp-server:real` only when a real backend is already running and
`UIQ_ENABLE_REAL_BACKEND_TESTS=true` is set.

## Truth boundary

This packet teaches the repo-native stdio MCP surface that works today.
Future npm or Docker command shapes are publish-ready but not yet published.
