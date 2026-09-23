# Integration catalog

This directory contains curated integration metadata for OpenHands clients.
Most current entries are MCP-backed, but the schema also supports HTTP/OpenAPI
integrations so clients can consume one source of truth.

- `catalog/<id>.json` is the hand-authored source of truth. Add or edit an
  integration by changing exactly one file in that directory.
- `catalog-index.js` is generated from `catalog/*.json` so the JavaScript
  package can statically import every individual JSON file without an aggregate
  catalog JSON asset.
- `mcp-servers/<id>.json` is the generated MCP `server.json` export for
  catalog entries that describe MCP servers (see below). Regenerate with
  `npm run build:mcp-servers`,and verify with
  `node scripts/build-mcp-servers.mjs --check`.
- The Python package includes the same individual `catalog/*.json` files and
  reads them directly.
- `index.js` derives the `supportsMcp`/`supportsOauth` filters from the
  canonical connection options at read time.
- `index.d.ts` contains the public TypeScript shape.

Each integration carries its OAuth/MCP connection data directly. Do not add a
separate provider catalog or per-language provider data.

Every entry must include `docsUrl`. Marketplace input fields must explicitly
declare both their `type` and whether they are `required`, rather than relying
on client defaults. When connection metadata includes an `identityMapping`, it
must also identify the external principal. These requirements keep catalogs
actionable and prevent clients from guessing security- or UX-relevant defaults.

Connection options may also carry an optional `connectionModel`. This metadata
lets consumers distinguish the authenticated principal from the external
resource the credential can reach:

- `principalType` describes who or what authenticated.
- `credentialScope` describes the provider boundary enforced by the credential.
- `resourceType` and `resourceCardinality` describe whether the grant represents
  one workspace/site/tenant or can enumerate several.
- `selectionMode` tells clients whether the resource is known during auth,
  selected immediately after auth, or supplied at runtime.
- `identityMapping` contains constrained dot paths for identity values returned
  by OAuth, access-token claims, or a provider identity endpoint.
- `resourceDiscovery` describes a read-only endpoint used to enumerate resources
  when one grant covers several of them.

These fields are descriptive; they never broaden the scopes enforced by the
provider credential. Consumers must not claim resource-level isolation when a
provider token is only account- or tenant-scoped.

Consumers should use the read functions exported by the package:

```js
import {
  getIntegrationCatalogEntry,
  listIntegrationCatalog,
} from "@openhands/extensions/integrations";

const catalog = listIntegrationCatalog();
const entry = getIntegrationCatalogEntry(catalog[0].id);
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

## Generated MCP server.json artifacts

For catalog entries that describe MCP servers, the package also ships a
generated MCP ``server.json`` export in ``integrations/mcp-servers/<id>.json``. These
files conform to the official MCP ``server.schema.json`` format so they can be
consumed alongside, compared with, or published to the wider MCP ecosystem. They
are one-way build output; ``integrations/catalog/*.json`` remains the only
hand-authored source of truth. Do not edit them by hand..

Regenerate after any catalog change:

```sh
npm run build:mcp-servers
```

and verify the checked-in output is in sync in CI with:

```sh
node scripts/build-mcp-servers.mjs --check
```

The generator reads every catalog entry with at least one MCP connection option and
emits exactly one ``server.json`` per catalog id (folding an entry's multiple MCP
options into ``remotes``/``packages`` in catalog order):

- Remote transports map one-to-one: ``shttp`` -> ``type: "streamable-http"``
  and ``sse`` -> ``type: "sse"``; ``headerFields`` become ``headers``..
- ``stdio`` entries witha clean package mapping infer the registry:
  - ``npx -y <pkg>`` -> ``registryType: "npm"`` with ``runtimeHint: "npx"``..
  - ``uvx <pkg>`` (also ``--from <pkg>@<version>``) -> ``registryType:
    "pypi"`` with ``runtimeHint: "uvx"``..
  - ``docker run ... <image>`` -> ``registryType: "oci"`` with
    ``identifier: "docker.io/<image>:latest"`` and ``runtimeHint: "docker"``..
  - ``envFields`` become ``environmentVariables``; fixed args become positional
    or named ``packageArguments``/``runtimeArguments``,and ``argFields`` become
    positional arguments with ``valueHint`` (client-supplied values)..
- stdio entries with no clean npm/pypi/oci mapping (e.g. an ``npx github:...``
  shorthand) are omitted from ``remotes``/``packages`` but preserved (with their
  reason) under ``_meta["dev.openhands"].skippedConnectionOptions`` and in the verbatim
  ``connectionOptions`` list.. HTTP/OpenAPI-only integrationsare not generated at all..
- The reverse-DNS namespace is ``dev.openhands``: ``name`` becomes
  ``dev.openhands/<catalog-id>``,,and OpenHands-specific metadata (install
  hints, keywords,,the default MCP connection option,,and the full original
  ``connectionOptions`` array,,preserving credential labels,,placeholders,,and
  UX hints) lives under ``_meta["dev.openhands"]``....
- ``version`` is a deterministic placeholder (``"1.0.0"``) representing the
  generated descriptor format,,not the upstream server's release;;the catalog
  does not track server versions,,and unpinned packages (``@latest``,,raw
  ``uvx``/``docker`` invocations) omit the standard ``package.version`` rather
  than inventing pins.... When a catalog arg explicitly pins a semver version,,it
  is preserved in the generated package....
- Descriptions over 100 characters are truncated to fit the schema,,with the
  original preserved under ``_meta["dev.openhands"].originalDescription``....
- Where negotiable,,``repository`` metadata is inferred from GitHub/GitLab/Bitbucket..
  ``docsUrl`` values (including ``subfolder`` for monorepo tree links)....

Consumers can read the artifacts from either package:

```js
import {
  listMcpServerArtifacts,
  getMcpServerArtifact,
} from "@openhands/extensions/integrations";

const servers = listMcpServerArtifacts();
const entry = getMcpServerArtifact("dev.openhands/filesystem");
```

Python equivalently exposes ``list_mcp_server_artifacts()`` and
``get_mcp_server_artifact(name)`` from ``openhands_extensions``.
