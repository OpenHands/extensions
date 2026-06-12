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
}

export const INTEGRATION_CATALOG: IntegrationCatalogEntry[];
export function listOAuthProviderCatalog(): OAuthProviderCatalogOption[];
export function getOAuthProviderRegistrationDefaults(
  slug: string,
): OAuthProviderRegistrationDefaults | undefined;

export const hubspotMcpServerUrl: string;
export const hubspotMcpAuthorizationUrl: string;
export const hubspotMcpTokenUrl: string;
export const hubspotRequiredScopes: readonly string[];
export const hubspotOptionalScopes: readonly string[];

export default INTEGRATION_CATALOG;
