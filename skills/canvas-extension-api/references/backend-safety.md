# Backend safety and persistence

Use `host.agentServer.request({ method, path, body })` only with root-relative paths that begin with exactly one `/`. Do not derive the Agent Server URL from `window.location`, read Canvas credentials, put secrets in `VITE_*`, or open a direct Agent Server WebSocket under host API 1. Validate complete response shapes and suppress late updates after unmount.

For command-backed Apps, expose fixed command templates only. Validate paths, pass them as structured `cwd`, encode variable input structurally (for example JSON plus base64), validate it again in the helper, and emit structured responses. Never interpolate user text into shell source or expose a general terminal.

Keep browser-local data namespaced by App name and backend ID in IndexedDB/OPFS/localStorage. Put backend-shared mutable state below `<agent-server-home>/.openhands/apps/<app-name>/`, after discovering the home through `GET /api/file/home` and validating the absolute path. Never write mutable state beside the installed manifest or bundle.

For a CLI, binary, compiler, database, or Sidecar, read [sidecar-pattern.md](sidecar-pattern.md). Probe without mutation; disclose exact downloads, builds, data paths, checksums, and process behavior; and gate installation behind acknowledgement. Do not expose general command execution, shell interpolation, silent or unpinned downloads, unauthenticated non-loopback binding, mutable state beside the installed bundle, or automatic data deletion when an App is removed.

## Package-owned managed backends

The managed-backend contract requires the stacked, unreleased Agent Server changes in [software-agent-sdk PR #5270](https://github.com/OpenHands/software-agent-sdk/pull/5270) at `ac7b322ddf7d2e0e90a3643c5e26d848236af9a3` and [PR #5272](https://github.com/OpenHands/software-agent-sdk/pull/5272) at `6d9c82973e765cce4843d6a2fb52f634efa64293`. Until a release containing both lands, those exact revisions are the minimum Agent Server implementation. Feature-detect `canvas_app_backend_bridge_v1` through `GET /server_info`; never infer support from an endpoint failure, Canvas internals, or a guessed port. Use the host helper only at the minimum host version documented in [v1-contract.md](v1-contract.md).

A managed backend is declarative, not an install hook. Installation, enablement, activation, and ordinary page mounts never prepare or start it. Show the resolved revision and backend declaration, then require explicit user consent before calling prepare and start with that exact revision. Updating or replacing the package invalidates approval. Never put a credential in the manifest, argv, browser bundle, URL, or log.

For embedded backend views, require the configured ingress to be a separate browser origin from Canvas. That origin is the isolation boundary. Apply the server-returned sandbox exactly, including `allow-same-origin`; removing it breaks Origin validation, partitioned-cookie delivery, and Worker creation in Chromium. Do not replace origin isolation with an opaque sandbox origin.

The Agent Server selects the current platform artifact, verifies its lowercase SHA-256 checksum, extracts it safely to immutable content-addressed storage, and runs only the declared structured argv without a shell. The executable must remain inside `{artifact_dir}`. Supported placeholders are `{artifact_dir}`, `{data_dir}`, and `{port}`. Inherited environment names are restricted to the server's non-credential allowlist; ambient Agent Server credentials do not flow to the child.

Only local Linux amd64 and arm64 artifacts are supported initially. Treat `unsupported` as an explicit UI state. The owned process is constrained by its launch contract and process group but is not OS-isolated; run untrusted backend code only inside a suitably isolated Agent Server runtime.

Backend data belongs to the service independently of the installed bundle. Disable and uninstall stop the owned process and revoke browser sessions but preserve mutable data. Data deletion is a separate explicit action. Installed Apps and their backends belong to one Agent Server; do not assume a service or its data is shared across isolated conversation runtimes.
