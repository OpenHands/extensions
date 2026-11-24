# Sidecar-backed Apps

Use this reference when an App needs a service in addition to its browser bundle. Choose either an optional package-owned managed backend, when the target Agent Server and Canvas host expose that capability, or a manual/deployment-owned Sidecar. Browser-only Apps remain valid.

The managed-backend contract is available on the stacked, unreleased Agent Server changes in [software-agent-sdk PR #5270](https://github.com/OpenHands/software-agent-sdk/pull/5270) at `ac7b322ddf7d2e0e90a3643c5e26d848236af9a3` and [PR #5272](https://github.com/OpenHands/software-agent-sdk/pull/5272) at `6d9c82973e765cce4843d6a2fb52f634efa64293`. Until a release containing both lands, those exact revisions are the minimum Agent Server implementation. Feature-detect `canvas_app_backend_bridge_v1` in `GET /server_info`; absence means the managed view path is unsupported, not that the App should guess a port or fall back to hidden Canvas state. Use the host helper only at the minimum host version documented in [v1-contract.md](v1-contract.md).

## Keep three boundaries

1. **Canvas App UI**: always ship `canvas-extension.json` and exactly one self-contained browser ESM entrypoint exporting `activate(host)`. Bundle UI dependencies, CSS, and required assets into that entrypoint.
2. **Service distribution and ownership**: for a managed backend, declare checksum-pinned platform artifacts in the same package and let the owning Agent Server prepare and run them. For a manual Sidecar, distribute and operate the service separately. Do not combine the models or add a general install hook.
3. **Onboarding and operator layer**: implement this as guided UI in the App view. Present status, disclosures, explicit revision-bound consent, and lifecycle actions there. Installing or enabling the App never authorizes backend preparation or startup.

## Declare a package-owned managed backend

Add the optional `backend` block only when the App owns its service artifacts:

```json
{
  "backend": {
    "schema_version": 1,
    "artifacts": {
      "linux-amd64": {
        "path": "backend/linux-amd64.tar.gz",
        "sha256": "<64 lowercase hex characters>"
      },
      "linux-arm64": {
        "path": "backend/linux-arm64.tar.gz",
        "sha256": "<64 lowercase hex characters>"
      }
    },
    "argv": [
      "{artifact_dir}/bin/server",
      "--host=127.0.0.1",
      "--port={port}",
      "--data-dir={data_dir}"
    ],
    "health": {
      "path": "/health",
      "timeout_seconds": 30,
      "interval_seconds": 0.1
    },
    "inherit_environment": ["LANG", "PATH", "TZ"]
  }
}
```

Artifact paths are package-relative `.tar.gz` files. The executable in `argv[0]` must resolve inside `{artifact_dir}`. The argv is a structured string list, never shell source; supported placeholders are `{artifact_dir}`, `{data_dir}`, and `{port}`. The current server supports Linux amd64 and arm64 and reports other platforms as `unsupported`.

## Choose a connection boundary

Prefer connection patterns in this order:

1. **Managed backend view**: for a package-owned backend, feature-detect `host.appBackendView` and call `host.appBackendView.mount({ container })`. Canvas owns session creation, iframe isolation, ingress validation, and revocation.
2. **Narrow Agent Server bridge**: for a manual Sidecar, add a backend-owned, authenticated endpoint for only the required operations and call it through `host.agentServer.request` with root-relative paths. Keep Sidecar credentials and routing on the backend.
3. **Documented deployment capability**: require a deployment adapter that deliberately exposes Sidecar access, feature-detect it, and document its version and contract.
4. **Direct browser connection only when explicitly non-portable**: document its origin, authentication, exposure, and deployment ownership. Do not represent this design as a portable host API 1 App.
5. **Bounded polling through the Agent Server**: use a narrow bridge for status where live events are unavailable in v1. Bound intervals, respect visibility, abort on disposal, and show stale state.

Reject guessed localhost names or ports, `window.location` derivation, Canvas internals, undocumented globals, and embedded credentials. Do not attempt to route a Sidecar or Automation call through `host.agentServer.request` without a documented Agent Server bridge.

## Model onboarding and operations

For a managed backend, use the server states exactly: `missing`, `stopped`, `starting`, `ready`, `unhealthy`, and `unsupported`. For a manual Sidecar, model additional UI-only states such as `unknown`, `probing`, and `incompatible` when needed. Preserve actionable failures and transition deliberately for consent, prepare/install, start, repair, upgrade, and stop failures.

Before any mutating action, disclose the source, resolved revision, version, checksums, install and data paths, ports and network exposure, process behavior, inherited environment names, and rollback or uninstall behavior. Obtain explicit consent for each applicable action. Managed-backend prepare and start calls carry the exact installed revision; updating the package invalidates prior approval.

Keep these actions separate and idempotent where meaningful:

- Probe
- Install
- Recheck
- Start
- Stop
- Repair
- Upgrade
- View logs
- Uninstall service
- Delete data

Make App removal, service uninstall, and data deletion distinct choices. Never delete Sidecar data because the App is disabled or removed.

## Narrow the service contract

Expose health, version, capabilities, and domain-specific operations only. Apply request timeouts, input validation, structured errors, and authentication whenever binding beyond a loopback boundary. Avoid a general shell, filesystem, process, or arbitrary URL API.

Persist service state and data in declared service-owned locations, not beside the installed App bundle. Keep secrets out of the browser package, manifest, logs, and mutable bundle-adjacent files; use the deployment's secret mechanism or a backend-owned bridge.

Canvas activation, page mounts, disposal, backend switches, and reconnects can repeat independently of a long-lived service. Make UI probes and subscriptions disposable, do not start or stop the Sidecar during ordinary mounts, and revalidate readiness after restart, version mismatch, or backend switching.
