# Install And Attach OpenUI MCP Studio

Use the current repo-native MCP path first.

## Quickest local setup

1. Clone the public repository:

```bash
git clone https://github.com/xiaojiou176-open/openui-mcp-studio.git
cd openui-mcp-studio
npm install
npm run build
```

2. Confirm the compiled MCP entry exists:

- `.runtime-cache/build/mcp-server/services/mcp-server/src/main.js`

3. Replace the placeholder server path in the host config snippets with the real
   local checkout path, and replace `GEMINI_API_KEY` with a real local secret
   before attach.

4. Attach the host with one of the config snippets in this folder.

## Current truthful install mode

- protocol: `stdio`
- transport: `stdio`
- runtime: local repo checkout
- public marketplace listing: not claimed

## What to hand back to the agent

- whether the build output exists
- whether `GEMINI_API_KEY` is available
- which host you are attaching
- whether the proof loop commands complete
