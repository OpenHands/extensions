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
      /**
       * Named request headers the user must supply (e.g. Datadog's
       * `DD-API-KEY` / `DD-APPLICATION-KEY`). Values are sent verbatim as
       * headers on every MCP request. The direct analog of stdio's
       * `envFields`: each entry renders one input in the install modal,
       * `type: "password"` entries are secret-saved by default, and
       * `required` entries are validated before submit. Composes with the
       * `api_key`/`bearer`/`basic` auth strategies (whose Bearer token is
       * folded into `Authorization` separately); a header field with
       * `key: "Authorization"` is redundant and should be avoided.
       */
      headerFields?: MarketplaceField[];
      /**
       * When true, the install modal renders the URL as an editable input
       * pre-filled with `url` instead of read-only. Use for servers whose
       * host is region/account-specific (e.g. Datadog's
       * `https://mcp.<site>.datadoghq.com/v1/mcp`); pair with the entry's
       * `installHint` to tell users what to change.
       */
      urlEditable?: boolean;
    }
  | {
      kind: "sse";
      url: string;
      apiKeyOptional?: boolean;
      /** See {@link IntegrationTransport} `shttp` `headerFields`. */
      headerFields?: MarketplaceField[];
      /** See {@link IntegrationTransport} `shttp` `urlEditable`. */
      urlEditable?: boolean;
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

export interface IntegrationHttpConfig {
  apiBaseUrl?: string;
  openApiUrl?: string;
}

export interface IntegrationConnectionOption {
  id: "oauth" | "api" | "none" | string;
  provider: IntegrationProvider;
  transport?: IntegrationTransport;
  http?: IntegrationHttpConfig;
  auth: IntegrationAuthConfig;
}


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
  logoUrl?: string;
  keywords?: string[];
  popularityRank?: number;
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
 * Reads the generated static import index over `integrations/catalog/<id>.json`.
 * Returns an independent copy, matching the Python read API.
 */
export function listIntegrationCatalog(
  filter?: IntegrationCatalogFilter,
): IntegrationCatalogEntry[];
/** Return one integration catalog entry by id as an independent copy. */
export function getIntegrationCatalogEntry(
  id: string,
): IntegrationCatalogEntry | undefined;
export default INTEGRATION_CATALOG;
