# Testing and installing OpenHands Apps

Use layered verification: static package checks, unit tests against the real entrypoint, repository build checks, then a manual Canvas lifecycle test.

## Static validation

Run:

```sh
node /path/to/canvas-extension-api/scripts/validate-extension.mjs /path/to/app-package
```

The validator checks:

- app package directory and `canvas-extension.json` existence;
- valid JSON and supported `schema_version`;
- required fields and basic semantic version shape;
- kebab-case app manifest name, contribution IDs, and path segments;
- unique page IDs and paths;
- entrypoint containment and existence;
- `activate` export presence;
- likely bare imports, remote imports, Node built-ins, dynamic imports, and source-map chunk references;
- `registerPage` IDs against declared manifest IDs.

Treat static import scanning as heuristic. Minified or generated bundles may require manual inspection. Treat a passing result as necessary but not sufficient. When using `--dist`, the validator checks the manifest entrypoint path under `dist/`, so a manifest entrypoint such as `bundle.mjs` requires `dist/bundle.mjs`.

## Sidecar test matrix

Test the browser bundle independently from the Sidecar: load the single ESM entrypoint through Blob import and confirm no service secret or origin assumption is embedded. Test the narrow bridge or deployment adapter with real request shapes and error handling. Test real Sidecar health, version, capabilities, and domain operations, including timeouts and structured failures.

Exercise `unknown`, `probing`, `missing`, `stopped`, `incompatible`, `ready`, and `unhealthy` onboarding states plus consent, install, start, repair, upgrade, and stop failures. Test repeated lifecycle actions, service restarts, version mismatches, backend switching, and Canvas remounts. Test App removal, service uninstall, and data deletion as distinct operations. Treat an unavailable Sidecar as a supported UI state, not a crash.

## Unit test shape

Exercise the actual app entrypoint in a DOM test environment. Keep the host double small and behavior-oriented.

```js
import { describe, expect, it, vi } from "vitest";
import { activate } from "./extension.js";

describe("example app", () => {
  it("mounts, requests backend data, and cleans up", async () => {
    let mountPage;
    const unregister = vi.fn();
    const navigate = vi.fn();
    const request = vi.fn().mockResolvedValue({ status: "ok" });
    const host = {
      apiVersion: "1",
      extension: {
        name: "example-dashboard",
        version: "0.1.0",
        resolvedRef: "test-ref",
      },
      backend: { id: "local-test", kind: "local", orgId: null },
      registerPage: vi.fn((id, mount) => {
        expect(id).toBe("dashboard");
        mountPage = mount;
        return unregister;
      }),
      navigate,
      agentServer: { request },
    };

    expect(activate(host)).toBe(unregister);

    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate });

    await vi.waitFor(() => {
      expect(container.textContent).toContain("ok");
    });
    expect(request).toHaveBeenCalledWith({ path: "/example" });

    cleanup();
    expect(container.childElementCount).toBe(0);
  });
});
```

Add focused cases for nested routes, error states, malformed responses, loading deduplication, timers, and unsupported host versions as applicable.

Prefer real timers for lifecycle behavior unless waiting would make the suite impractical. When fake timers are necessary, state why in the test and restore them after each case.

## Build verification

For a source-based TypeScript, React, Vue, or other framework implementation, configure the bundler in library mode and emit one browser ESM file matching the manifest entrypoint.

Required output properties:

- ESM format;
- one JavaScript file;
- no unresolved bare imports;
- no external chunks;
- no Node runtime assumptions;
- CSS injected or embedded when the runtime cannot fetch additional package assets;
- small local assets embedded as data URLs or otherwise included in the single bundle.

Inspect output using repository tooling and direct searches. Example checks:

```sh
node --check dist/extension.js
rg '^\s*(import|export\s+.*\s+from)\s+.*["'"'][^./]' dist/extension.js
rg 'import\s*\(' dist/extension.js
rg 'node:|require\(|module\.exports|process\.env|__dirname|__filename' dist/extension.js
```

Do not run the browser bundle directly with Node as a functional test. Use a DOM test environment or Canvas.

## Upstream mock frontend workflow

The initial OpenHands frontend includes an MSW development mode that can install a checked-in fixture before Agent Server app endpoints are available.

From an OpenHands checkout:

```sh
VITE_FRONTEND_PORT=3102 \
VITE_BACKEND_BASE_URL=http://127.0.0.1:8000 \
VITE_SESSION_API_KEY=canvas-extension-dev \
npm run dev:mock
```

Open:

```text
http://localhost:3102/extensions
```

Install a fixture path that exists inside that OpenHands checkout, such as:

```text
src/fixtures/canvas-extensions/demo-page
```

The mock flow validates frontend inventory, enablement, bundle loading, page registration, nested routing, and cleanup. It does not validate Agent Server installation, filesystem boundaries, persistence, authentication, Git resolution, symlinks, or immutable revisions.

To test a separately located app with this mock, copy it into a suitable fixture path only when authorized and avoid copying secrets-bearing files. Prefer adding a temporary ignored fixture or using the backend flow once available. Remove temporary copies after testing.

## Real Agent Server installation

Use Customize -> Apps when available, or the authenticated management API when explicitly requested.

### Backend-local path

Use a path visible from the Agent Server process. A path visible only on the frontend host is insufficient when the backend runs in a container, remote VM, or different filesystem namespace.

Install request shape:

```json
{
  "source": "/absolute/path/on/agent-server",
  "ref": null,
  "repo_path": null,
  "force": false
}
```

### Git repository

Use distribution coordinates compatible with the backend:

```json
{
  "source": "github:owner/repository",
  "ref": "main",
  "repo_path": "extensions/example-dashboard",
  "force": false
}
```

For a repository containing the app at its root, omit `repo_path`. Pin or report the resolved revision returned by the backend.

### Multiple apps in one repository

Place each app under an independent package root:

```text
repository/
├── extensions/
│   ├── canvas-pulse/
│   │   ├── canvas-extension.json
│   │   ├── extension.js
│   │   └── extension.test.js
│   └── project-dashboard/
│       ├── canvas-extension.json
│       ├── dist/
│       │   └── extension.js
│       └── src/
├── packages/
│   └── shared-source/
└── package.json
```

Keep each manifest's `entrypoint` relative to that app's package root. Configure shared build tooling to emit one self-contained browser ESM bundle per app. Do not make one app entrypoint import another app's output at runtime; Blob URL loading prevents package-relative module resolution.

Validate each package separately:

```sh
for extension in extensions/*; do
  node /path/to/validate-extension.mjs "$extension"
done
```

The Add app form installs one app per submission. It sends one `source`, optional `ref`, and optional `repo_path` in each install request. It does not scan a repository recursively, discover all `canvas-extension.json` files, or bulk-install nested apps.

Install the example repository twice:

| Extension | Source | Ref | Repository path |
| --- | --- | --- | --- |
| Canvas Pulse | `github:owner/repository` | `main` | `extensions/canvas-pulse` |
| Project Dashboard | `github:owner/repository` | `main` | `extensions/project-dashboard` |

Each installation receives its own resolved revision, enabled state, lifecycle, and inventory entry. Installation leaves each one disabled; enable each separately after review and authorization.

When preparing instructions for several apps, generate an install matrix rather than saying to add the repository once. Keep the source/ref identical when appropriate and vary `repo_path` for each package root.

Do not upload or publish a local app unless requested. Do not embed credentials in a source URL.

## Manual lifecycle checklist

Complete these checks against the target backend:

### Installation

- Confirm the app appears in Customize -> Apps.
- Confirm installation leaves it disabled.
- Confirm the displayed name, version, description, source, requested ref, resolved ref, and contributions.
- Confirm no navigation item appears and no app code executes while disabled.

### Enablement

- Read the trusted-code disclosure.
- Enable only with user authorization.
- Confirm the page navigation item appears without restarting Canvas.
- Open the page and verify loading, success, empty, and failure states.
- Verify authenticated Agent Server requests target the active owning backend.

### Routing

- Open the declared root route.
- Open at least one nested route directly.
- Confirm the mount callback receives only the remainder below the declared page path.
- Confirm app navigation respects the Canvas base path.
- Confirm the longest declared page path wins when page paths overlap.

### Cleanup

- Navigate away and verify page-level timers, listeners, observers, and DOM are removed.
- Disable the app and confirm all page registrations and navigation disappear.
- Re-enable and confirm the app activates cleanly a second time.
- Update or reinstall when applicable and confirm stale effects do not remain.
- Switch backend or reconnect and confirm the previous backend's app does not leak into the new context.

### Removal

- Uninstall only when explicitly requested.
- Confirm the inventory, navigation, and routes no longer expose the app.

## Diagnosing common failures

### App is listed but has no page

Check that the installed API response includes the parsed manifest. The frontend treats `manifest` as optional for compatibility with Agent Server versions that omit it. Without `manifest.contributes.pages`, Canvas cannot admit page registrations or render navigation.

Check that the app is enabled and that `registerPage` uses an ID declared in the manifest.

### Entrypoint fails to import

Check for unresolved package imports, extra chunks, remote imports, syntax errors, top-level Node globals, or code that expects a normal URL instead of a Blob module URL.

Remember that relative imports from a Blob URL cannot resolve to files in the installed package. Bundle everything into the entrypoint.

### Agent Server request fails before network activity

Ensure `path` begins with exactly one `/`. Do not use an absolute URL, protocol-relative URL, or relative path.

### Nested path is wrong

Treat the mount `path` as a route remainder without a leading slash. Build navigation URLs from `/extensions/{encoded-extension-name}/{declared-page-root}` and encode user-controlled route segments.

### UI duplicates after re-enable

Return all activation and mount disposers. Remove injected style elements, stop timers, detach listeners, and prevent late async callbacks from writing after disposal.

### App works locally but not from Git

Confirm the manifest and built entrypoint are committed, the requested ref contains them, `repo_path` points at the directory containing `canvas-extension.json`, and generated output is not excluded from publication.
