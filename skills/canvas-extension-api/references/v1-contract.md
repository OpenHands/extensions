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
  backend?: CanvasExtensionBackend | null;
}

interface CanvasExtensionBackend {
  schema_version: 1;
  artifacts: Partial<Record<"linux-amd64" | "linux-arm64", {
    path: string;
    sha256: string;
  }>>;
  argv: string[];
  health?: {
    path?: string;
    timeout_seconds?: number;
    interval_seconds?: number;
  };
  inherit_environment?: string[];
}

interface CanvasExtensionPageContribution {
  id: string;
  title: string;
  path: string;
  nav_label?: string | null;
  description?: string | null;
}
```

Required manifest fields are `schema_version`, `name`, `version`, and `entrypoint`. A useful page package also supplies `display_name`, `description`, and at least one `contributes.pages` entry. `backend` is optional: omitting it preserves a browser-only App or a manual/deployment-owned Sidecar.

The managed-backend contract requires the stacked, unreleased Agent Server changes in [software-agent-sdk PR #5270](https://github.com/OpenHands/software-agent-sdk/pull/5270) at `ac7b322ddf7d2e0e90a3643c5e26d848236af9a3` and [PR #5272](https://github.com/OpenHands/software-agent-sdk/pull/5272) at `4c81fa22ef959fca04496f496ee6163324855696`. Until a release containing both lands, those exact revisions are the minimum Agent Server implementation. Feature-detect `canvas_app_backend_bridge_v1` in `GET /server_info`; the same response must provide `app_backend_ingress_url`. Use the host view helper only at the minimum host version stated below.

For a managed backend:

- Key `artifacts` only by `linux-amd64` or `linux-arm64`; one matching entry is sufficient.
- Keep each artifact `path` package-relative, contained, and ending in `.tar.gz`.
- Set `sha256` to exactly 64 lowercase hexadecimal characters.
- Use a non-empty structured `argv`; `argv[0]` must resolve inside `{artifact_dir}`.
- Use only `{artifact_dir}`, `{data_dir}`, and `{port}` placeholders.
- Keep `health.path` root-relative. Defaults are `/health`, 30 seconds, and 0.1 seconds.
- Request only `LANG`, `LC_ALL`, `LC_CTYPE`, `PATH`, `TMPDIR`, or `TZ` in `inherit_environment`, without duplicates. Ambient Agent Server credentials are never inherited.

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
  readonly appBackendView?: {
    mount(options: { container: HTMLElement }): () => void;
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

`appBackendView` is additive and optional. Feature-detect it before mounting. It is absent for host builds without the helper, no-backend and cloud selections, or selected Agent Servers without `canvas_app_backend_bridge_v1`, `app_backend_ingress_url`, and the compatible typed client. `mount({ container })` returns a disposer. The helper obtains an app-scoped session, validates the HTTP(S) ingress and sandbox, renders loading/error/retry and safe new-tab fallback, and revokes the session on disposal. It does not prepare, start, stop, or delete backend data.

Every App API call is scoped to the active backend. When the user changes backend, Canvas disposes the old activation, mounted backend views, and sessions before activating the App with a fresh host snapshot.


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
| `GET` | `/api/canvas-extensions/installed/{name}/backend` | Read managed-backend status and revision |
| `POST` | `/api/canvas-extensions/installed/{name}/backend/prepare` | Verify and prepare the approved revision |
| `POST` | `/api/canvas-extensions/installed/{name}/backend/start` | Start the prepared approved revision |
| `POST` | `/api/canvas-extensions/installed/{name}/backend/stop` | Stop the owned process group |
| `GET` | `/api/canvas-extensions/installed/{name}/backend/logs` | Read bounded backend logs |
| `DELETE` | `/api/canvas-extensions/installed/{name}/backend/data` | Separately delete preserved mutable data |

Prepare and start bodies are `{"revision":"<exact installed revision>"}`. Status is exactly `missing`, `stopped`, `starting`, `ready`, `unhealthy`, or `unsupported`. Installation, enablement, activation, and page mounting never prepare or start a backend. Updating invalidates approval. Disable and uninstall stop owned processes and revoke bridge access but preserve backend data; data deletion is separate.

The bridge advertises `canvas_app_backend_bridge_v1` and `app_backend_ingress_url` through `GET /server_info`. Its control endpoints are `POST` and `DELETE` on `/app-backends/{name}/session` at the configured ingress, which must be a separate browser origin from Canvas. Session responses contain `ingress_url`, `expires_at`, and `iframe_sandbox`; the credential is an HttpOnly cookie and never appears in the response or URL. The v1 sandbox is `allow-forms allow-modals allow-popups allow-same-origin allow-scripts`. Preserve `allow-same-origin`: the separate ingress origin is the isolation boundary, while an opaque sandbox origin causes Chromium to send `Origin: null` for mutating fetches and WebSockets, omit the partitioned cookie, and reject Worker creation with `SecurityError`.

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
