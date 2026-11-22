# Whiteboard App

An [Excalidraw](https://github.com/excalidraw/excalidraw) whiteboard for Agent Canvas. Boards autosave to the active Agent Server as standard `.excalidraw` files, so they can be opened in excalidraw.com or read by an agent on the same server.

Install it in Agent Canvas from **Customize → Apps → Add app** with:

```text
https://github.com/OpenHands/extensions
```

and the path `apps/whiteboard`.

## Pages and boards

The manifest declares one `board` page at `/boards`, so board URLs read `/extensions/whiteboard/boards/<id>`: `whiteboard` is the App name and `boards` the page path.

- `/extensions/whiteboard/boards` reopens the last board you used in this browser (the `default` board the first time).
- `/extensions/whiteboard/boards/<id>` opens a specific board. Ids use lowercase letters, digits, and hyphens.

The board button next to Excalidraw's main-menu button opens the board picker. (In Excalidraw's compact layout, where the menu moves to the bottom bar, the button sits in the top toolbar instead.)

- **Switch**: lists boards, most recently edited first.
- **Create**: name a board. Its id is derived from the name plus a short random suffix (for example `sprint-plan-k3x9`).
- **Rename board**: changes the title; the id and URL stay the same.
- **Archive board**: hides the board from the list after a confirmation. The Agent Server file API has no delete, so its files stay on disk.

## Storage

Each board is a directory below `<agent-server-home>/.openhands/apps/whiteboard/boards/<id>/`:

- `board.excalidraw`: a standard Excalidraw document.
- `meta.json`: `{ "title", "createdAt", "updatedAt", "archived"? }`.

The file API can list directories but not files, so the board list comes from those directories rather than a shared index. That also means two tabs creating boards never write the same file. A board directory without `meta.json` still appears, titled from its id.

Edits are saved about a second after the drawing changes and when the page unmounts. Pointer movement, zoom, and selection do not trigger writes. Saving refreshes `updatedAt` at most once a minute. The light/dark theme is not part of an `.excalidraw` file, so it is remembered per browser and backend in `localStorage`, together with the last board opened.

Two tabs editing the same board overwrite each other (last write wins).

## How the bundle stays fast

Canvas fetches and imports every enabled App's entrypoint when it starts, but Excalidraw and React are about 2 MB of minified JavaScript. `build.mjs` builds in two stages:

1. `src/board.jsx` (React, Excalidraw, its CSS, and fonts) is bundled, gzipped, and base64-encoded.
2. `src/extension.js`, the small shell that registers the page and owns persistence, embeds that payload as a string constant.

Importing the shell at Canvas startup parses one string literal (about 6 ms in Chrome). The first time the page opens, the shell decodes the payload with `Uint8Array.fromBase64`, decompresses it with `DecompressionStream`, and imports it from a Blob URL (about 150 to 200 ms). Later visits during the same activation reuse the evaluated module, so a remount takes about 10 ms. The artifact is still one self-contained ESM file.

The build also resolves Excalidraw's lazily loaded assets so nothing is fetched at runtime:

- Fonts are embedded as `data:` URLs. The 12 MB Xiaolai CJK font is left out, and Excalidraw is prevented from falling back to its CDN for it.
- Only the English locale is bundled.
- The Mermaid-to-Excalidraw dialog is stubbed out because it would add several megabytes.
- Font subsetting for SVG export (1.7 MB of WebAssembly) is replaced with Excalidraw's own fallback, which embeds the whole font face. Exported SVGs are larger, but otherwise the same.

Excalidraw's stylesheet is injected only while the page is mounted. It defines a few `:root` custom properties and unscoped class names, all prefixed or specific to Excalidraw.

## Develop and verify

Requirements: Node.js 22 or newer, npm, and Google Chrome for the Blob smoke test (set `CHROME_PATH` if Chrome is installed elsewhere).

```sh
npm ci
npm run check
```

`npm run build` writes the checked-in `extension.js`. `npm test` runs the unit tests against the built bundle and the store. `npm run test:blob` imports the bundle from a Blob URL in headless Chrome, draws a rectangle, checks the autosave upload, creates a board from the picker with real keystrokes, and verifies cleanup and remounting. It also fails if the page makes any network request.

To test in a local Agent Canvas, install this directory as a local path from **Customize → Apps → Add app**, enable it, and open **Whiteboard** in the sidebar. After rebuilding, use **Update** on the App card to reload the bundle.
