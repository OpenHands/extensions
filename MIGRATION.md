# Migration Guide

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
