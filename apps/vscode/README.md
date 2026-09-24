# VS Code App

This App provides a full-height OpenVSCode editor. Before the backend is ready, the App shows backend status, an explicit workspace-folder input, and revision-bound prepare/start/stop/refresh actions. Once ready, the page contains only the editor iframe. The folder is persisted in browser storage and sent as an optional `query.folder` mount parameter; it is a user convenience, not OS sandboxing.

## Artifact delivery

The repository intentionally contains no OpenVSCode binaries. `scripts/package.mjs` downloads the pinned upstream OpenVSCode Server `v1.109.5` Linux amd64 and arm64 archives, verifies their upstream checksums, normalizes the archive layout and metadata, and writes the package-contained archives required by `canvas-extension.json`. The GitHub Actions workflow publishes the resulting `vscode-app-<commit>` artifact; that archive is the installable coordinate for this revision.

The package is not a release until reviewed and merged. The workflow artifact is a development delivery coordinate, not a published release or a version pin for Agent Server. This App depends on the Canvas consumer change that adds optional `mount({ container, query: { folder } })` support; until that consumer PR lands, setup works but the selected folder is not forwarded to OpenVSCode.

The backend uses app-owned data directories for user data and extensions and receives only the manifest allowlisted environment. It does not receive Agent Server credentials. OpenVSCode starts at the existing app-owned `{data_dir}` by default; the optional folder query changes the editor folder only when the Canvas consumer supports it. Folder selection is not OS sandboxing.

The real ngrok editor/save/terminal click-through GIF is maintained in the Agent Canvas implementation PR as development-stack evidence. It is not bundled here and is not a release or package test.
