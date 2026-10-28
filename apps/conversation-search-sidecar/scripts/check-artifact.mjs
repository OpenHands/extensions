import { copyFile, readdir, readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";
import process from "node:process";

const appRoot = resolve(import.meta.dirname, "..");
const distRoot = resolve(appRoot, "dist");
const output = resolve(distRoot, "extension.js");
const files = await readdir(distRoot, { recursive: true });
if (files.length !== 1 || files[0] !== "extension.js") throw new Error(`Expected exactly dist/extension.js; found: ${files.join(", ") || "nothing"}`);
const info = await stat(output);
if (!info.isFile() || info.size === 0) throw new Error("dist/extension.js is empty or not a file.");
const source = await readFile(output, "utf8");
const forbidden = [
  [/(?:^|[;}]\s*)import\s*(?:\(|[\s{*])/, "a runtime import"],
  [/(?:^|[;}]\s*)export\s+[^;]*?\sfrom\s*["']/m, "a re-export dependency"],
  [/\bfrom\s*["'](?:\.?\.?\/|[A-Za-z@])/m, "an unresolved module specifier"],
  [/new\s+URL\(\s*["']\.?\.?\//m, "a relative URL asset"],
  [/sourceMappingURL=/, "a source map reference"],
  [/\brequire\s*\(/, "a CommonJS require call"],
  [/(?:src|href)\s*=\s*["']https?:/m, "an external runtime asset"],
];
for (const [pattern, description] of forbidden) if (pattern.test(source)) throw new Error(`extension.js contains ${description}: ${pattern}`);
const required = [
  [/export\s*\{[^}]*\bactivate\b/, "the activate export"],
  [/CONVERSATION_SEARCH_PROBE/, "the non-mutating prerequisite probe"],
  [/\.openhands\/apps\/conversation-search-sidecar/, "the isolated App data path"],
  [/execute_bash_command/, "the authenticated Bash bridge"],
  [/Bleve/, "the native full-text engine disclosure"],
  [/Delete exact directory/, "the destructive data confirmation"],
  [/Automatic idle shutdown/, "the daemon cleanup policy"],
  [/No conversation content is transmitted/, "the local privacy disclosure"],
];
for (const [pattern, description] of required) if (!pattern.test(source)) throw new Error(`extension.js is missing ${description}.`);
if (process.argv.includes("--sync")) await copyFile(output, resolve(appRoot, "extension.js"));
console.log(`Artifact OK: one self-contained Blob-compatible ESM file (${info.size.toLocaleString()} bytes), with inline Go source/CSS and no sibling runtime assets.`);
