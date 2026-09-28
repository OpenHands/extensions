# Sidecar-backed Apps

Use this reference when an App needs a separately installed service. Host API 1 supports a browser App package and authenticated Agent Server HTTP requests; it does not provide Sidecar installation, process management, connection brokering, Automation adaptation, arbitrary install hooks, or an Agent Server WebSocket capability.

## Keep three boundaries

1. **Canvas App package**: ship `canvas-extension.json` and exactly one self-contained browser ESM entrypoint exporting `activate(host)`. Bundle UI dependencies, CSS, and required assets into that entrypoint.
2. **Sidecar distribution**: distribute the service, its versioned artifacts, and its service-specific installation and operation mechanism separately.
3. **Onboarding and operator layer**: implement this as a guided UI in the App view. Present status, disclosures, explicit consent, and lifecycle actions there. Do not infer that installing or enabling the Canvas App authorizes any Sidecar mutation.

## Choose a connection boundary

Prefer connection patterns in this order:

1. **Narrow Agent Server bridge**: add a backend-owned, authenticated endpoint for the required Sidecar operations and call it through `host.agentServer.request` with root-relative paths. Keep Sidecar credentials and routing on the backend.
2. **Documented future or deployment capability**: require a host or deployment adapter that deliberately exposes Sidecar access, feature-detect it, and document the required version and deployment contract.
3. **Direct browser connection only when explicitly non-portable**: document its origin, authentication, exposure, and deployment ownership. Do not represent this design as a portable host API 1 App.
4. **Bounded polling through the Agent Server**: use a narrow bridge for status where live events are unavailable in v1. Bound intervals, respect visibility, abort on disposal, and show stale state.

Reject guessed localhost names or ports, `window.location` derivation, Canvas internals, undocumented globals, and embedded credentials. Do not attempt to route a Sidecar or Automation call through `host.agentServer.request` without a documented Agent Server bridge.

## Model onboarding and operations

Represent service state explicitly: `unknown`, `probing`, `missing`, `stopped`, `incompatible`, `ready`, and `unhealthy`. Preserve actionable failures and transition deliberately for consent, install, start, repair, upgrade, and stop failures. Treat unavailable Sidecar status as a supported UI state.

Before any mutating action, disclose the source, version, checksum, install and data paths, ports and network exposure, process behavior, credentials, and rollback or uninstall behavior. Obtain explicit consent for each applicable action.

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
