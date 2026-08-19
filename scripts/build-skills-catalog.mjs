#!/usr/bin/env node
/**
 * Generates skills/index.js from the SKILL.md source files.
 *
 * Run manually or via `npm run build:skills` before publishing.
 * The generated file is checked into git so consumers get a normal
 * JS module import — no build-time filesystem reads needed.
 */
import { readdirSync, readFileSync, writeFileSync, statSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SKILLS_DIR = join(__dirname, "..", "skills");
const OUTPUT = join(SKILLS_DIR, "index.js");

const MARKETPLACES_DIR = join(__dirname, "..", "marketplaces");
const SKILL_SOURCE_PREFIX = "./skills/";

/**
 * Categories for skill entries, consumed by the agent-canvas /skills facet rail.
 *
 * Distinct from the `category` on marketplace *plugin* entries, which serves Claude Code marketplace browsing and keeps its own values.
 */
export const SKILL_CATEGORY_IDS = [
  "automations",
  "environment",
  "code-hosting",
  "agent-authoring",
  "code-quality",
  "integrations",
  "writing",
  "design",
  "other",
];

const FALLBACK_CATEGORY = "other";

/**
 * Build a `skill directory name -> {category, defaultEnabled, file}` map from every manifest.
 *
 * `defaultEnabled` is the manifest's answer to "is this skill on for every new
 * workspace?". Absent means off; a host resolving a fresh workspace turns on
 * exactly the entries that set it. `file` is kept only to name the offending
 * manifest in conflict errors.
 */
export function buildEntryMap(marketplacesDir) {
  const map = new Map();

  for (const filename of readdirSync(marketplacesDir).filter((f) => f.endsWith(".json")).sort()) {
    const manifest = JSON.parse(readFileSync(join(marketplacesDir, filename), "utf-8"));

    for (const entry of manifest.plugins ?? []) {
      const source = entry.source ?? "";
      if (!source.startsWith(SKILL_SOURCE_PREFIX)) continue;

      const name = source.slice(SKILL_SOURCE_PREFIX.length);
      const { category } = entry;

      if (!SKILL_CATEGORY_IDS.includes(category)) {
        throw new Error(
          `${filename}: skill "${name}" has category "${category}", expected one of: ${SKILL_CATEGORY_IDS.join(", ")}`,
        );
      }

      if ("defaultEnabled" in entry && typeof entry.defaultEnabled !== "boolean") {
        throw new Error(
          `${filename}: skill "${name}" has defaultEnabled ${JSON.stringify(entry.defaultEnabled)}, expected a boolean`,
        );
      }

      const defaultEnabled = entry.defaultEnabled === true;

      const existing = map.get(name);
      if (existing && existing.category !== category) {
        throw new Error(
          `Conflicting categories for skill "${name}": ${existing.file} says "${existing.category}", ${filename} says "${category}"`,
        );
      }
      if (existing && existing.defaultEnabled !== defaultEnabled) {
        throw new Error(
          `Conflicting defaultEnabled for skill "${name}": ${existing.file} says ${existing.defaultEnabled}, ${filename} says ${defaultEnabled}`,
        );
      }

      map.set(name, { category, defaultEnabled, file: filename });
    }
  }

  return map;
}

/** Minimal YAML frontmatter parser for the flat format used by SKILL.md. */
export function parseFrontmatter(raw) {
  const result = {};
  let currentKey = null;

  for (const line of raw.split("\n")) {
    // List items
    if (/^\s*-\s/.test(line)) {
      if (currentKey) {
        if (!Array.isArray(result[currentKey])) result[currentKey] = [];
        result[currentKey].push(line.replace(/^\s*-\s*/, ""));
      }
      continue;
    }
    // Key: value (allow hyphens in key names, e.g. event-key)
    const match = line.match(/^([\w-]+):\s*(.*)/);
    if (match) {
      currentKey = match[1];
      const value = match[2].trim();
      result[currentKey] = value && value !== ">" && value !== ">-" && value !== "|" ? value : "";
      continue;
    }
    // Continuation line
    if (currentKey && typeof result[currentKey] === "string" && line.trim()) {
      result[currentKey] = (result[currentKey] + " " + line.trim()).trim();
    }
  }

  return {
    name: result.name ?? "",
    description: result.description ?? "",
    triggers: Array.isArray(result.triggers) ? result.triggers : [],
    ...(result.license ? { license: result.license } : {}),
    ...(result.compatibility ? { compatibility: result.compatibility } : {}),
  };
}

/**
 * Build the catalog from SKILL.md files in the given directory.
 *
 * Pass an isolated `marketplacesDir` when building from fixtures; the default reads this repo's real manifests.
 */
export function buildCatalog(skillsDir, marketplacesDir = MARKETPLACES_DIR) {
  const entries = [];
  const manifestEntries = buildEntryMap(marketplacesDir);
  const uncategorized = [];

  for (const dir of readdirSync(skillsDir).sort()) {
    const dirPath = join(skillsDir, dir);
    if (!statSync(dirPath).isDirectory()) continue;
    const skillMd = join(dirPath, "SKILL.md");
    if (!existsSync(skillMd)) continue;

    const raw = readFileSync(skillMd, "utf-8").replace(/\r\n?/g, "\n");
    const parts = raw.split("---");
    if (parts.length < 3) {
      console.warn(`Warning: ${skillMd} missing frontmatter sections, skipping`);
      continue;
    }

    const fm = parseFrontmatter(parts[1]);
    const body = parts.slice(2).join("---").trim();

    const mapped = manifestEntries.get(dir);
    if (!mapped) uncategorized.push(dir);

    entries.push({
      name: fm.name?.trim() || dir,
      description: fm.description,
      triggers: fm.triggers,
      content: body,
      category: mapped?.category ?? FALLBACK_CATEGORY,
      // Emitted only when true, so the absent case stays the single off-by-default shape.
      ...(mapped?.defaultEnabled ? { defaultEnabled: true } : {}),
      ...(fm.license ? { license: fm.license } : {}),
      ...(fm.compatibility ? { compatibility: fm.compatibility } : {}),
    });
  }

  if (uncategorized.length > 0) {
    console.warn(
      `Warning: no marketplace entry, category defaults to "${FALLBACK_CATEGORY}": ${uncategorized.join(", ")}`,
    );
  }

  return entries;
}

// Run codegen when executed directly (not when imported as a module).
const isMain = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (isMain) {
  const entries = buildCatalog(SKILLS_DIR);
  const defaultEnabledNames = entries.filter((e) => e.defaultEnabled).map((e) => e.name);

  const source = `// Auto-generated by scripts/build-skills-catalog.mjs — do not edit.
// Source of truth: skills/*/SKILL.md and marketplaces/*.json (category, defaultEnabled)
export const SKILL_CATEGORY_IDS = ${JSON.stringify(SKILL_CATEGORY_IDS)};
export const SKILLS_CATALOG = ${JSON.stringify(entries, null, 2)};
export const DEFAULT_ENABLED_SKILL_NAMES = ${JSON.stringify(defaultEnabledNames)};
export default SKILLS_CATALOG;
`;

  writeFileSync(OUTPUT, source);
  console.log(`Generated ${OUTPUT} with ${entries.length} skills (${defaultEnabledNames.length} default-enabled)`);
}
