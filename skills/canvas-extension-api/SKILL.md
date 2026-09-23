---
name: canvas-extension-api
description: This skill should be used when the user asks to "create an OpenHands App", "scaffold a Canvas App", "build an app with the Canvas Extensions API", "build an Agent Canvas App", "bundle a single-file Canvas App", "build a Sidecar-backed Canvas App", "add onboarding for an App service", "add a custom interface to Agent Canvas", "validate an OpenHands App", or mentions Canvas Apps, Agent Canvas extensions, Blob-importable app bundles, registerPage, app pages, Sidecars, or canvas extension packages.
---

# Canvas Extensions API

Build and validate OpenHands Apps with the Canvas Extensions API, targeting the currently implemented manifest schema 1 and host API 1 routed-page ABI.

Use the naming layers consistently:

- **OpenHands Apps** - customer-facing category for interfaces people discover, install, enable, and open.
- **Apps for Agent Canvas** - product phrasing that clarifies where apps run.
- **Canvas Extensions API** - developer platform used to build apps.
- **Canvas extension package** - technical artifact containing `canvas-extension.json` and its entrypoint.
- **OpenHands Extensions** - ecosystem and repository umbrella for apps, skills, plugins, automations, and integrations.

Use current product labels in user-facing instructions: **Apps for Agent Canvas**, **Add app**, **Installed apps**, **App source**, **Enable trusted app**, and **Build an app**. Keep technical identifiers such as `canvas-extension.json`, `/api/canvas-extensions/*`, `host.extension`, and `/extensions/*` unchanged unless the target implementation changes them.

Treat apps as trusted, same-realm browser code owned by the active Agent Server. Keep the categories distinct: apps extend what people can do in Agent Canvas, plugins extend agent runtime capabilities, and skills provide agent instructions and knowledge.


## Prefer the proven App authoring loop

Treat an App as one authenticated browser dependency graph that Canvas imports from a Blob URL. Do not build a hosted SPA: the production result must be exactly one self-contained browser ESM entrypoint that exports `activate(host)`. Always ship this UI package even when it uses an optional package-owned managed backend or a manual/deployment-owned Sidecar. Make the App page the guided UI for service setup after the App is opened. Never treat a service as another browser chunk or an automatic extension install hook.

For a new App, create an independent package in the target repository and implement its own UI, tests, and build tooling. Follow the Vite library-build reference in `references/packaging-recipes.md`; do not copy a shared starter or introduce a repository-wide runtime/workspace unless the target repository explicitly requires it.

Keep all source, scripts, dependencies, tests, and checked-in `extension.js` inside the App package. Implement one declared page with explicit root, nested, and unknown-route behavior. Inject scoped CSS per mount and clean it up with framework roots, requests, listeners, timers, Workers, and object URLs. Build validation must verify `dist/extension.js` before synchronizing it to the App root. Do not synchronize an unverified artifact. Use `CHROME_PATH` when the Chrome executable is elsewhere.

For an existing App, run the reusable static gate before and after its own checks:

```sh
node /path/to/canvas-extension-api/scripts/validate-extension.mjs /path/to/app
node /path/to/canvas-extension-api/scripts/validate-extension.mjs /path/to/app --dist --marker <required-feature-marker>
```

Treat the static validator as a gate, not a replacement for the browser Blob smoke test. Read `references/packaging-recipes.md` before adding CSS, raw assets, dynamic modules, Workers, or WASM. Read `references/backend-safety.md` before any Agent Server integration or persistence. Read `references/sidecar-pattern.md` before designing a separately installed service or its onboarding. Read `references/acceptance-checklist.md` before reporting local Canvas compatibility.

## Establish the target

Start by locating the target directory instead of assuming the current workspace. Inspect repository instructions, existing package management, build tooling, tests, and git status before editing.

Make an early architecture decision: browser-only App, Agent Server-integrated App, package-owned managed-backend App, manual/deployment-owned Sidecar App, or explicitly deployment-specific App. Keep the portable host API 1 surface separate from optional Agent Server/host capabilities and deployment-owned behavior.

Use the package-owned managed-backend path only when the target stack includes the lifecycle contract from [software-agent-sdk PR #5270](https://github.com/OpenHands/software-agent-sdk/pull/5270) at `ac7b322ddf7d2e0e90a3643c5e26d848236af9a3`, the bridge contract from [PR #5272](https://github.com/OpenHands/software-agent-sdk/pull/5272) at `4c81fa22ef959fca04496f496ee6163324855696`, and the host version named in `references/v1-contract.md`. Until a release containing both SDK PRs lands, those exact revisions are the minimum Agent Server implementation. Feature-detect `canvas_app_backend_bridge_v1` and `app_backend_ingress_url` through `GET /server_info`; absence is an actionable unsupported state. Do not convert manual Sidecars into managed backends unless the App owns checksum-pinned artifacts for every supported platform.

Clarify only choices that materially affect implementation:

- app purpose and page behavior;
- target repository and subdirectory;
- dependency-free JavaScript versus a bundled TypeScript/framework project;
- Agent Server endpoints or host metadata required;
- whether to build only, install locally, or prepare publication instructions;
- for a Sidecar: execution location, owner, connection route, secrets and data, lifecycle actions, and portability across Agent Canvas deployments.

Default to one app with one routed page when requirements are otherwise clear. Keep the first implementation small and dependency-free unless the requested UI clearly benefits from a framework or the repository already has a bundler.

When creating multiple Apps in one repository, give every App an independent package root containing its own `canvas-extension.json`, entrypoint, version, tests, README, and build tooling. Do not introduce a monorepo, shared runtime, or common build foundation unless the target repository explicitly requires one. Keep app manifest names globally distinct within the Agent Server installation.

Treat installation as one app per request. The current Customize -> Apps flow accepts one `source`, optional `ref`, and optional `repo_path`; it does not recursively discover or bulk-install every manifest in a repository. For a remote repository, add each app separately using the same source/ref and its own `repo_path`. For a backend-local source, select each app package directory as the source path.

Read `references/v1-contract.md` before implementing unfamiliar Canvas Extensions API behavior. Read `references/connections.md` before connecting to Agent Server, the Automation service, or WebSocket endpoints. Read `references/sidecar-pattern.md` before proposing a Sidecar bridge, onboarding, or operator action. Read `references/testing-and-installation.md` before installing or testing inside Agent Canvas, especially for a multi-app repository.

## Inspect current upstream behavior

Treat the v1 contract as young and subject to change. Before substantial work, compare the installed or target OpenHands version with the current upstream sources when access is available:

- `specs/canvas-extensions.md`
- `src/types/canvas-extension.ts`
- `src/components/features/canvas-extensions/canvas-extensions-runtime.tsx`
- `src/routes/canvas-extension-page.tsx`
- `docs/CANVAS_EXTENSIONS_TESTING.md`

Do not invent planned surfaces such as conversation tabs, slots, themes, or visualizer replacement. Implement only contributions supported by the target version. Routed pages are the only implemented contribution in host API 1.

## Create the app package

Place `canvas-extension.json` at the app package root. Point `entrypoint` to one self-contained browser ESM file inside that root.

Use this minimal manifest shape:

```json
{
  "schema_version": 1,
  "name": "example-dashboard",
  "display_name": "Example dashboard",
  "version": "0.1.0",
  "description": "A backend-specific project dashboard.",
  "entrypoint": "extension.js",
  "contributes": {
    "pages": [
      {
        "id": "dashboard",
        "title": "Dashboard",
        "path": "/dashboard",
        "nav_label": "Dashboard"
      }
    ]
  }
}
```

For an optional package-owned managed backend, add this top-level sibling of `contributes`:

```json
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
  "health": { "path": "/health" }
}
```

This declaration is optional. Omit it for browser-only Apps and manual/deployment-owned Sidecars. It never authorizes automatic preparation or startup. The server supports Linux amd64 and arm64 initially, verifies package-contained `.tar.gz` artifacts by SHA-256, and executes the structured argv without a shell. `argv[0]` must remain inside `{artifact_dir}`; allowed placeholders are `{artifact_dir}`, `{data_dir}`, and `{port}`.

Follow these invariants:

- Use lowercase letters, digits, and hyphens for app names and page IDs.
- Use absolute kebab-case page paths with a leading slash.
- Keep every manifest path within the app package root.
- Give each page ID and path a unique value.
- Register only page IDs declared in the manifest.
- Keep the entrypoint free of unresolved bare imports and external chunks.
- Bundle dependencies, CSS, and small assets into the entrypoint when using build tooling.

Add a concise `README.md` when the app is intended for reuse or publication. Document purpose, build command if any, output entrypoint, installation coordinate, and verification steps. Avoid adding explanatory change-log documents.

## Implement activation and pages

Export an `activate` function from the ESM entrypoint:

```js
export function activate(host) {
  if (host.apiVersion !== "1") {
    throw new Error(`This app requires host API 1.`);
  }

  return host.registerPage("dashboard", ({ container, path, navigate }) => {
    const root = document.createElement("section");
    root.textContent = path ? `Nested route: ${path}` : "Dashboard";
    container.append(root);

    return () => root.remove();
  });
}
```

Use the host contract deliberately:

- Read immutable metadata from `host.extension` and `host.backend`.
- Call `host.registerPage(id, mount)` during activation.
- Use the mount callback's `path` as the route remainder below the declared page path.
- Treat every nested-route navigation as a fresh mount: Canvas disposes the previous mount, clears the container, and invokes the mount callback with the new remainder. DOM and framework state do not persist across route changes; keep intentional cross-route state in the URL, backend, or activation-scoped state and clean it up on deactivation.
- Use `navigate(absoluteCanvasPath)` for Canvas-aware routing.
- Use `host.agentServer.request({ path, method, body, headers })` for authenticated calls to the owning Agent Server.
- Pass only root-relative request paths beginning with one `/`; never pass absolute URLs or `//` paths.

Prefer [`@openhands/typescript-client`](https://github.com/OpenHands/software-agent-sdk/tree/main/clients/typescript) for bundled TypeScript integrations whenever it covers the required Agent Server API and the necessary connection inputs are available. Prefer its typed clients, models, compatibility checks, and WebSocket lifecycle over hand-written transport code. Bundle the client into the self-contained app entrypoint; never leave a bare package import or external runtime chunk.

Respect the host API 1 connection boundary:

- Treat `host.agentServer.request` as the portable Agent Server HTTP path; Canvas selects the active backend and supplies authentication.
- For a managed-backend view, require the feature-detected host helper documented in `references/v1-contract.md`. The helper owns session creation, validated iframe isolation, retry/new-tab behavior, and revocation; the App never reads the app-scoped cookie or constructs the ingress URL. The ingress must be a separate browser origin from Canvas, and the host must preserve the server-returned sandbox including `allow-same-origin`.
- Installing, enabling, activating, or mounting an App never prepares or starts a managed backend. Show the resolved revision and declaration, obtain explicit lifecycle consent, and call prepare then start with that exact revision. An update invalidates approval.
- Do not derive an Agent Server URL from `window.location` or extract session keys from Canvas internals.
- Do not send Automation service requests through `host.agentServer.request` unless the backend explicitly documents an Agent Server proxy for them. Automation is a separate service with deployment-provided base URL and authentication.
- Do not open a direct Agent Server WebSocket from a portable v1 app. The host currently exposes neither the owning server origin nor a WebSocket/auth capability. Poll through `host.agentServer.request`, add a backend-owned bridge, or feature-detect a future host subscription API.
- Use the TypeScript client's Agent Server WebSocket support in trusted standalone or future host-enabled contexts, and stop it during disposal. Do not treat the Agent Server client as an Automation service client.

Return cleanup from every layer that creates effects:

- Return the unregister function or an activation disposer from `activate`.
- Return a mount disposer for DOM nodes, timers, listeners, observers, subscriptions, and outstanding state.
- Make async work disposal-aware so late responses cannot mutate an unmounted page.
- Remove injected styles when the page unmounts.

Assume activation, mounting, and disposal may happen repeatedly during hot enable/disable, updates, backend switches, reconnects, and route changes.

## Build a production-quality page

Render within the supplied `container`; do not replace unrelated Canvas DOM. Scope CSS under an app-specific root class. Prefer Canvas CSS variables with sensible fallbacks rather than copying host implementation classes.

Provide:

- semantic structure and headings inside the supplied container. Canvas already owns the outer `<main aria-label={page title}>`, so do not add a nested `main` or duplicate page landmark label;
- keyboard-operable controls and visible focus;
- responsive behavior for narrow layouts;
- loading, empty, stale, and error states;
- reduced-motion handling for animation;
- text-safe rendering through DOM APIs or escaping rather than untrusted `innerHTML`;
- clear handling for malformed or partial Agent Server responses.

Avoid global event handlers, prototype changes, global CSS selectors, and ambient state unless unavoidable. Same-realm execution means these effects have full Canvas authority and cleanup is only best-effort.

## Add tests

Test real app code with a DOM environment and a small Canvas Extensions API host test double. Test at minimum:

1. `activate` registers every declared page exactly once.
2. The mount renders its initial state.
3. Agent Server requests use the expected root-relative path and method.
4. Nested navigation disposes the prior mount and remounts with the correct route remainder; test any intentionally preserved state explicitly.
5. The mount disposer removes DOM and stops effects.
6. The activation disposer unregisters contributions.
7. Unsupported host API versions fail clearly when compatibility is checked.
8. Network and malformed-response errors render safely.

Use the repository's existing test infrastructure. Do not introduce a new framework when adequate tests already exist. For dependency-free fixtures, Vitest with a DOM environment matches the upstream example, but it is not part of the Canvas Extensions API runtime contract.

## Validate the package

Run the bundled validator before reporting completion:

```sh
node /path/to/canvas-extension-api/scripts/validate-extension.mjs /path/to/app-package
```

Then run the target repository's formatter, linter, tests, and build. Inspect the final entrypoint rather than assuming the bundler configuration worked:

- confirm the file exists at the manifest path;
- confirm it exports `activate`;
- reject bare imports and dynamic external chunks;
- confirm CSS and required small assets are bundled or embedded;
- confirm the output runs as browser ESM without Node globals.

Treat validator warnings as prompts for inspection, not proof of invalidity. The helper uses conservative static checks and cannot replace loading the app bundle in Canvas.

## Install and verify safely

Install only when requested. Installation and enablement are separate product actions: installation must leave the app disabled, and enabling executes trusted same-realm code. Managed-backend preparation and startup are additional explicit actions tied to the resolved revision; installation, enablement, activation, and ordinary page mounts never execute backend code.

For a backend-local app, install the path as interpreted on the Agent Server machine. For a Git-hosted app, provide `source`, optional `ref`, and optional `repo_path`. Never assume a frontend-local path exists inside a remote or containerized backend.

For multiple apps in one repository, produce an install matrix listing app name, manifest directory, source, ref, and `repo_path`. Submit one Add app operation per row. For remote repositories, omit `repo_path` only when the selected app lives at the repository root. For backend-local sources, make `source` the selected app package directory. Do not claim that selecting a repository root installs nested apps.

Validate and test every app package independently, then run shared repository checks once. Report partial failures by app name rather than treating one passing app package as validation of the entire repository.

Verify the lifecycle in Canvas:

1. Install and confirm the inventory entry is disabled.
2. Review source, revision, manifest metadata, and contributions.
3. Enable and accept the trusted-code disclosure: “This app runs trusted JavaScript inside Agent Canvas and can make authenticated requests to the active Agent Server. Review its source and revision before enabling it.”
4. Open the navigation item and exercise root and nested routes.
5. Disable and confirm navigation and mounted UI disappear.
6. Re-enable without restarting Canvas.
7. Switch backend or reconnect when relevant and confirm isolation.
8. Uninstall only when requested.

Do not enable, uninstall, publish, push, or open a pull request without the user's authorization.

## Report completion

Summarize:

- app location and contributed pages;
- manifest schema and host API targeted;
- build output and validation results;
- tests run and their results;
- installation status, explicitly stating whether it remains disabled;
- remaining limitations tied to the current v1 ABI.

## Resources

- `references/v1-contract.md` - exact manifest, host API, lifecycle, routing, trust, and current limitations.
- `references/connections.md` - Agent Server HTTP, Automation service, WebSocket, and TypeScript client connection guidance.
- `references/testing-and-installation.md` - test strategy, manual Canvas workflow, and installation coordinates.
- `references/packaging-recipes.md` - one-file Vite, CSS, assets, Workers, and WASM rules.
- `references/backend-safety.md` - authenticated requests, command safety, persistence, and prerequisite onboarding.
- `references/acceptance-checklist.md` - automated checks and the local install/enable/reload lifecycle.
- `scripts/validate-extension.mjs` - dependency-free static artifact validator for an App package directory.
