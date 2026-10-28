# Repository guidance

- This repository contains the `terminal` App for Agent Canvas.
- Run `npm run check` after changes. It type-checks, tests, builds the single-file extension, validates it, and runs a Chromium Blob-import command smoke.
- `src/` builds the required self-contained Canvas `extension.js`, including xterm.js and shadow-scoped styles.
- The App is a command runner over host API 1, not a persistent PTY. Every submitted line calls `host.agentServer.request` with `POST /api/bash/execute_bash_command`, the backend home as `cwd`, and a bounded timeout.
- Never add a sidecar, direct fetch, WebSocket, API-key input/discovery, localStorage access, Canvas-internal state inspection, guessed backend URL, iframe, hosted SPA, or provisioning flow.
- Let Canvas select the active backend and attach authentication through `host.agentServer.request`.
- Keep the UI terminal-only. Explain request errors in xterm and its narrow status strip.
- Run only one command at a time and ignore late request results after unmounting.
- Every mount must remove light and shadow DOM, observers, terminal subscriptions, styles, and the xterm instance.
- The app targets manifest schema 1 and host API 1.
- Do not install, enable, publish, push, or deploy the App unless the user explicitly asks.

## Current host deployment

- Production source is `/root/git/canvas-app-terminal`.
- The legacy `canvas-app-terminal.service` sidecar must remain disabled and its `/opt/canvas-app-terminal` runtime removed.
- The installed Canvas identity is `terminal`; the obsolete `backend-terminal` installation must remain uninstalled.
- After source changes, run `npm run check` and force-refresh `terminal` through `/api/canvas-extensions/install` using the active Agent Server credential.
