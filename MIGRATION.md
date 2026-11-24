# Migration Guide

## Slack catalog entry switched to Slack's hosted MCP server only

The Slack integration's third-party `@zencoderai/slack-mcp-server` stdio option
was removed; the entry now points only at Slack's official hosted MCP server
(`https://mcp.slack.com/mcp`), via the existing OAuth option and a new
user-token bearer option whose credential is saved as `SLACK_MCP_USER_TOKEN`
(named to avoid colliding with the `slack-channel-monitor` skill's
`SLACK_USER_TOKEN` / `SLACK_BOT_TOKEN` secret resolution).

### Previously installed Slack servers

If you previously installed Slack through the old `api` stdio option, your
installed server keeps working but Agent Canvas no longer matches it to the
catalog entry. Canvas [matches installed servers by
transport](https://github.com/OpenHands/OpenHands/blob/c5e47c4b4dab1d14724e74675c06254957ccbf47/src/utils/mcp-marketplace-utils.ts#L217-L245),
so the server shows as a plain custom server instead of the Slack integration.

That same match is also what Canvas uses to decide [whether Slack is connected
for a
template](https://github.com/OpenHands/OpenHands/blob/d5dcd45d1c3f798fce782833029476a2b371e051/src/hooks/query/use-manifest-prerequisites.ts#L57-L71),
so an install made from the old card counts as missing until you reconnect.
Until then, the **Continue** button stays disabled for these automations:

- `slack-channel-monitor`
- `slack-standup-digest`
- `incident-retrospective-drafter`

To get the catalog match and template prerequisites back, remove the old
install and reconnect Slack from the integration card, which now uses the
hosted server.

### Slack channel monitor no longer gets a token from the card

`slack-channel-monitor` reads `SLACK_USER_TOKEN` then `SLACK_BOT_TOKEN`
([`skills/slack-channel-monitor/scripts/main.py`](skills/slack-channel-monitor/scripts/main.py)),
and the renamed `SLACK_MCP_USER_TOKEN` is intentionally *not* in that list: on
a user token the monitor ignores the token owner's own messages and replies as
them, so feeding it the MCP token by default would change its behavior without
notice. As a result, connecting Slack from the integration card no longer
gives the monitor a token — its template prerequisite ("Slack connected") is
met, but the cron run stops with "No Slack token found."

If you use `slack-channel-monitor`, set one of the following in **OpenHands
Settings → Secrets** after connecting Slack MCP:

| Secret | Token type |
|--------|-----------|
| `SLACK_BOT_TOKEN` | Bot (`xoxb-`) |
| `SLACK_USER_TOKEN` | User (`xoxp-`) |

The proper long-term fix is for the monitor's template to declare the secret
it reads (tracked in #985).

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
