# Install and Connect Prompt Switchboard MCP

This guide avoids private paths and keeps the install loop portable.

## What you need

- a local clone of `https://github.com/xiaojiou176-open/multi-ai-sidepanel`
- Node.js and npm
- the Prompt Switchboard browser extension installed and able to reach its side panel
- at least two supported AI chat tabs signed in and open

## 1. Clone and install the repo

```bash
git clone https://github.com/xiaojiou176-open/multi-ai-sidepanel.git
cd multi-ai-sidepanel
npm install
```

## 2. Make the MCP server launchable

Prompt Switchboard exposes its MCP server through the repo-owned script:

```bash
npm --prefix /absolute/path/to/multi-ai-sidepanel run mcp:server
```

You do not need to invent a new wrapper. Reuse that command in your host config.

## 3. Connect it in an OpenHands-style host

Copy and edit [OPENHANDS_MCP_CONFIG.json](OPENHANDS_MCP_CONFIG.json) so the
absolute path points at your local clone.

## 4. Connect it in OpenClaw

Copy and edit [OPENCLAW_MCP_CONFIG.json](OPENCLAW_MCP_CONFIG.json), then load it
into your OpenClaw MCP configuration.

## 5. Verify the smallest useful loop

Once the host can see the server, run this tool sequence:

1. `prompt_switchboard.bridge_status`
2. `prompt_switchboard.check_readiness`
3. `prompt_switchboard.compare`

If that loop works, the host wiring is good enough for a real compare-first
workflow.
