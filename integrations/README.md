# Integration catalog

This directory contains curated integration metadata for OpenHands clients.
Most current entries are MCP-backed, but the schema also supports HTTP/OpenAPI
integrations so clients can consume one source of truth.

- `catalog/<id>.json` is the hand-authored source of truth. Add or edit an
  integration by changing exactly one file in that directory.
- `catalog-index.js` is generated from `catalog/*.json` so the JavaScript
  package can statically import every individual JSON file without an aggregate
  catalog JSON asset.
- The Python package includes the same individual `catalog/*.json` files and
  reads them directly.
- `index.js` derives the `supportsMcp`/`supportsOauth` filters from the
  canonical connection options at read time.
- `index.d.ts` contains the public TypeScript shape.

Each integration carries its OAuth/MCP connection data directly. Do not add a
separate provider catalog or per-language provider data.

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
- Read serializable logo metadata from each `IntegrationCatalogEntry` (`logoUrl`,
  `iconBg`, and `iconColor`) instead of importing React-specific logo maps.
- Use `IntegrationCatalogEntry` instead of `McpCatalogEntry`.
- Read MCP configuration from `entry.connectionOptions[]`. Direct MCP entries
  have `provider: "mcp"` and a `transport`; entries may expose multiple
  options such as `id: "oauth"` for a hosted OAuth MCP endpoint and `id:
"api"` for an API-key or stdio fallback. The first option is the preferred
  default.
- Automation catalog entries now use `requiredIntegrationIds` instead of
  `requiredMcpIds`.

The `mcps` API was intentionally broken because it was pre-release and had not
been adopted as a stable public surface.

The catalog intentionally stores only serializable data, including language-agnostic logo URLs and optional presentation colors. Client applications can render those fields directly while keeping any purely UI-specific styling local.
