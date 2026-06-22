/**
 * Runtime integration catalog.
 *
 * The source of truth is the hand-authored JSON asset
 * `integrations/integration-catalog.json` (mirrored byte-for-byte into the
 * Python package). Each per-integration entry also exists as
 * `integrations/catalog/<id>.json`; CI asserts these copies stay in sync.
 * Both the JS package and the Python package read the same JSON at runtime.
 */
import catalogAsset from "./integration-catalog.json" with { type: "json" };

const RAW_INTEGRATIONS = catalogAsset.integrations;

const entrySupportsMcp = (entry) =>
  entry.connectionOptions.some((option) => option.provider === "mcp");

const entrySupportsOauth = (entry) =>
  entry.connectionOptions.some((option) => option.auth?.strategy === "oauth2");

const withDerivedFlags = (entry) => ({
  ...entry,
  supportsMcp: entrySupportsMcp(entry),
  supportsOauth: entrySupportsOauth(entry),
});

const INTEGRATIONS = RAW_INTEGRATIONS.map(withDerivedFlags);
const INTEGRATION_BY_ID = new Map(INTEGRATIONS.map((entry) => [entry.id, entry]));

export const listIntegrationCatalog = (filter) => {
  if (!filter) return INTEGRATIONS;
  const { mcp, oauth } = filter;
  if (mcp === undefined && oauth === undefined) return INTEGRATIONS;
  return INTEGRATIONS.filter((entry) => {
    const mcpOk = mcp === undefined || entry.supportsMcp === mcp;
    const oauthOk = oauth === undefined || entry.supportsOauth === oauth;
    return mcpOk && oauthOk;
  });
};

export const getIntegrationCatalogEntry = (id) => INTEGRATION_BY_ID.get(id);

export const INTEGRATION_CATALOG = INTEGRATIONS;

export default INTEGRATION_CATALOG;
