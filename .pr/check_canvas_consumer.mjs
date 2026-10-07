// Execute the actual Canvas catalog adapter without installing the whole UI.
// node .pr/check_canvas_consumer.mjs ../OpenHands /path/to/typescript/lib/typescript.js
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { getIntegrationCatalogEntry } from "../integrations/index.js";

const [canvasRoot, typescriptPath] = process.argv.slice(2);
assert(canvasRoot && typescriptPath, "Provide Canvas checkout and TypeScript paths");
const tsModule = await import(pathToFileURL(path.resolve(typescriptPath)).href);
const ts = tsModule.default ?? tsModule;
const source = await readFile(
  path.join(canvasRoot, "src/utils/mcp-marketplace-utils.ts"), "utf8",
);
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ESNext, module: ts.ModuleKind.ESNext },
});
const adapter = await import(
  `data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`
);
const entry = getIntegrationCatalogEntry("azure-devops");
assert(entry);
assert.equal(adapter.getMcpMarketplaceCatalog([entry]).length, 1);
const remote = adapter.getDefaultMcpConnectionOption(entry);
assert.equal(remote.transport.kind, "shttp");
assert.equal(remote.transport.url, "https://mcp.dev.azure.com/");
// The marketplace cannot collect the Entra client ID yet. Its existing filter
// must select the PAT form while custom/server-aware clients can use remote.
const local = adapter.getInstallableMcpConnectionOption(entry);
assert.equal(local.id, "pat");
assert.equal(local.transport.kind, "stdio");
console.log(JSON.stringify({
  marketplaceVisible: true,
  preferredConnection: remote.id,
  canvasInstallForm: local.id,
  organizationField: local.transport.argFields[0].key,
  secretField: local.transport.envFields[0].key,
}, null, 2));
