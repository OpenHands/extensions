# Backend safety and persistence

Use `host.agentServer.request({ method, path, body })` only with root-relative paths that begin with exactly one `/`. Do not derive the Agent Server URL from `window.location`, read Canvas credentials, put secrets in `VITE_*`, or open a direct Agent Server WebSocket under host API 1. Validate complete response shapes and suppress late updates after unmount.

For command-backed Apps, expose fixed command templates only. Validate paths, pass them as structured `cwd`, encode variable input structurally (for example JSON plus base64), validate it again in the helper, and emit structured responses. Never interpolate user text into shell source or expose a general terminal.

Keep browser-local data namespaced by App name and backend ID in IndexedDB/OPFS/localStorage. Put backend-shared mutable state below `<agent-server-home>/.openhands/apps/<app-name>/`, after discovering the home through `GET /api/file/home` and validating the absolute path. Never write mutable state beside the installed manifest or bundle.

For a CLI, binary, compiler, database, or Sidecar, read [sidecar-pattern.md](sidecar-pattern.md). Probe without mutation; disclose exact downloads, builds, data paths, checksums, and process behavior; and gate installation behind acknowledgement. Do not expose general command execution, shell interpolation, silent or unpinned downloads, unauthenticated non-loopback binding, mutable state beside the installed bundle, or automatic data deletion when an App is removed.
