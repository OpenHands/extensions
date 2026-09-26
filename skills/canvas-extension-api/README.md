# Canvas Extensions API

Build and validate Apps for Agent Canvas using manifest schema 1 and host API 1.

This skill covers the routed-page contract currently implemented by Agent Canvas, including:

- `canvas-extension.json` manifests;
- self-contained browser ESM entrypoints exporting `activate(host)`;
- `host.registerPage` lifecycle and routing;
- authenticated Agent Server requests;
- one-file packaging, Blob import testing, and installation;
- optional Sidecar architecture and backend safety;
- a dependency-free package validator.

## Validate an app package

```sh
node scripts/validate-extension.mjs /path/to/app-package
```

For a build output staged under `dist/`:

```sh
node scripts/validate-extension.mjs /path/to/app-package --dist
```

Run the validator tests with:

```sh
node --test scripts/validate-extension.test.mjs
```

See [SKILL.md](SKILL.md) for the complete agent workflow and the `references/` directory for focused implementation guidance.
