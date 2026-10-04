/**
 * Runtime integration catalog.
 *
 * The source of truth is the hand-authored `integrations/catalog/<id>.json`
 * directory. `catalog-index.js` is generated from that directory so the JS
 * package can statically import each JSON file without an aggregate JSON asset.
 */
import { INTEGRATION_CATALOG_ENTRIES } from "./catalog-index.js";

const clone = (value) => JSON.parse(JSON.stringify(value));
const INTEGRATIONS = INTEGRATION_CATALOG_ENTRIES;
const INTEGRATION_BY_ID = new Map(INTEGRATIONS.map((entry) => [entry.id, entry]));

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

export default INTEGRATION_CATALOG;
