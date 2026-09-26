# Agent Canvas Apps

Apps are installable interfaces that bring dashboards, internal tools, and workflows directly into Agent Canvas without requiring a fork. They are powered by the Canvas Extensions API, which is currently beta.

## Package convention

Each App occupies one directory under `apps/` and is a self-contained Canvas Extension package:

- `canvas-extension.json` declares the package, routed pages, and optional managed backend.
- The manifest's `entrypoint` is a browser ESM module that exports `activate(host)`.
- App-specific documentation and assets may live beside the manifest and entrypoint.
- Build output must remain self-contained: browser entrypoints must not import package dependencies at runtime.

The registry catalog is `apps/catalog.json`, exposed to JavaScript consumers as `APPS_CATALOG` from `@openhands/extensions/apps`. Add one catalog entry when adding an App; keep its `source` and `manifest` paths relative to this repository.

## Trust and installation

Enabling an App executes its trusted JavaScript in the Agent Canvas browser context. An App can make authenticated requests to the active Agent Server through the host API. Review the source, manifest, and resolved revision before enabling an App. Apps are not skills or plugins: an App provides a Canvas interface, a skill provides agent instructions, and a plugin provides agent capabilities and configuration.

The host currently supports routed custom pages through the beta Canvas Extensions API. Follow the API documentation and validate packages with the repository's Canvas App validator before submitting a pull request.
