#!/usr/bin/env node
import { readdir, readFile, realpath, stat } from "node:fs/promises";
import path from "node:path";

const name = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const semver = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/;
const imports = /(?:^|[;}\n])\s*import\s+(?:[^"'()]*?\s+from\s+)?["']([^"']+)["']|(?:^|[;}\n])\s*export\s+[^"']*?\s+from\s+["']([^"']+)["']/gm;
const forbidden = [
  [/(?:^|[;}\n])\s*import\s*\(/m, "runtime dynamic import"],
  [/\bexport\s+[^;]*?\sfrom\s*["']/m, "re-exported dependency"],
  [/\bnew\s+URL\(\s*["']\.?\.?\//m, "relative URL asset"],
  [/\b(?:require\s*\(|module\.exports)/, "CommonJS dependency"],
  [/sourceMappingURL=/, "source-map reference"],
];

const [target, ...options] = process.argv.slice(2);
if (!target || target === "--help" || target === "-h") {
  console.log("Usage: validate-extension.mjs <app-directory> [--dist] [--marker <text>]");
  process.exit(target ? 0 : 2);
}
const checkDist = options.includes("--dist");
const markers = [];
for (let i = 0; i < options.length; i += 1) {
  if (options[i] === "--marker" && options[i + 1]) markers.push(options[++i]);
  else if (options[i] !== "--dist") throw new Error(`Unknown option: ${options[i]}`);
}
const root = path.resolve(target);
const errors = [];
const fail = (message) => errors.push(message);
const within = (parent, child) => {
  const relative = path.relative(parent, child);
  return relative !== "" && relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
};

let manifest;
try {
  if (!(await stat(root)).isDirectory()) throw new Error("not a directory");
  manifest = JSON.parse(await readFile(path.join(root, "canvas-extension.json"), "utf8"));
} catch (error) {
  console.error(`ERROR: Cannot read App package: ${error.message}`);
  process.exit(1);
}
if (!manifest || typeof manifest !== "object" || Array.isArray(manifest)) fail("Manifest root must be an object.");
if (manifest.schema_version !== 1) fail("Manifest schema_version must equal 1.");
for (const field of ["name", "version", "entrypoint"]) {
  if (typeof manifest[field] !== "string" || !manifest[field].trim()) fail(`Manifest ${field} must be a non-empty string.`);
}
if (typeof manifest.name === "string" && !name.test(manifest.name)) fail("Manifest name must use lowercase kebab-case.");
if (typeof manifest.version === "string" && !semver.test(manifest.version)) fail("Manifest version must use semantic versioning.");

const ids = new Set();
const paths = new Set();
const pages = manifest.contributes?.pages;
if (!Array.isArray(pages) || pages.length === 0) fail("Manifest must declare at least one routed page.");
for (const [index, page] of (pages ?? []).entries()) {
  const label = `contributes.pages[${index}]`;
  if (!page || typeof page !== "object" || Array.isArray(page)) { fail(`${label} must be an object.`); continue; }
  if (typeof page.id !== "string" || !name.test(page.id)) fail(`${label}.id must use lowercase kebab-case.`);
  if (typeof page.title !== "string" || !page.title.trim()) fail(`${label}.title must be a non-empty string.`);
  if (typeof page.path !== "string" || !/^\/(?:[a-z0-9]+(?:-[a-z0-9]+)*)(?:\/[a-z0-9]+(?:-[a-z0-9]+)*)*$/.test(page.path)) fail(`${label}.path must be an absolute kebab-case route.`);
  if (ids.has(page.id)) fail(`Page id ${page.id} is declared more than once.`); ids.add(page.id);
  if (paths.has(page.path)) fail(`Page path ${page.path} is declared more than once.`); paths.add(page.path);
}

const entrypoint = checkDist
  ? path.resolve(root, "dist", manifest.entrypoint ?? "")
  : path.resolve(root, manifest.entrypoint ?? "");
try {
  const [realRoot, realEntrypoint] = await Promise.all([realpath(root), realpath(entrypoint)]);
  if (!within(realRoot, realEntrypoint)) fail("Entrypoint escapes the App package root.");
  const source = await readFile(realEntrypoint, "utf8");
  if (!source.trim()) fail("Entrypoint is empty.");
  if (!/\bexport\s*(?:\{[^}]*\bactivate\b[^}]*\}|(?:async\s+)?function\s+activate\b)/m.test(source)) fail("Entrypoint must export activate.");
  for (const match of source.matchAll(imports)) {
    const specifier = match[1] ?? match[2];
    if (specifier && !specifier.startsWith("data:") && !specifier.startsWith("blob:")) fail(`Entrypoint contains unresolved module specifier: ${specifier}`);
  }
  for (const [pattern, description] of forbidden) if (pattern.test(source)) fail(`Entrypoint contains ${description}.`);
  for (const marker of markers) if (!source.includes(marker)) fail(`Entrypoint is missing required marker: ${marker}`);
  const registered = new Set([...source.matchAll(/\.registerPage\s*\(\s*["']([^"']+)["']/g)].map((match) => match[1]));
  for (const id of registered) if (!ids.has(id)) fail(`Entrypoint registers undeclared page id ${id}.`);
} catch (error) { fail(`Cannot read entrypoint: ${error.message}`); }

if (checkDist) {
  try {
    const files = await readdir(path.join(root, "dist"), { recursive: true });
    const expected = manifest.entrypoint;
    if (files.length !== 1 || files[0] !== expected) fail(`Expected exactly dist/${expected}; found ${files.join(", ") || "nothing"}.`);
  } catch (error) { fail(`Cannot inspect dist output: ${error.message}`); }
}
if (errors.length) { for (const error of errors) console.error(`ERROR: ${error}`); process.exit(1); }
console.log(`Canvas App validation passed: ${root}${checkDist ? " (dist)" : ""}`);
