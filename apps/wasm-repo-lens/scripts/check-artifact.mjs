import { copyFile, readdir, readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";
import process from "node:process";

const appRoot = resolve(import.meta.dirname, "..");
const distRoot = resolve(appRoot, "dist");
const output = resolve(distRoot, "extension.js");
const files = await readdir(distRoot, { recursive: true });

if (files.length !== 1 || files[0] !== "extension.js") {
  throw new Error(`Expected exactly dist/extension.js; found: ${files.join(", ") || "nothing"}`);
}

const info = await stat(output);
if (!info.isFile() || info.size === 0) throw new Error("dist/extension.js is empty or not a file.");

const source = await readFile(output, "utf8");
const forbidden = [
  [/(?:^|[;}]\s*)import\s*(?:\(|[\s{*])/m, "a runtime import"],
  [/(?:^|[;}]\s*)export\s+[^;]*?\sfrom\s*["']/m, "a re-export dependency"],
  [/\bfrom\s*["'](?:\.?\.?\/|[A-Za-z@])/m, "an unresolved module specifier"],
  [/new\s+URL\(\s*["']\.?\.?\//m, "a relative URL asset"],
  [/sourceMappingURL=/, "a source map reference"],
  [/\brequire\s*\(/, "a CommonJS require call"],
  [/(?:src|href)\s*=\s*["']https?:/m, "an external runtime asset"],
];

for (const [pattern, description] of forbidden) {
  if (pattern.test(source)) throw new Error(`extension.js contains ${description}: ${pattern}`);
}

const required = [
  [/export\s*\{[^}]*\bactivate\b/, "the activate export"],
  [/data:application\/wasm;base64,/, "the embedded Rust/WASM engine"],
  [/WASM_REPO_LENS_PROBE/, "the fixed prerequisite command"],
  [/execute_bash_command/, "the controlled Agent Server command endpoint"],
  [/new Worker\(/, "the inline Worker runtime"],
  [/Source crosses one boundary/, "the data-boundary view"],
];

for (const [pattern, description] of required) {
  if (!pattern.test(source)) throw new Error(`extension.js is missing ${description}.`);
}

if (process.argv.includes("--sync")) await copyFile(output, resolve(appRoot, "extension.js"));
console.log(`Artifact OK: one self-contained ESM file (${info.size.toLocaleString()} bytes) with inline Worker, Rust/WASM, CSS, and no sibling runtime assets.`);
