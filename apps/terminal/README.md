# Terminal

Terminal is an App for Agent Canvas that runs shell commands on the active backend through Canvas host API 1. It bundles xterm.js into a single Blob-importable `extension.js` and does not use a sidecar, custom HTTP request, WebSocket, localStorage credential lookup, or API key.

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

In **Customize → Apps**, add this backend-visible source:

```text
/root/git/canvas-app-terminal
```

Review and enable the installed **Terminal** App. Reinstall with force after rebuilding because Canvas installs a copy rather than running the source tree directly.

## Security model

This App uses only the Canvas-provided authenticated request adapter.

- It never reads or stores an Agent Server API key.
- It never inspects Canvas localStorage, Redux state, DOM attributes, or undocumented globals.
- It does not create direct network requests or WebSockets.
- It passes only root-relative Agent Server paths to `host.agentServer.request`.
- Commands run with the permissions and command policy of the active backend's Agent Server.
- Only one command request runs at a time, with a 300-second requested timeout.
- Late results are ignored after the page unmounts.
