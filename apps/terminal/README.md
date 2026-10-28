# Terminal

Terminal is an App for Agent Canvas that runs shell commands on the active backend through Canvas host API 1. It bundles xterm.js into a single Blob-importable `extension.js` and does not use a sidecar, custom HTTP request, WebSocket, localStorage credential lookup, or API key.

> [!WARNING]
> Terminal is a general-purpose shell. Every command you type runs on the Agent Server machine through `POST /api/bash/execute_bash_command`, with the same permissions as the agent. Enable it only on a backend where you would run those commands yourself.

## Architecture

1. Canvas Blob-imports `extension.js` and mounts the Terminal page.
2. The App asks `host.agentServer.request` for `/api/file/home`.
3. Entering a command calls the authenticated host adapter with:

```json
{
  "method": "POST",
  "path": "/api/bash/execute_bash_command",
  "body": {
    "command": "pwd",
    "cwd": "/backend/home",
    "timeout": 300
  }
}
```

4. Canvas selects the active backend and attaches authentication. The App renders returned stdout, stderr, and nonzero exit status in xterm.

Each submitted line is an independent `execute_bash` request. This is a command runner rather than a persistent PTY: interactive full-screen programs, live streaming, signals, and shell state between commands are not available through host API 1.

## Build and verify

Use a supported even-numbered Node release (Node 22 or 24 recommended).

```sh
npm ci
npx playwright install chromium
npm run check
```

The build emits one `extension.js` containing the App, xterm.js, and all styles. `npm run check` performs strict type checking, tests, a production build, Canvas artifact validation, and a Chromium Blob-import smoke that enters a command through xterm and verifies the Host API request.

## Install in Agent Canvas

In **Customize → Apps → Add app**, paste this folder's URL at the commit you reviewed as **App source**:

```text
https://github.com/OpenHands/extensions/tree/<commit>/apps/terminal
```

The form splits it into source `https://github.com/OpenHands/extensions`, **Ref** `<commit>` and **Path** `apps/terminal`. The App installs disabled. Review its source at that revision, switch it on and confirm **Enable trusted app**, then open **Terminal** from the sidebar. Canvas installs a copy, so after a change use **Update** on its card, or uninstall and reinstall.

## Security model

This App uses only the Canvas-provided authenticated request adapter.

- It never reads or stores an Agent Server API key.
- It never inspects Canvas localStorage, Redux state, DOM attributes, or undocumented globals.
- It does not create direct network requests or WebSockets.
- It passes only root-relative Agent Server paths to `host.agentServer.request`.
- Commands run with the permissions and command policy of the active backend's Agent Server.
- Only one command request runs at a time, with a 300-second requested timeout.
- Late results are ignored after the page unmounts.

## Source

Moved from [OpenHands/canvas-apps](https://github.com/OpenHands/canvas-apps/tree/b83068fdce5ec7f85c07b8aefa15d413982059d0/terminal) at `b83068fdce5ec7f85c07b8aefa15d413982059d0`, keeping the MIT [LICENSE](LICENSE). Installations made from canvas-apps do not follow this move: uninstall them and install again from this registry.
