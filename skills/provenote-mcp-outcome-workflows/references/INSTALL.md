# Install and Connect Provenote MCP

This guide avoids private paths and keeps the install loop portable.

## What you need

- a local clone of `https://github.com/xiaojiou176-open/provenote`
- `uv`
- a workspace where the host can launch shell commands

## 1. Clone and install the repo

```bash
git clone https://github.com/xiaojiou176-open/provenote.git
cd provenote
uv sync
```

## 2. Make the MCP server launchable

Provenote exposes its MCP server through the repo-owned entrypoint:

```bash
cd /absolute/path/to/provenote
uv run provenote-mcp
```

You do not need to invent a wrapper package. Reuse that command in your host
config.

## 3. Connect it in an OpenHands-style host

Copy and edit [OPENHANDS_MCP_CONFIG.json](OPENHANDS_MCP_CONFIG.json) so the
absolute path points at your local clone.

## 4. Connect it in OpenClaw

Copy and edit [OPENCLAW_MCP_CONFIG.json](OPENCLAW_MCP_CONFIG.json), then load it
into your OpenClaw MCP configuration.

## 5. Verify the smallest useful loop

Once the host can see the server, run this tool sequence:

1. `draft.list`
2. `research_thread.list`
3. `auditable_run.list`

If those three read calls work, the host wiring is good enough for a real
read-first outcome workflow.
