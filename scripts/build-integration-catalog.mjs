#!/usr/bin/env node
/**
 * Generates integrations/oauth-provider-catalog.json, the single source of
 * truth for the OAuth provider catalog. Both the JS package
 * (integrations/oauth-provider-catalog.js) and the Python package
 * (python/openhands_extensions) read this asset at runtime so the two language
 * bindings never drift.
 *
 * The generator source is the JS module chain
 * (oauth-provider-catalog.js + oauth-provider-registration-defaults.js); run
 * `npm run build:integration-catalog` after editing those files. CI asserts
 * the checked-in JSON matches a fresh generation (see
 * tests/test_integration_catalog_in_sync.py).
 *
 * Shape (mirrors listOAuthProviderCatalog()):
 *   {
 *     "providers": OAuthProviderCatalogOption[],
 *     "defaultManagedConnectors": ManagedConnector[]   // providers whose
 *                                                       // registrationDefaults
 *                                                       // describe a non-oauth2
 *                                                       // default managed connector
 *   }
 */
import { writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { listOAuthProviderCatalog } from "../integrations/oauth-provider-catalog.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUTPUT = path.resolve(__dirname, "..", "integrations", "oauth-provider-catalog.json");

const isDefaultManagedConnectorProvider = (provider) => {
  const defaults = provider.registrationDefaults;
  if (!defaults?.authStrategy || defaults.authStrategy === "oauth2") {
    return false;
  }
  if (defaults.provider === "http" && defaults.apiBaseUrl && defaults.openApiUrl) {
    return true;
  }
  if (defaults.provider === "mcp" && defaults.serverUrl) {
    return true;
  }
  return false;
};

const defaultManagedConnector = (provider) => {
  const defaults = provider.registrationDefaults;
  return {
    slug: provider.managedConnectorSlug ?? provider.slug,
    name: provider.name,
    description: provider.description,
    appUrl: provider.appUrl,
    docsUrl: provider.docsUrl,
    categories: provider.categories,
    authModes:
      defaults.authModes?.length && defaults.authModes.every(Boolean)
        ? defaults.authModes
        : [defaults.authStrategy],
    authStrategy: defaults.authStrategy,
    provider: defaults.provider,
    credentialLabel: defaults.credentialLabel ?? `${provider.name} credential`,
    credentialPlaceholder:
      defaults.credentialPlaceholder ?? `Paste your ${provider.name} credential`,
    credentialHelp: defaults.credentialHelp ?? `Credential required by ${provider.name}.`,
    apiKeyHeaderName: defaults.apiKeyHeaderName?.trim() || undefined,
    apiBaseUrl: defaults.apiBaseUrl,
    openApiUrl: defaults.openApiUrl,
    serverUrl: defaults.serverUrl,
    oauthConfigured: true,
  };
};

export function buildCatalog() {
  const providers = listOAuthProviderCatalog();
  return {
    providers,
    defaultManagedConnectors: providers
      .filter(isDefaultManagedConnectorProvider)
      .map(defaultManagedConnector),
  };
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (isMain) {
  const catalog = buildCatalog();
  writeFileSync(OUTPUT, `${JSON.stringify(catalog, null, 2)}\n`);
  console.log(
    `Generated ${OUTPUT} with ${catalog.providers.length} providers and ` +
      `${catalog.defaultManagedConnectors.length} default managed connectors`,
  );
}
