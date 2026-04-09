# Install And Attach Shopflow MCP

Use the current repo-native MCP path first.

## Quickest local setup

1. Clone the public repository:

```bash
git clone https://github.com/xiaojiou176-open/shopflow-suite.git
cd shopflow-suite
pnpm install
```

2. Start the read-only MCP surface:

```bash
pnpm mcp:stdio
```

3. Replace `/absolute/path/to/shopflow-suite` in the host config snippets with
   the real path to your local clone before attach.

4. Verify the packet surface:

```bash
pnpm verify:catalog
pnpm verify:release-readiness
```

## Current truthful install mode

- protocol: `stdio`
- transport: `stdio`
- public listing: not claimed
- browser extension/store listing: not claimed

## What to hand back to the agent

- whether the MCP server launches
- whether the capability packets are readable
- whether the distribution bundle looks ready or still blocked
