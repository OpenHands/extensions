import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import process from "node:process";

const root = resolve(import.meta.dirname, "..");
const main = await readFile(resolve(root, "native/main.go"));
const goMod = await readFile(resolve(root, "native/go.mod"));
const goSum = await readFile(resolve(root, "native/go.sum"));
const metadataPath = resolve(root, "native/artifact-metadata.json");
const metadata = JSON.parse(await readFile(metadataPath, "utf8"));
const digest = (value) => createHash("sha256").update(value).digest("hex");
const expected = {
  source_sha256: createHash("sha256").update(main).update("\0").update(goMod).update("\0").update(goSum).digest("hex"),
  main_go_sha256: digest(main),
  go_mod_sha256: digest(goMod),
  go_sum_sha256: digest(goSum),
};
const stale = Object.entries(expected).filter(([key, value]) => metadata[key] !== value);
if (process.argv.includes("--sync")) {
  Object.assign(metadata, expected);
  await writeFile(metadataPath, `${JSON.stringify(metadata, null, 2)}\n`);
} else if (stale.length) {
  throw new Error(`Native source metadata is stale: ${stale.map(([key]) => key).join(", ")}. Run node scripts/check-native-metadata.mjs --sync.`);
}
console.log(`Native metadata OK: Go source ${expected.source_sha256.slice(0, 16)}…; Bleve dependency is pinned.`);
