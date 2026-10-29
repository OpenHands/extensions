import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const manifest = JSON.parse(await readFile(resolve(root, "canvas-extension.json"), "utf8"));
const entrypoint = resolve(root, manifest.entrypoint);
const icon = resolve(root, manifest.icon);
const source = await readFile(entrypoint, "utf8");

await stat(icon);
if (!/export\s+(?:async\s+)?function\s+activate\b/.test(source)) throw new Error("extension.js must export activate(host).");
if (/^\s*import\s+(?!\()/m.test(source) || /\bimport\s*\(/.test(source)) throw new Error("extension.js must not depend on external modules.");
console.log(`Artifact check OK: ${manifest.entrypoint} is a self-contained App entrypoint.`);
