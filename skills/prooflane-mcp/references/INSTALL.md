# Install And Attach Prooflane MCP

## Local repo setup

```bash
git clone https://github.com/xiaojiou176-open/ui-automation-control-plane.git
cd ui-automation-control-plane
./scripts/setup.sh
```

If you already trust the workspace toolchain, `pnpm install` is enough for JS
dependencies.

Before loading the host config snippets in this folder, replace
`/ABSOLUTE/PATH/TO/REPO` with the real path to your local clone.

## Start the current repo-native MCP server

```bash
pnpm mcp:start
```

## Verification commands

```bash
pnpm mcp:check
pnpm mcp:build
pnpm mcp:package:smoke
pnpm mcp:doc:contract
pnpm mcp:smoke
```

## Truth boundary

This packet teaches the repo-native stdio MCP surface that works today.
The package shape `@uiq/mcp-server` / `prooflane-mcp` is publish-ready but not
yet published.
