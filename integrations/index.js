/**
 * Runtime integration catalog.
 *
 * The single source of truth is the unified JSON asset
 * `integrations/integration-catalog.json`, generated from the JS authoring
 * source (`integration-catalog-source.mjs`, which merges the per-integration
 * JSON files under `integrations/catalog/` with the OAuth provider
 * registration defaults) by `scripts/build-integration-catalog.mjs`. Both the
 * JS package (this module) and the Python package (`openhands_extensions`)
 * read that same JSON asset at runtime, so the two language bindings can never
 * drift. A CI parity test regenerates the JSON from the authoring source and
 * asserts the checked-in copy matches.
 *
 * Each catalog entry carries one or more `connectionOptions`, each of which is
 * an oauth and/or an mcp/http connector, plus `supportsOauth` / `supportsMcp`
 * flags. Use `listIntegrationCatalog({ mcp, oauth })` to filter.
 */
import catalogAsset from "./integration-catalog.json" with { type: "json" };

const INTEGRATIONS = catalogAsset.integrations;
const PROVIDERS = catalogAsset.providers;
const DEFAULT_MANAGED_CONNECTORS = catalogAsset.defaultManagedConnectors;

/**
 * Return the full integration catalog, optionally filtered by connector type.
 *
 * @param {{ mcp?: boolean, oauth?: boolean }} [filter]
 *   - `mcp: true`  -> only entries that expose at least one `mcp` connector.
 *   - `oauth: true` -> only entries that expose at least one `oauth2` connector.
 *   - `mcp: false` / `oauth: false` -> only entries that do NOT expose that
 *     connector type. Omitting a flag leaves that dimension unfiltered.
 * @returns the cached array (read-only by contract).
 */
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

/**
 * Return the OAuth provider catalog (provider-level registration defaults).
 * Reads from the unified JSON asset; returns the cached array (read-only).
 */
export const listOAuthProviderCatalog = () => PROVIDERS;

/**
 * Return the registration defaults for `slug`, or `undefined`.
 */
export const getOAuthProviderRegistrationDefaults = (slug) => {
  const provider = PROVIDERS.find((p) => p.slug === slug);
  return provider?.registrationDefaults;
};

/**
 * Return the default managed connectors derived from the OAuth provider
 * catalog. Mirrors `defaultManagedConnectors` in the unified JSON asset.
 */
export const defaultManagedConnectors = () => DEFAULT_MANAGED_CONNECTORS;

export const INTEGRATION_CATALOG = INTEGRATIONS;

export default INTEGRATION_CATALOG;
