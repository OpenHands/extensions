# Canvas Extensions API v1 contract

Use this reference for manifest schema 1 and host API 1 as implemented by the initial Apps frontend landing.

## Authoritative sources

Upstream repository: <https://github.com/OpenHands/OpenHands>

Initial frontend landing: [PR #16895](https://github.com/OpenHands/OpenHands/pull/16895), `feat: land the Canvas Extensions frontend (load pages, sidebar, customize)`.

Inspect these files when targeting a newer OpenHands revision:

- `specs/canvas-extensions.md` - product decisions and package contract.
- `src/types/canvas-extension.ts` - TypeScript source of truth for host API types.
- `src/extensions/canvas-extension-module-loader.ts` - ESM loading and `activate` validation.
- `src/components/features/canvas-extensions/canvas-extensions-runtime.tsx` - registration, activation, disposal, and backend scoping.
- `src/routes/canvas-extension-page.tsx` - route matching and mount lifecycle.
- `src/api/canvas-extensions-service.ts` - management endpoints and authenticated Agent Server request behavior.
- `src/fixtures/canvas-extensions/demo-page/` - minimal dependency-free fixture.
- `docs/CANVAS_EXTENSIONS_TESTING.md` - mock frontend workflow.

## Product and trust model

Treat the active Agent Server as the owner of installed apps. Source, resolved revision, files, manifest, and enabled state live on that backend. Switching backend replaces the active app inventory.

Treat enabled code as trusted same-realm JavaScript. No iframe, worker sandbox, granular permission boundary, or CSS security boundary exists in v1. Enabled code has the ambient browser authority available to Canvas and can use authenticated helpers for the current backend.

Keep install and enable separate. Installation produces a disabled app. Enabling is the explicit execution consent point. Enablement and disablement are hot and require no restart.

## Manifest schema 1

Filename: `canvas-extension.json` at the app package root.

```ts
interface CanvasExtensionManifest {
  schema_version: 1;
  name: string;
  display_name?: string | null;
  version: string;
  description?: string | null;
  entrypoint: string;
  contributes?: {
    pages?: CanvasExtensionPageContribution[] | null;
  } | null;
}

interface CanvasExtensionPageContribution {
  id: string;
  title: string;
  path: string;
  nav_label?: string | null;
  description?: string | null;
}
```

Required manifest fields are `schema_version`, `name`, `version`, and `entrypoint`. A useful page package also supplies `display_name`, `description`, and at least one `contributes.pages` entry.

Apply these rules:

- Match app manifest names and contribution IDs against `^[a-z0-9]+(?:-[a-z0-9]+)*$`.
- Begin each page path with `/`.
- Use one or more kebab-case route segments for each page path.
- Keep the entrypoint inside the installed app package root.
- Produce one self-contained browser ESM entrypoint.
- Bundle or embed dependencies, CSS, and small assets.
- Leave no unresolved bare imports or external output chunks.

The frontend normalizes the declared leading slash away for internal route matching. It validates the app manifest name, contribution ID, and every path segment before admitting the page.

## Host API 1

```ts
interface CanvasExtensionHost {
  readonly apiVersion: "1";
  readonly extension: Readonly<{
    name: string;
    version: string;
    resolvedRef: string | null;
  }>;
  readonly backend: Readonly<{
    id: string;
    kind: "local" | "cloud";
    orgId: string | null;
  }>;
  registerPage(
    contributionId: string,
    mount: CanvasExtensionPageMount,
  ): () => void;
  navigate(path: string): void;
  agentServer: {
    request<T = unknown>(request: {
      method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
      path: string;
      body?: unknown;
      headers?: Record<string, string>;
    }): Promise<T>;
  };
}

type CanvasExtensionPageMount = (context: {
  container: HTMLElement;
  path: string;
  navigate(path: string): void;
}) => void | (() => void) | Promise<void | (() => void)>;
```

The ESM entrypoint must export:

```ts
export function activate(
  host: CanvasExtensionHost,
): void | (() => void) | Promise<void | (() => void)>;
```

The loader fetches authenticated JavaScript text, creates a temporary Blob URL, imports it as ESM, verifies the `activate` export, and revokes the Blob URL. Import does not activate a disabled installation.

## Registration constraints

Register each page during activation using exactly the page ID declared in the manifest. The runtime rejects undeclared IDs and duplicate registrations.

Return the unregister function from `activate` for a single contribution, or collect multiple unregister functions and return one disposer:

```js
export function activate(host) {
  const disposers = [
    host.registerPage("overview", mountOverview),
    host.registerPage("settings", mountSettings),
  ];
  return () => {
    for (const dispose of disposers.reverse()) dispose();
  };
}
```

The runtime invokes activation cleanup and registration cleanup when disabling, uninstalling, updating, switching backend, reconnecting, or otherwise replacing the activation inventory. Cleanup errors are logged and do not prevent later cleanup attempts.

## Routing

Canvas mounts a declared page under:

```text
/extensions/{extension-name}/{declared-page-path}
```

For an app `canvas-pulse` and page path `/pulse`, the root URL is:

```text
/extensions/canvas-pulse/pulse
```

A visit to:

```text
/extensions/canvas-pulse/pulse/services/agent_server
```

selects the longest matching declared page path and passes this remainder to the mount callback:

```text
services/agent_server
```

Use the mount callback's `navigate` function, or `host.navigate`, rather than manipulating history directly. Pass a Canvas path, typically an absolute path such as `/extensions/canvas-pulse/pulse`.

The route is base-path aware through React Router. Avoid constructing browser origins or assuming Canvas runs at `/`.

## Agent Server requests

Use `host.agentServer.request` to target the app-owning backend with Canvas authentication. The helper accepts method, root-relative path, body, and headers.

Valid:

```js
const serverInfo = await host.agentServer.request({
  path: "/server_info",
});
```

Invalid:

```js
host.agentServer.request({ path: "server_info" });
host.agentServer.request({ path: "//other-host/path" });
host.agentServer.request({ path: "https://other-host/path" });
```

The current service rejects paths that do not begin with one `/`. It defaults `method` to `GET`.

## Runtime lifecycle

For every enabled installation, Canvas:

1. Fetches authenticated entrypoint text from the owning backend.
2. Imports the self-contained ESM bundle from a Blob URL.
3. Validates the `activate` export.
4. Creates an app-scoped registry and calls `activate`.
5. Admits only page registrations declared by the manifest.
6. Renders contributed pages under a Canvas-owned error boundary.
7. Unmounts pages and invokes cleanup when the activation inventory changes.

A page mount may be synchronous or asynchronous. If an async mount resolves after route disposal, Canvas immediately invokes the returned disposer.

Build app code to tolerate repeated activation and mounting. Guard asynchronous requests against late state updates. Clear intervals, animation frames, observers, event listeners, and DOM/style nodes.

## Management API

The current Canvas frontend service calls:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/canvas-extensions/installed` | List installed apps |
| `POST` | `/api/canvas-extensions/install` | Install disabled from Git or backend-local path |
| `PATCH` | `/api/canvas-extensions/installed/{name}` | Set enabled state |
| `DELETE` | `/api/canvas-extensions/installed/{name}` | Uninstall |
| `GET` | `/api/canvas-extensions/installed/{name}/bundle` | Fetch entrypoint JavaScript text |

Install request:

```json
{
  "source": "github:owner/repository",
  "ref": "main",
  "repo_path": "extensions/example-dashboard",
  "force": false
}
```

Interpret backend-local paths on the Agent Server machine, not in the frontend process. For a backend-local source, the current Canvas frontend joins a supplied `repo_path` into `source` before sending the install request and sends `repo_path: null`; select the app package directory as seen by the Agent Server. A repository may hold multiple apps under different `repo_path` values.

Each install request resolves exactly one canvas extension package root. For a remote repository, the directory selected by `repo_path`, or the repository root when `repo_path` is omitted, must contain that app's `canvas-extension.json`. For a backend-local source, the `source` path is already the selected app package directory. The current Add app form submits one install request and does not recursively discover or bulk-install nested app manifests. Install every remote app separately with the same `source` and `ref` when appropriate and a distinct `repo_path`; submit every local app package directory separately.

Treat co-located apps as independent installations: each app has its own manifest name, version, resolved revision record, enabled state, bundle, registrations, and cleanup lifecycle. Shared repository source or build tooling does not combine their runtime identities.

Backend endpoint availability may lag behind the frontend. HTTP 404 means the backend lacks Apps support. Cloud backends are not supported by the current frontend service.

## Current v1 limitations

Do not promise or implement these features without confirming a newer contract:

- conversation tabs or panels;
- header, footer, badge, or arbitrary host slots;
- code-free theme contributions;
- visualizer augmentation or replacement;
- marketplace signing or publisher verification;
- enforceable fine-grained permissions;
- iframe or worker isolation;
- arbitrary install lifecycle scripts;
- automatic agent-driven enablement.

Page contributions are the supported host API 1 ABI. Host compatibility manifest fields and a published Canvas Extensions API SDK or bundler template are not part of the current contract.
