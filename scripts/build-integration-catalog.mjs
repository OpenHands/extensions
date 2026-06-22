#!/usr/bin/env node
/**
 * Generates the checked-in unified integration catalog asset
 * (integrations/integration-catalog.json). The authoring source —
 * `integrations/integration-catalog-source.mjs` (which merges the
 * per-integration JSON files with `oauth-provider-catalog-source.mjs` and
 * `oauth-provider-registration-defaults-source.js`) — is the ONLY place the
 * catalog is assembled; this script imports it to emit the JSON. Both the JS
 * package (`integrations/index.js`) and the Python package
 * (`python/openhands_extensions`) read that same JSON asset at runtime, so the
 * two language bindings never drift. CI asserts the checked-in JSON matches a
 * fresh generation.
 *
 * Run `npm run build:integration-catalog` after editing the authoring source.
 *
 * Shape (see buildIntegrationCatalog()):
 *   {
 *     "integrations": IntegrationCatalogEntry[],          // unified; each entry
 *                                                          // carries oauth and/or
 *                                                          // mcp connectionOptions
 *                                                          // + supportsOauth/supportsMcp
 *     "providers": OAuthProviderCatalogOption[],          // oauth-provider view
 *     "defaultManagedConnectors": ManagedConnector[],     // non-oauth2 providers
 *     "defaultManagedConnectorSlugs": string[]
 *   }
 */
import { writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// The authoring source. This is the ONLY place the catalog is assembled from
// hand-authored data; the runtime modules (JS and Python) read the generated
// JSON asset, not this source.
import { buildIntegrationCatalog } from "../integrations/integration-catalog-source.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Every location the generated catalog asset must be written to. There is a
 * single generation pass (below); each path receives a byte-identical copy so
 * the Python package (which reads its embedded copy) and CI see exactly the
 * same bytes as the JS authoring source generates. A parity test
 * (tests/test_integration_catalog_in_sync.py) asserts the checked-in copies
 * stay identical, so a maintainer who edits one without re-running
 * `npm run build:integration-catalog` fails CI.
 */
const OUTPUTS = [
  path.resolve(__dirname, "..", "integrations", "integration-catalog.json"),
  path.resolve(
    __dirname,
    "..",
    "python",
    "openhands_extensions",
    "integration-catalog.json",
  ),
];

/**
 * Build the unified integration catalog snapshot from the authoring source.
 * This is the producer side; runtime consumers read the generated JSON asset.
 * The shape is `{ integrations, providers, defaultManagedConnectors,
 * defaultManagedConnectorSlugs }` (see buildIntegrationCatalog).
 */
export function buildCatalog() {
  return buildIntegrationCatalog();
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (isMain) {
  const catalog = buildCatalog();
  const serialized = `${JSON.stringify(catalog, null, 2)}\n`;
  for (const output of OUTPUTS) {
    writeFileSync(output, serialized);
  }
  console.log(
    `Generated ${catalog.integrations.length} integrations, ` +
      `${catalog.providers.length} oauth providers, and ` +
      `${catalog.defaultManagedConnectors.length} default managed connectors -> ` +
      OUTPUTS.map((p) => path.relative(path.resolve(__dirname, ".."), p)).join(", "),
  );
}
