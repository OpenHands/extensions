export type MarketplaceFieldType = "text" | "password";

export interface MarketplaceField {
  key: string;
  label: string;
  type?: MarketplaceFieldType;
  placeholder?: string;
  helperText?: string;
  helperLink?: string;
  required?: boolean;
}

export type IntegrationTransport =
  | {
      kind: "shttp";
      url: string;
      apiKeyOptional?: boolean;
    }
  | {
      kind: "sse";
      url: string;
      apiKeyOptional?: boolean;
    }
  | {
      kind: "stdio";
      serverName: string;
      command: string;
      args: string[];
      envFields?: MarketplaceField[];
      argFields?: MarketplaceField[];
    };

export type IntegrationAuthStrategy =
  | "none"
  | "api_key"
  | "bearer"
  | "basic"
  | "oauth2";

export type IntegrationProvider = "mcp" | "http";

export interface IntegrationOAuthConfig {
  authorizationUrl?: string;
  tokenUrl?: string;
  scopes?: string[];
  optionalScopes?: string[];
  toolScopes?: string[];
  scopeSeparator?: "space" | "comma";
  pkce?: boolean;
  clientAuthentication?: "basic" | "body" | "none";
  registrationUrl?: string;
  additionalAuthorizationParams?: Record<string, string>;
  additionalTokenParams?: Record<string, string>;
}

export interface IntegrationAuthConfig {
  strategy: IntegrationAuthStrategy;
  authModes?: IntegrationAuthStrategy[];
  credentialLabel?: string;
  credentialPlaceholder?: string;
  credentialHelp?: string;
  credentialSecretName?: string;
  saveCredentialAsSecretByDefault?: boolean;
  apiKeyHeaderName?: string;
  apiKeyOptional?: boolean;
  oauth?: IntegrationOAuthConfig;
}

export interface IntegrationHttpDefaultTool {
  name: string;
  description?: string;
  method?: string;
  path?: string;
  scopes?: string[];
}

export interface IntegrationHttpConfig {
  apiBaseUrl?: string;
  openApiUrl?: string;
  defaultTool?: IntegrationHttpDefaultTool;
}

export interface IntegrationConnectionOption {
  id: "oauth" | "api" | "none" | string;
  provider: IntegrationProvider;
  transport?: IntegrationTransport;
  http?: IntegrationHttpConfig;
  auth: IntegrationAuthConfig;
}

export interface OAuthProviderRegistrationDefaults {
  provider?: IntegrationProvider;
  authModes?: IntegrationAuthStrategy[];
  authStrategy?: IntegrationAuthStrategy;
  credentialLabel?: string;
  credentialPlaceholder?: string;
  credentialHelp?: string;
  apiKeyHeaderName?: string;
  apiBaseUrl?: string;
  serverUrl?: string;
  openApiUrl?: string;
  authorizationUrl?: string;
  tokenUrl?: string;
  scopes?: string[];
  optionalScopes?: string[];
  toolScopes?: string[];
  scopeSeparator?: "space" | "comma";
  pkce?: boolean;
  clientAuthentication?: "basic" | "body" | "none";
  registrationUrl?: string;
  additionalAuthorizationParams?: Record<string, string>;
  additionalTokenParams?: Record<string, string>;
  toolName?: string;
  toolDescription?: string;
  requestMethod?: string;
  requestPath?: string;
}

export interface OAuthProviderCatalogOption {
  slug: string;
  name: string;
  description: string;
  categories: string[];
  authStrategy: IntegrationAuthStrategy;
  availability: "oauth_ready" | "manual_token" | "planned";
  managedConnectorSlug?: string;
  appUrl?: string;
  docsUrl?: string;
  notes: string;
  popularityRank: number;
  registrationDefaults?: OAuthProviderRegistrationDefaults;
}

export interface OAuthProviderOverride {
  /** OAuth-context description (when it differs from the integration's). */
  description?: string;
  /** OAuth-context docs URL (when it differs from the integration's). */
  docsUrl?: string;
  /** OAuth-context popularity rank (when it differs from the integration's). */
  popularityRank?: number;
}

export interface IntegrationCatalogEntry {
  id: string;
  kind: IntegrationProvider;
  name: string;
  description: string;
  categories?: string[];
  appUrl?: string;
  docsUrl?: string;
  notes?: string;
  iconBg?: string;
  iconColor?: string;
  keywords?: string[];
  popularityRank?: number;
  runtimeAvailability?: "all" | "local";
  catalogStatus?: "oauth_ready" | "manual_token" | "planned";
  managedConnectorSlug?: string;
  authStrategy?: IntegrationAuthStrategy;
  installHint?: string;
  defaultConnectionOptionId?: string;
  connectionOptions: IntegrationConnectionOption[];
  registrationDefaults?: OAuthProviderRegistrationDefaults;
  /**
   * OAuth-provider override for this integration. Non-null exactly when the
   * integration has an OAuth provider entry; carries only the fields whose
   * OAuth-context values differ from the integration's connector view. The
   * provider view is reconstructed at runtime by
   * {@link listOAuthProviderCatalog}.
   */
  oauthProvider?: OAuthProviderOverride | null;
  /** True if any connection option is an `mcp` connector (derived). */
  supportsMcp?: boolean;
  /** True if any connection option uses the `oauth2` auth strategy (derived). */
  supportsOauth?: boolean;
}

/**
 * Filter for {@link listIntegrationCatalog}. Each dimension is tri-state:
 * `true` keeps only entries that support that connector type, `false` keeps
 * only entries that do not, and `undefined` leaves that dimension unfiltered.
 */
export interface IntegrationCatalogFilter {
  /** Filter on whether the entry exposes at least one `mcp` connector. */
  mcp?: boolean;
  /** Filter on whether the entry exposes at least one `oauth2` connector. */
  oauth?: boolean;
}

export const INTEGRATION_CATALOG: IntegrationCatalogEntry[];
/**
 * Return the full integration catalog, optionally filtered by connector type.
 * Reads from the unified `integration-catalog.json` asset (single source of
 * truth shared with the Python package). Returns the cached array; callers
 * must treat it as read-only.
 */
export function listIntegrationCatalog(
  filter?: IntegrationCatalogFilter,
): IntegrationCatalogEntry[];
export function listOAuthProviderCatalog(): OAuthProviderCatalogOption[];
export function getOAuthProviderRegistrationDefaults(
  slug: string,
): OAuthProviderRegistrationDefaults | undefined;

/**
 * A default managed connector derived from a provider's registration defaults
 * (the non-oauth2 providers). Serialized into the catalog JSON asset as
 * `defaultManagedConnectors` and read back by both the JS and Python packages.
 */
export interface ManagedConnector {
  slug: string;
  name: string;
  description: string;
  appUrl?: string;
  docsUrl?: string;
  categories: string[];
  authModes: IntegrationAuthStrategy[];
  authStrategy: IntegrationAuthStrategy;
  provider: IntegrationProvider;
  credentialLabel: string;
  credentialPlaceholder: string;
  credentialHelp: string;
  apiKeyHeaderName?: string;
  apiBaseUrl?: string;
  openApiUrl?: string;
  serverUrl?: string;
  oauthConfigured: boolean;
}

/** Return the default managed connectors derived from the catalog. */
export function defaultManagedConnectors(): ManagedConnector[];

export default INTEGRATION_CATALOG;
