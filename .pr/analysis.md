# Azure DevOps MCP catalog investigation

Issue: https://github.com/OpenHands/OpenHands/issues/15769

This is an integration catalog omission. It is tracked in OpenHands/OpenHands,
but the reusable entry belongs in OpenHands/extensions. Existing draft
OpenHands/extensions#384 is a related proposal; this branch starts from current
main and includes current-schema validation, published-package evidence, and
the limitations of the current Canvas install form.

## Reproduction

Before adding the entry, the three new `azure_devops` tests fail with a missing
catalog key, missing logo entry, and a Python lookup returning `None`:

```text
pytest -q tests/test_catalogs.py tests/test_integration_catalog_in_sync.py -k azure_devops
3 failed, 30 deselected
```

On Windows set `PYTHONUTF8=1` because existing tests read UTF-8 catalog files
using the process's default encoding.

## Dependency chain and ownership

- `integrations/catalog/<id>.json` is the hand-authored source.
- `npm run build:integrations` generates `integrations/catalog-index.js`.
- `integrations/index.js` exposes lookup and MCP/OAuth filters; the Python
  wheel packages the same JSON and exposes validated Pydantic models.
- Canvas imports `@openhands/extensions/integrations` (currently pinned to
  0.24.0). `src/utils/mcp-marketplace-utils.ts` chooses the installable option.
  `src/components/features/mcp-page/install-server-modal.tsx` appends argFields
  to fixed CLI args and stores envFields as environment values.
- SDK/Agent Server own stdio execution and hosted MCP OAuth discovery. The
  custom server editor can supply a registered OAuth client ID.

Inspected revisions:

- extensions: `c4551cf7446fbc17d85e1af9c9181a5ce1564798`
- Canvas: `a8c05584ec6bb063a0857460b9cbff48e136919f`
- local SDK checkout: `2cef2d83d4e3d99e0e1479ba177b52d001d8e6f1`
- Microsoft source: `1919d27db70eb0561c22d2be4e4b095c3d804590`

## Minimal design

Add one JSON entry and a logo derived from Canvas's existing Azure DevOps SVG;
regenerate the JS index. No schema or provider-specific runtime changes.

The issue's sample uses the wrong npm package, environment variables, auth
strategy spelling, and remote transport. The official local package is
`@azure-devops/mcp`; its PAT mode takes an organization positional argument
and `PERSONAL_ACCESS_TOKEN=base64(<email>:<PAT>)`. Canvas appends the organization
after the flags, which the published CLI accepts. Marketplace fields explicitly
declare their types and requiredness under the current schema.

The hosted endpoint uses Streamable HTTP. Its documented base URL is usable
without an organization segment when tool calls supply organization context;
the URL remains editable so clients can append their organization.

Keep hosted auth as `strategy: oauth2`, using MCP discovery rather than
hard-coded Entra endpoints or the Azure DevOps REST API's audience. A live GET
to `https://mcp.dev.azure.com/.well-known/oauth-protected-resource` returned 200:

```json
{
  "resource": "https://mcp.dev.azure.com",
  "authorization_servers": ["https://login.microsoftonline.com/organizations/v2.0"],
  "bearer_methods_supported": ["header"],
  "scopes_supported": ["https://mcp.dev.azure.com/.default"]
}
```

An unauthenticated Streamable HTTP initialize returned 401 with
`Bearer resource_metadata="https://mcp.dev.azure.com/.well-known/oauth-protected-resource/"`.
The [official remote setup guide](https://learn.microsoft.com/en-us/azure/devops/mcp-server/remote-mcp-server)
requires a custom Entra app registration. Catalog data alone cannot provide a
client registration. Current Canvas does not collect client IDs in its catalog
install modal and skips strategy-only OAuth options there; it selects the PAT
form. The entry explains the custom-editor remote setup rather than claiming
one-click hosted OAuth.

## Validation

```text
npm run build:integrations
pytest -q tests/test_catalogs.py tests/test_catalog_schema.py tests/test_integration_catalog_in_sync.py
120 passed

python .pr/smoke_azure_devops.py
server: Azure DevOps MCP Server 2.10.0
protocol: 2025-11-25
tool_count: 40
core_list_projects: present
wit_work_item and other work-item tools: present
authenticated_azure_api_calls: false
```

The smoke script launches the real catalog command with a synthetic PAT and
an explicit test tenant, then sends MCP initialize and tools/list. No real Azure
credentials or project/work-item operations were exercised. Published npm
2.10.0 is dated 2026-09-09, more than seven days before verification.

Additional checks passed:

- Actual Canvas marketplace adapter executed via TypeScript transpilation:
  visible entry, preferred remote metadata, PAT install form, organization arg,
  and password environment field.
- `npm pack`: catalog JSON, generated index, and SVG included; lookup and
  MCP/OAuth filters work from the extracted tarball.
- `pip wheel --no-deps .`: catalog JSON included; lookup and MCP/OAuth filters
  work using the extracted wheel rather than source paths.
- `python scripts/sync_extensions.py --check`: passed with three existing
  non-blocking marketplace coverage warnings. Native Git symlinks were restored
  in the Windows checkout to match CI; no tracked content changes resulted.
- `git diff --check`: passed.

## Release and remaining live verification

After an extensions release containing this entry, Canvas needs its regular
package/lockfile dependency update to expose the new tile. Real organization
PAT calls and Entra OAuth login still require a reviewer-owned Azure DevOps
organization, PAT, and registered client. No authenticated end-to-end claim is
made. A generic Canvas install flow supporting OAuth client inputs and option
selection is a separate application-owned enhancement.
