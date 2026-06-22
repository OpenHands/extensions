import { readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const catalogDir = path.join(root, "integrations", "catalog");
const assetPaths = [
  path.join(root, "integrations", "integration-catalog.json"),
  path.join(root, "python", "openhands_extensions", "integration-catalog.json"),
];

const files = (await readdir(catalogDir))
  .filter((file) => file.endsWith(".json"))
  .sort((left, right) => left.localeCompare(right));

const integrations = await Promise.all(
  files.map(async (file) => JSON.parse(await readFile(path.join(catalogDir, file), "utf8"))),
);

integrations.sort((left, right) => {
  const rank = (right.popularityRank ?? -1) - (left.popularityRank ?? -1);
  return rank || left.id.localeCompare(right.id);
});

const body = `${JSON.stringify({ integrations }, null, 2)}\n`;
await Promise.all(assetPaths.map((assetPath) => writeFile(assetPath, body)));
