/**
 * Runtime integration catalog.
 *
 * The source of truth is the hand-authored `integrations/catalog/<id>.json`
 * directory. `integration-catalog.json` is a generated package asset assembled
 * from that directory and mirrored byte-for-byte into the Python package. Both
 * JS and Python derive read-time convenience fields from `connectionOptions`.
 */
import catalogAsset from "./integration-catalog.json" with { type: "json" };

const RAW_INTEGRATIONS = catalogAsset.integrations;

const definedEntries = (entries) =>
  Object.fromEntries(entries.filter(([, value]) => value !== undefined));

const defaultConnectionOption = (entry) => entry.connectionOptions[0];

const entrySupportsMcp = (entry) =>
  entry.connectionOptions.some((option) => option.provider === "mcp");

const entrySupportsOauth = (entry) =>
  entry.connectionOptions.some((option) => option.auth?.strategy === "oauth2");

const registrationDefaultsFor = (entry) => {
  if (!entry.availability) return undefined;
  const option = defaultConnectionOption(entry);
  if (!option) return undefined;
  const auth = option.auth ?? {};
  const oauth = auth.oauth ?? {};
  const http = option.http ?? {};
  const tool = http.defaultTool ?? {};
  const transportUrl = option.transport?.url;
  return definedEntries([
    ["provider", option.provider],
    ["authModes", auth.authModes],
    ["authStrategy", auth.strategy],
    ["credentialLabel", auth.credentialLabel],
    ["credentialPlaceholder", auth.credentialPlaceholder],
    ["credentialHelp", auth.credentialHelp],
    ["credentialSecretName", auth.credentialSecretName],
    ["saveCredentialAsSecretByDefault", auth.saveCredentialAsSecretByDefault],
    ["apiKeyHeaderName", auth.apiKeyHeaderName],
    ["apiKeyOptional", auth.apiKeyOptional],
    ["apiBaseUrl", http.apiBaseUrl],
    ["serverUrl", transportUrl],
    ["openApiUrl", http.openApiUrl],
    ["authorizationUrl", oauth.authorizationUrl],
    ["tokenUrl", oauth.tokenUrl],
    ["scopes", oauth.scopes],
    ["optionalScopes", oauth.optionalScopes],
    ["toolScopes", oauth.toolScopes],
    ["scopeSeparator", oauth.scopeSeparator],
    ["pkce", oauth.pkce],
    ["clientAuthentication", oauth.clientAuthentication],
    ["registrationUrl", oauth.registrationUrl],
    ["additionalAuthorizationParams", oauth.additionalAuthorizationParams],
    ["additionalTokenParams", oauth.additionalTokenParams],
    ["toolName", tool.name],
    ["toolDescription", tool.description],
    ["requestMethod", tool.method],
    ["requestPath", tool.path],
  ]);
};

const withDerivedFields = (entry) => {
  const defaultOption = defaultConnectionOption(entry);
  const registrationDefaults = registrationDefaultsFor(entry);
  const supportsMcp = entrySupportsMcp(entry);
  const supportsOauth = entrySupportsOauth(entry);
  return definedEntries([
    ...Object.entries(entry),
    ["catalogStatus", entry.availability],
    ["defaultConnectionOptionId", defaultOption?.id],
    ["authStrategy", defaultOption?.auth?.strategy],
    ["managedConnectorSlug", entry.availability && entry.availability !== "planned" ? entry.id : undefined],
    ["registrationDefaults", registrationDefaults],
    ["supportsMcp", supportsMcp],
    ["supportsOauth", supportsOauth],
  ]);
};

const INTEGRATIONS = RAW_INTEGRATIONS.map(withDerivedFields);
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
