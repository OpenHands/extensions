# Integration catalog

This directory contains curated integration metadata for OpenHands clients.
Most current entries are MCP-backed, but the schema also supports HTTP/OpenAPI
integrations so clients can consume one source of truth.

- `integration-catalog.json` is the hand-authored source of truth (a single
  JSON asset, NOT generated from any `.mjs`/`.js` source). It is mirrored
  byte-for-byte into the Python package.
- `catalog/<id>.json` contains one file per integration entry, kept in sync
  with the matching entry in `integration-catalog.json` (a CI parity test
  asserts the two never drift).
- `index.js` reads `integration-catalog.json` at runtime and derives the
  `supportsMcp`/`supportsOauth` flags, the reconstructed `providers[]` view,
  and `defaultManagedConnectors` from the canonical data.
- `index.d.ts` contains the public TypeScript shape.

Provider-specific OAuth knowledge is merged into each integration as a minimal
`oauthProvider` override object (`null` when the integration has no OAuth
provider); only fields whose OAuth-context values differ from the integration's
connector view (`description`, `docsUrl`, `popularityRank`) are stored. The
`providers[]` view is reconstructed at runtime by `listOAuthProviderCatalog()`.

Consumers can import the package export:

```js
import { INTEGRATION_CATALOG } from "@openhands/extensions/integrations";
```

## Migration from the MCP catalog

This catalog replaces the experimental `@openhands/extensions/mcps` export.
The MCP-only `mcps/` directory has been renamed to `integrations/`, and the
old package exports were removed rather than kept as aliases.

- Import `INTEGRATION_CATALOG` from `@openhands/extensions/integrations`
  instead of `MCP_CATALOG` from `@openhands/extensions/mcps`.
- Import logo mappings from `@openhands/extensions/integrations/logos`
  instead of `@openhands/extensions/mcps/logos`.
- Use `IntegrationCatalogEntry` instead of `McpCatalogEntry`.
- Read MCP configuration from `entry.connectionOptions[]`. Direct MCP entries
  have `provider: "mcp"` and a `transport`; entries may expose multiple
  options such as `id: "oauth"` for a hosted OAuth MCP endpoint and `id:
"api"` for an API-key or stdio fallback.
- Use `entry.defaultConnectionOptionId` to choose the preferred option.
- Automation catalog entries now use `requiredIntegrationIds` instead of
  `requiredMcpIds`.

The `mcps` API was intentionally broken because it was pre-release and had not
been adopted as a stable public surface.

The catalog intentionally stores only serializable data. Client applications are responsible for mapping entries to UI-specific icons or styling.
