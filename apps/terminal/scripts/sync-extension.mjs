import { copyFile, readFile, readdir } from "node:fs/promises";
import { resolve } from "node:path";

const projectRoot = resolve(import.meta.dirname, "..");
const distDir = resolve(projectRoot, "dist");
const builtEntrypoint = resolve(distDir, "extension.js");
const manifestEntrypoint = resolve(projectRoot, "extension.js");

const files = await readdir(distDir);
if (files.length !== 1 || files[0] !== "extension.js") {
  throw new Error(`Expected exactly dist/extension.js, received: ${files.join(", ") || "no files"}`);
}

const source = await readFile(builtEntrypoint, "utf8");
if (!/export\s*\{[^}]*\bactivate\b[^}]*\}/s.test(source) && !/export\s+(?:async\s+)?function\s+activate\b/.test(source)) {
  throw new Error("The built entrypoint does not export activate.");
}
if (/(?:^|\n)\s*import\s+(?!["']data:)/m.test(source) || /\bimport\s*\(/.test(source)) {
  throw new Error("The built entrypoint contains an unresolved import.");
}
if (/\b(?:require\s*\(|module\.exports|process\.env|__dirname|__filename)/.test(source) || /["']node:[^"']+["']/.test(source)) {
  throw new Error("The built entrypoint contains a Node runtime dependency.");
}

await copyFile(builtEntrypoint, manifestEntrypoint);
console.log("Verified dist/extension.js and synchronized extension.js.");
