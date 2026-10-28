# Extension Lab

A capability test bench and pattern gallery for Canvas extension authors — see what works, what doesn't, and copy the code.

## What it does

Extension Lab runs live tests of every technique a Canvas extension can use, showing a pass/fail badge for each. It's the reference for "can I do X in an extension?"

## Pages

1. **Dashboard** (`/lab`) — A grid of capability cards, each running a live test:
   - Vanilla DOM manipulation
   - Inline blob ESM module imports
   - CDN dynamic imports (esm.sh)
   - CSS variable theming (`--oh-*`)
   - localStorage persistence (per-backend)
   - Web Workers (from blob URLs)
   - Web Components (custom elements with Shadow DOM)
   - Agent Server API (`host.agentServer.request()`)
   - ResizeObserver
   - IndexedDB
   - MutationObserver

2. **Pattern Gallery** (`/lab/patterns`) — Copy-paste code snippets for each working capability, plus a list of known limitations (relative imports, bare imports, extension folder assets, Node.js APIs).

3. **Stress Test** (`/lab/stress`) — Mount/unmount loops, leak detection, localStorage quota, concurrent async with cancellation, and rapid custom element recreation.

## Build

```sh
npm install
npm run build
```

The build copies the self-contained source to `extension.js`. No bundler is needed.

## Test

```sh
npm test
```

## Install in Agent Canvas

Use **Customize → Extensions → Add Extension** with:

- **Source**: local path to this directory
- Or `github:owner/repo` with repo path `extension-lab`
