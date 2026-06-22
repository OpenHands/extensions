/**
 * Runtime integration catalog.
 *
 * The source of truth is the hand-authored `integrations/catalog/<id>.json`
 * directory. `catalog-index.js` is generated from that directory so the JS
 * package can statically import each JSON file without an aggregate JSON asset.
 */
import { INTEGRATION_CATALOG_ENTRIES } from "./catalog-index.js";

const INTEGRATIONS = INTEGRATION_CATALOG_ENTRIES;
const INTEGRATION_BY_ID = new Map(INTEGRATIONS.map((entry) => [entry.id, entry]));

const entrySupportsMcp = (entry) =>
  entry.connectionOptions.some((option) => option.provider === "mcp");

const entrySupportsOauth = (entry) =>
  entry.connectionOptions.some((option) => option.auth?.strategy === "oauth2");

export const listIntegrationCatalog = (filter) => {
  if (!filter) return INTEGRATIONS;
  const { mcp, oauth } = filter;
  if (mcp === undefined && oauth === undefined) return INTEGRATIONS;
  return INTEGRATIONS.filter((entry) => {
    const mcpOk = mcp === undefined || entrySupportsMcp(entry) === mcp;
    const oauthOk = oauth === undefined || entrySupportsOauth(entry) === oauth;
    return mcpOk && oauthOk;
  });
};

export const getIntegrationCatalogEntry = (id) => INTEGRATION_BY_ID.get(id);

export const INTEGRATION_CATALOG = INTEGRATIONS;

export default INTEGRATION_CATALOG;
