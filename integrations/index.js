/**
 * Runtime integration catalog.
 *
 * The source of truth is the hand-authored `integrations/catalog/<id>.json`
 * directory. `catalog-index.js` is generated from that directory so the JS
 * package can statically import each JSON file without an aggregate JSON asset.
 */
import { INTEGRATION_CATALOG_ENTRIES } from "./catalog-index.js";
import { MCP_SERVER_ARTIFACTS } from "./mcp-servers/index.js";

const clone = (value) => JSON.parse(JSON.stringify(value));
const INTEGRATIONS = INTEGRATION_CATALOG_ENTRIES;
const INTEGRATION_BY_ID = new Map(INTEGRATIONS.map((entry) => [entry.id, entry]));
const MCP_SERVERS = MCP_SERVER_ARTIFACTS;
const MCP_SERVER_BY_NAME = new Map(MCP_SERVERS.map((artifact) => [artifact.name, artifact]));

const entrySupportsMcp = (entry) =>
  entry.connectionOptions.some((option) => option.provider === "mcp");

const entrySupportsOauth = (entry) =>
  entry.connectionOptions.some((option) => option.auth?.strategy === "oauth2");

export const listIntegrationCatalog = (filter) => {
  const entries =
    !filter || (filter.mcp === undefined && filter.oauth === undefined)
      ? INTEGRATIONS
      : INTEGRATIONS.filter((entry) => {
          const mcpOk =
            filter.mcp === undefined || entrySupportsMcp(entry) === filter.mcp;
          const oauthOk =
            filter.oauth === undefined ||
            entrySupportsOauth(entry) === filter.oauth;
          return mcpOk && oauthOk;
        });
  return clone(entries);
};

export const getIntegrationCatalogEntry = (id) => {
  const entry = INTEGRATION_BY_ID.get(id);
  return entry ? clone(entry) : undefined;
};

export const INTEGRATION_CATALOG = clone(INTEGRATIONS);

/**
 * Generated MCP `server.json` artifacts derived from `integrations/catalog/*.json`.
 * The catalog stays the hand-authored source of truth; these files are
 * one-way build output (see scripts/build-mcp-servers.mjs).
 */
export const MCP_SERVER_ARTIFACT_INDEX = clone(MCP_SERVERS);

/** Return every generated MCP server artifact as an independent copy. */
export const listMcpServerArtifacts = () => clone(MCP_SERVERS);

/** Return one generated MCP server artifact by its reverse-DNS `name`, or undefined. */
export const getMcpServerArtifact = (name) => {
  const artifact = MCP_SERVER_BY_NAME.get(name);
  return artifact ? clone(artifact) : undefined;
};

export default INTEGRATION_CATALOG;
