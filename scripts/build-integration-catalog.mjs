#!/usr/bin/env node
/**
 * Generates the checked-in OAuth provider catalog asset
 * (integrations/oauth-provider-catalog.json). The JS package is the authoring
 * and runtime source — `integrations/oauth-provider-catalog.js` (plus
 * `oauth-provider-registration-defaults.js`) — and this script imports it to
 * emit the JSON. The Python package (`python/openhands_extensions`) reads its
 * embedded copy of that same JSON at runtime. CI asserts the checked-in JSON
 * matches a fresh generation so the two language bindings never drift.
 *
 * Run `npm run build:integration-catalog` after editing the JS source files.
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

/**
 * Every location the generated catalog asset must be written to. There is a
 * single generation pass (below); each path receives a byte-identical copy so
 * the Python package (which reads its embedded copy) and CI see exactly the
 * same bytes as the JS source generates. A parity test
 * (tests/test_integration_catalog_in_sync.py) asserts the checked-in copies
 * stay identical, so a maintainer who edits one without re-running
 * `npm run build:integration-catalog` fails CI.
 */
const OUTPUTS = [
  path.resolve(__dirname, "..", "integrations", "oauth-provider-catalog.json"),
  path.resolve(
    __dirname,
    "..",
    "python",
    "openhands_extensions",
    "oauth-provider-catalog.json",
  ),
];

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
  const serialized = `${JSON.stringify(catalog, null, 2)}\n`;
  for (const output of OUTPUTS) {
    writeFileSync(output, serialized);
  }
  console.log(
    `Generated ${catalog.providers.length} providers and ` +
      `${catalog.defaultManagedConnectors.length} default managed connectors -> ` +
      OUTPUTS.map((p) => path.relative(path.resolve(__dirname, ".."), p)).join(", "),
  );
}
