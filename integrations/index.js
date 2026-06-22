/**
 * Runtime integration catalog.
 *
 * The single source of truth is the hand-authored JSON asset
 * `integrations/integration-catalog.json` (mirrored byte-for-byte into the
 * Python package). It is NOT generated from any `.mjs`/`.js` source: humans
 * edit it directly, and each per-integration entry also exists as
 * `integrations/catalog/<id>.json` (a CI parity test asserts the two never
 * drift). Both the JS package (this module) and the Python package
 * (`openhands_extensions`) read that same JSON asset at runtime, so the two
 * language bindings can never drift.
 *
 * The asset stores only canonical, non-duplicated data. Provider-specific
 * OAuth knowledge that used to live in a separate top-level `providers[]`
 * array is merged into each integration as a minimal `oauthProvider` override
 * object (`null` when the integration has no OAuth provider). Everything that
 * is derivable - `supportsMcp` / `supportsOauth`, the reconstructed
 * `providers[]` view, and `defaultManagedConnectors` - is computed here at
 * runtime so the asset stays minimal.
 *
 * Each catalog entry carries one or more `connectionOptions`, each of which is
 * an oauth and/or an mcp/http connector, plus `supportsOauth` / `supportsMcp`
 * flags (derived). Use `listIntegrationCatalog({ mcp, oauth })` to filter.
 */
import catalogAsset from "./integration-catalog.json" with { type: "json" };

const RAW_INTEGRATIONS = catalogAsset.integrations;
const DEFAULT_MANAGED_CONNECTOR_SLUGS = catalogAsset.defaultManagedConnectorSlugs;

const omitUndefined = (object) => {
  const out = {};
  for (const [key, value] of Object.entries(object)) {
    if (value !== undefined) out[key] = value;
  }
  return out;
};

const entrySupportsMcp = (entry) =>
  entry.connectionOptions.some((option) => option.provider === "mcp");

const entrySupportsOauth = (entry) =>
  entry.connectionOptions.some((option) => option.auth?.strategy === "oauth2");

/** Attach the derived `supportsMcp` / `supportsOauth` flags to a raw entry. */
const withDerivedFlags = (entry) => ({
  ...entry,
  supportsMcp: entrySupportsMcp(entry),
  supportsOauth: entrySupportsOauth(entry),
});

const INTEGRATIONS = RAW_INTEGRATIONS.map(withDerivedFlags);

/**
 * Reconstruct the OAuth-provider view for an integration. The provider's
 * identity, UI metadata, and `registrationDefaults` already live on the
 * integration; `oauthProvider` carries only the fields whose OAuth-context
 * values differ from the integration's connector view
 * (`description`, `docsUrl`, `popularityRank`). `availability` is the
 * integration's `catalogStatus`; `slug` is the integration `id`.
 */
const reconstructProvider = (entry) => {
  const override = entry.oauthProvider ?? {};
  return omitUndefined({
    slug: entry.id,
    name: entry.name,
    description: override.description ?? entry.description,
    categories: entry.categories,
    availability: entry.catalogStatus,
    managedConnectorSlug: entry.managedConnectorSlug,
    appUrl: entry.appUrl,
    docsUrl: override.docsUrl ?? entry.docsUrl,
    notes: entry.notes ?? "",
    authStrategy: entry.authStrategy ?? "oauth2",
    popularityRank: override.popularityRank ?? entry.popularityRank,
    registrationDefaults: entry.registrationDefaults,
  });
};

const PROVIDERS = RAW_INTEGRATIONS.filter(
  (entry) => entry.oauthProvider !== null && entry.oauthProvider !== undefined,
).map(reconstructProvider);

/**
 * Build a default managed connector from an integration's provider view + its
 * non-oauth2 `registrationDefaults`. Mirrors the previous hub derivation.
 */
const toDefaultManagedConnector = (entry) => {
  const provider = reconstructProvider(entry);
  const defaults = provider.registrationDefaults ?? {};
  const authModes =
    Array.isArray(defaults.authModes) && defaults.authModes.length && defaults.authModes.every(Boolean)
      ? defaults.authModes
      : [defaults.authStrategy];
  return omitUndefined({
    slug: provider.managedConnectorSlug ?? provider.slug,
    name: provider.name,
    description: provider.description,
    appUrl: provider.appUrl,
    docsUrl: provider.docsUrl,
    categories: provider.categories,
    authModes,
    authStrategy: defaults.authStrategy,
    provider: defaults.provider,
    credentialLabel: defaults.credentialLabel ?? `${provider.name} credential`,
    credentialPlaceholder:
      defaults.credentialPlaceholder ?? `Paste your ${provider.name} credential`,
    credentialHelp: defaults.credentialHelp ?? `Credential required by ${provider.name}.`,
    apiKeyHeaderName: (defaults.apiKeyHeaderName ?? "").trim() || undefined,
    apiBaseUrl: defaults.apiBaseUrl,
    openApiUrl: defaults.openApiUrl,
    serverUrl: defaults.serverUrl,
    oauthConfigured: true,
  });
};

const PROVIDER_BY_SLUG = new Map(PROVIDERS.map((p) => [p.slug, p]));

const DEFAULT_MANAGED_CONNECTORS = DEFAULT_MANAGED_CONNECTOR_SLUGS.map((slug) => {
  const entry = RAW_INTEGRATIONS.find((e) => e.id === slug);
  return entry ? toDefaultManagedConnector(entry) : undefined;
}).filter(Boolean);

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
 * Return the OAuth provider catalog (provider-level registration defaults),
 * reconstructed at runtime from the integrations. Each integration with a
 * non-null `oauthProvider` yields one provider entry whose shape matches the
 * legacy `providers[]` contract. Returns the cached array (read-only).
 */
export const listOAuthProviderCatalog = () => PROVIDERS;

/**
 * Return the registration defaults for `slug`, or `undefined`.
 */
export const getOAuthProviderRegistrationDefaults = (slug) =>
  PROVIDER_BY_SLUG.get(slug)?.registrationDefaults;

/**
 * Return the default managed connectors derived from the catalog's
 * `defaultManagedConnectorSlugs`. Each slug is resolved to its integration and
 * materialized from the integration's provider view + `registrationDefaults`.
 */
export const defaultManagedConnectors = () => DEFAULT_MANAGED_CONNECTORS;

export const INTEGRATION_CATALOG = INTEGRATIONS;

export default INTEGRATION_CATALOG;
