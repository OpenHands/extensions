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

export type IntegrationAvailability = "oauth_ready" | "manual_token" | "planned";

export interface IntegrationCatalogEntry {
  id: string;
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
  availability?: IntegrationAvailability;
  installHint?: string;
  connectionOptions: IntegrationConnectionOption[];
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
 * Reads the generated `integration-catalog.json` package asset. The manually
 * edited source of truth is `integrations/catalog/<id>.json`. Returns the
 * cached array; callers must treat it as read-only.
 */
export function listIntegrationCatalog(
  filter?: IntegrationCatalogFilter,
): IntegrationCatalogEntry[];
export function getIntegrationCatalogEntry(
  id: string,
): IntegrationCatalogEntry | undefined;
export default INTEGRATION_CATALOG;
