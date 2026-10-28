# Vite Showcase

Vite Showcase is a standalone Agent Canvas App demonstrating that a conventional Vite 8, React 19, and TypeScript project can ship as one authenticated, self-contained browser ESM bundle.

The checked-in `extension.js` is installable without building. Its modular source includes React, inline CSS, an SVG asset, JSON, raw Markdown, a source-level dynamic import, and an inline Web Worker. Production emits no runtime chunks or sibling assets.

## Pages

The manifest declares one `showcase` page at `/showcase`. The App handles nested mount paths itself:

- `/showcase` (and `/showcase/overview`) — packaging overview
- `/showcase/architecture` — source-to-artifact map and lazy module result
- `/showcase/diagnostics` — host, App, backend, route, and Worker diagnostics

Unknown nested routes show a recovery screen with a route back to the showcase root. Use the header navigation or `Alt+1`, `Alt+2`, and `Alt+3` inside the mounted App.

## Develop and verify

Requirements: Node.js 22.12 or newer and npm.

```sh
npm install
npm run check
```

Run commands from this `vite-showcase` directory. `npm run check` type-checks the source before the other validations. `npm run build` creates `dist/extension.js`, verifies that it is the only emitted file and contains no unresolved module or sibling-asset references, then synchronizes it to the checked-in root `extension.js`. `npm test` covers activation, manifest registration, nested routing, unsupported API rejection, diagnostics, cleanup, and remounting. `npm run test:blob` launches the installed Google Chrome binary headlessly, imports the checked-in bundle through a Blob URL, and exercises activation, Worker execution, navigation, disposal, and remounting. Set `CHROME_PATH` if Chrome is installed elsewhere.

## Local Canvas acceptance checklist

The Apps screen currently has no refresh action. After rebuilding, uninstall and reinstall the App rather than expecting Canvas to refresh its bundle.

1. From this directory, run `npm install` and `npm run check`.
2. Resolve this directory's absolute path with `pwd`.
3. In Agent Canvas, open **Settings → Apps**, choose **Install from local path**, and paste the absolute `vite-showcase` directory path.
4. Enable **Vite Showcase** and open it from the navigation.
5. Visit Overview, Architecture, and Runtime Diagnostics. Confirm that diagnostics show the active host/App/backend metadata, nested path, and `fibonacci(32) = 2178309` Worker result.
6. Try an unknown nested URL and use **Return to showcase root**.
7. Reload Canvas and confirm the App still opens and navigates.
8. Disable the App, confirm its page is unavailable, then re-enable it and repeat a mount/navigation check.
9. For any source change: rebuild, uninstall, reinstall from the same absolute path, and retest.

## Runtime and persistence

Vite Showcase uses only browser APIs and the Canvas host context. It installs no CLI, downloads nothing, starts no background process, and stores no mutable data. Mount cleanup aborts pending lazy work, removes the keyboard listener and injected styles, terminates the Worker, and unmounts React.
