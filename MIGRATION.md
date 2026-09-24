# Migration Guide

## Python raw-dict catalog accessors removed in 0.12.0

`openhands_extensions.list_integration_catalog` and
`openhands_extensions.get_integration_catalog_entry` were deprecated in 0.10.0
with `removed_in="0.12.0"` and are removed in 0.12.0, per the two-minor-release
runway enforced by `scripts/check_deprecations.py`. Replace them with the typed
accessors, which validate every entry against `IntegrationCatalogEntry`:

```diff
-from openhands_extensions import get_integration_catalog_entry, list_integration_catalog
+from openhands_extensions import (
+    get_integration_catalog_entry_model,
+    list_integration_catalog_models,
+)

-entries = list_integration_catalog(oauth=True)
-entry = get_integration_catalog_entry("github")
-entry_id = entry["id"]
+entries = list_integration_catalog_models(oauth=True)
+entry = get_integration_catalog_entry_model("github")
+entry_id = entry.id
```

The filter arguments (`mcp=`, `oauth=`) and the `None` returned for an unknown
id are unchanged; only the element type differs. Callers that genuinely need
JSON-compatible dictionaries can call `model.model_dump(exclude_none=True)`,
which reproduces the hand-authored entry exactly, or read the unchanged
`INTEGRATION_CATALOG_SNAPSHOT`. The JavaScript API is unaffected:
`listIntegrationCatalog` / `getIntegrationCatalogEntry` keep returning plain
objects.

## MCP catalog to integration catalog

This package version is still `0.0.0`, and the MCP catalog was an experimental
pre-release API. This migration intentionally removes the old MCP-only export
paths and names instead of keeping deprecated aliases.

### Import paths and symbols

Before:

```js
import { MCP_CATALOG } from "@openhands/extensions/mcps";
import { MCP_LOGOS } from "@openhands/extensions/mcps/logos";
```

After:

```js
import { INTEGRATION_CATALOG } from "@openhands/extensions/integrations";
import { INTEGRATION_LOGOS } from "@openhands/extensions/integrations/logos";
```

TypeScript consumers should replace `McpCatalogEntry` with
`IntegrationCatalogEntry`.

### Catalog entries

Before, MCP entries exposed a single `template`:

```js
const template = entry.template;
```

After, integrations expose one or more `connectionOptions`:

```js
const option =
  entry.connectionOptions.find(
    (candidate) => candidate.id === entry.defaultConnectionOptionId,
  ) ?? entry.connectionOptions[0];
```

MCP-backed options use `provider: "mcp"` and include their transport details.
Other integration types can use the same catalog entry shape without pretending
to be MCP servers.

### Automation entries

Automation templates now refer to integrations, not MCP-only records:

```diff
- requiredMcpIds
+ requiredIntegrationIds
```

### Deprecation timeline

There is no deprecation window for the old `mcps` exports. They were removed in
this PR because downstream consumers are being updated in the same coordinated
change and the API had not been treated as stable.
