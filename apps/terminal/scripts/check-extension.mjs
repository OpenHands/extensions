import { readdir, readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const manifest = JSON.parse(await readFile(resolve(root, "canvas-extension.json"), "utf8"));
const distFiles = await readdir(resolve(root, "dist"), { recursive: true });
const built = await readFile(resolve(root, "dist/extension.js"), "utf8");
const checkedIn = await readFile(resolve(root, manifest.entrypoint), "utf8");

if (manifest.schema_version !== 1) throw new Error("Manifest schema_version must equal 1.");
if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(manifest.name)) throw new Error("Manifest name must use lowercase kebab-case.");
if (!/^\d+\.\d+\.\d+/.test(manifest.version)) throw new Error("Manifest version must use semantic versioning.");
if (!Array.isArray(manifest.contributes?.pages) || manifest.contributes.pages.length === 0) {
  throw new Error("Manifest must declare at least one page.");
}
if (distFiles.length !== 1 || distFiles[0] !== "extension.js") {
  throw new Error(`Expected exactly dist/extension.js; found ${distFiles.join(", ") || "nothing"}.`);
}
if (!built || built !== checkedIn) throw new Error("Checked-in extension.js does not match dist/extension.js.");

const forbidden = [
  [/(?:^|[;}\n])\s*import\s*(?:\(|[\s{*])/m, "a runtime import"],
  [/\bexport\s+[^;]*?\sfrom\s*["']/m, "a re-exported dependency"],
  [/\bnew\s+URL\(\s*["']\.?\.?\//m, "a relative URL asset"],
  [/\b(?:require\s*\(|module\.exports)/, "a CommonJS dependency"],
  [/sourceMappingURL=/, "a source-map reference"],
];
for (const [pattern, description] of forbidden) {
  if (pattern.test(built)) throw new Error(`extension.js contains ${description}.`);
}
if (!/\bexport\s*\{[^}]*\bactivate\b/.test(built)) throw new Error("extension.js must export activate.");

const declared = new Set(manifest.contributes.pages.map((page) => page.id));
for (const [, pageId] of built.matchAll(/\.registerPage\s*\(\s*["']([^"']+)["']/g)) {
  if (!declared.has(pageId)) throw new Error(`extension.js registers undeclared page ${pageId}.`);
}

console.log(`Canvas App artifact passed: ${manifest.name}@${manifest.version}`);
