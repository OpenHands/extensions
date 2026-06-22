import { readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const catalogDir = path.join(root, "integrations", "catalog");
const outputPath = path.join(root, "integrations", "catalog-index.js");

const files = (await readdir(catalogDir))
  .filter((file) => file.endsWith(".json"))
  .sort((left, right) => left.localeCompare(right));

const integrations = await Promise.all(
  files.map(async (file) => ({
    file,
    entry: JSON.parse(await readFile(path.join(catalogDir, file), "utf8")),
  })),
);

integrations.sort((left, right) => {
  const rank = (right.entry.popularityRank ?? -1) - (left.entry.popularityRank ?? -1);
  return rank || left.entry.id.localeCompare(right.entry.id);
});

const indexedIntegrations = integrations.map((integration, index) => ({
  ...integration,
  importName: `entry${index}`,
}));

const imports = indexedIntegrations
  .map(({ file, importName }) => `import ${importName} from "./catalog/${file}" with { type: "json" };`)
  .join("\n");
const entries = indexedIntegrations.map(({ importName }) => `  ${importName},`).join("\n");

const body = `${imports}\n\nexport const INTEGRATION_CATALOG_ENTRIES = [\n${entries}\n];\n`;
await writeFile(outputPath, body);
