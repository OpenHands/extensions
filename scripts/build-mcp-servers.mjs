// Generates MCP server.json artifacts from the integration catalog.
//
// Source of truth: integrations/catalog/<id>.json (hand-authored).
// Output: integrations/mcp-servers/<id>.json (schema-valid MCP server.json)
// plus integrations/mcp-servers/index.js (static import index for the JS package).
//
// Generation is one-way and deterministic: catalog entries with MCP connection
// options are folded into one server.json per entry, and MCP options that cannot be
// mapped to the MCP server schema (e.g. an npx GitHub shorthand or an unknown
// stdio launcher) are preserved under _meta["dev.openhands"].connectionOptions but
// omitted from the standard remotes/packages arrays. HTTP/OpenAPI-only entries
// are out of scope and not generated at all.
//
// Regenerate with: npm run build:mcp-servers
// Verify in sync with: node scripts/build-mcp-servers.mjs --check

import { mkdir, readdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";

export const NAMESPACE = "dev.openhands";
export const DESCRIPTOR_VERSION = "1.0.0";
export const SCHEMA_URI =
  "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json";

const ROOT = process.cwd();
const CATALOG_DIR = path.join(ROOT, "integrations", "catalog");
const OUT_DIR = path.join(ROOT, "integrations", "mcp-servers");

export const REGISTRY_BASE_URLS = {
  npm: "https://registry.npmjs.org",
  pypi: "https://pypi.org",
};

const flagRe = /^-(?:-[a-zA-Z0-9][a-zA-Z0-9-]*|[a-zA-Z])$/;
const npmPackageRe = /^(@[^/@]+\/)?[^/@]+$/;

function truncate(description) {
  if (description.length <= 100) return description;
  return `${description.slice(0, 97)}...`;
}

function sanitizeId(id) {
  return id.replace(/[^a-zA-Z0-9._-]/g, "-");
}

function inferRepository(docsUrl) {
  const url = String(docsUrl ?? "");
  const m = url.match(
    /^https:\/\/(github|gitlab|bitbucket)\.com\/([^/]+)\/([^/]+)(?:\/tree\/([^/]+)(\/(.*))?)?$/,
  );
  if (m === null) return undefined;
  const [, host, owner, repo, branch, , subfolder] = m;
  const repository = {
    url: `https://${host}.com/${owner}/${repo}`,
    source: host,
  };
  if ((branch === "main" || branch === "master") && subfolder) {
    repository.subfolder = subfolder;

  }
  return repository;
}

function fieldInput(field) {
  const input = {
    description: field.helperText ?? field.label,
    isRequired: Boolean(field.required),
    isSecret: field.type === "password",
  };
  if (field.placeholder) input.placeholder = field.placeholder;
  return input;
}

function keyValueInputs(fields) {
  const mappedFields = [];
  for (const field of fields ?? []) {
    mappedFields.push({ name: field.key, ...fieldInput(field) });
  }
  return mappedFields;
}

function parsePackageSpec(spec) {
  const match = spec.match(/^(@[^/@]+\/)?[^/@]+(@.*)?$/);
  if (match === null) return { identifier: spec };
  const pin = match[2];
  if (pin === undefined) return { identifier: spec };
  const version = pin.slice(1);
  const unpinned = spec.slice(0, spec.length - pin.length);
  if (version === "latest") return { identifier: unpinned };
  if (!/^[0-9]/.test(version)) return { identifier: spec };
  return { identifier: unpinned, version };
}

function mapArgs(args, argFields = []) {
  const mapped = [];
  for (const token of args ?? []) {
    const eq = token.indexOf("=");
    if (eq > -1 && flagRe.test(token.slice(0, eq))) {
      mapped.push({
        type: "named",
        name: token.slice(0, eq),
        value: token.slice(eq + 1),
      });
      continue;
    }
    if (flagRe.test(token)) {
      mapped.push({ type: "named", name: token });
      continue;
    }
    mapped.push({ type: "positional", value: token });
  }
  for (const field of argFields ?? []) {
    mapped.push({
      type: "positional",
      valueHint: field.key,
      ...fieldInput(field),
      isRepeated: /whitespace-separated|space separated/i.test(
        field.helperText ?? field.placeholder ?? "",
      ),
    });
  }
  return mapped;
}

function mapStdioPackage(option) {
  const t = option.transport;
  const args = t.args ?? [];
  switch (t.command) {
    case "npx": {
      if (args[0] !== "-y" || args[1] === undefined) {
        return { unsupported: "unsupported-npx-invocation" };
      }
      const spec = args[1];
      if (spec.startsWith("github:")) return { unsupported: "no-clean-npm-mapping" };
      const parsed = parsePackageSpec(spec);
      if (!npmPackageRe.test(parsed.identifier)) return { unsupported: "no-clean-npm-mapping" };
      const packageArgs = mapArgs(args.slice(2), t.argFields);
      return {
        package: {
          registryType: "npm",
          registryBaseUrl: REGISTRY_BASE_URLS.npm,
          identifier: parsed.identifier,
          ...(parsed.version ? { version: parsed.version } : {}),
          runtimeHint: "npx",
          transport: { type: "stdio" },
          ...(t.envFields?.length
            ? { environmentVariables: keyValueInputs(t.envFields) }
            : {}),
          ...(packageArgs.length ? { packageArguments: packageArgs } : {}),
        },
      };
    }
    case "uvx": {
      let argsAfter;
      let spec;
      if (args[0] === "--from") {
        if (args[1] === undefined) return { unsupported: "unsupported-uvx-invocation" };
        spec = args[1];
        const binaryName = args[2] ??  "";
        if (binaryName && binaryName !== spec.replace(/@.*$/, "")) {
          return { unsupported: "uvx-binary-name-mismatch" };
        }
        argsAfter = args.slice(3);
      } else {
        spec = args[0];
        argsAfter = args.slice(1);
      }
      if (spec === undefined) return { unsupported: "unsupported-uvx-invocation" };
      const parsedSpec = parsePackageSpec(spec);
      const pkgArgs = mapArgs(argsAfter, t.argFields);
      return {
        package: {
          registryType: "pypi",
          registryBaseUrl: REGISTRY_BASE_URLS.pypi,
          identifier: parsedSpec.identifier,
          ...(parsedSpec.version ? { version: parsedSpec.version } : {}),
          runtimeHint: "uvx",
          transport: { type: "stdio" },
          ...(t.envFields?.length
            ? { environmentVariables: keyValueInputs(t.envFields) }
            : {}),
          ...(pkgArgs.length ? { packageArguments: pkgArgs } : {}),
        },
      };
    }
    case "docker": {
      const image = args[args.length - 1];
      if (args[0] !== "run" || image === undefined) {
        return { unsupported: "unsupported-docker-invocation" };
      }
      const runtimeArgs = mapArgs(args.slice(1, -1));
      return {
        package: {
          registryType: "oci",
          identifier: `docker.io/${image}:latest`,
          runtimeHint: "docker",
          transport: { type: "stdio" },
          ...(t.envFields?.length
            ? { environmentVariables: keyValueInputs(t.envFields) }
            : {}),
          ...(runtimeArgs.length ? { runtimeArguments: runtimeArgs } : {}),
        },
      };
    }
    default:
      return { unsupported: `unsupported-command-${t.command}` };
  }
}

function buildRemotes(option) {
  const t = option.transport;
  const headers = [];
  for (const field of t.headerFields ?? []) {
    headers.push({ name: field.key, ...fieldInput(field) });
  }
  return [
    {
      type: t.kind === "sse" ? "sse" : "streamable-http",
      url: t.url,
      ...(headers.length ? { headers } : {}),
    },
  ];
}

export function buildArtifacts(entries) {
  const artifacts = new Map();
  for (const entry of entries) {
    const mcpOptions = (entry.connectionOptions ?? []).filter(
      (option) => option.provider === "mcp",
    );
    if (mcpOptions.length === 0) continue;
    const remotes = [];
    const packages = [];
    const skipped = [];
    let foundSupported = false;
    for (const option of mcpOptions) {
      const transport = option.transport;
      if (transport.kind === "shttp" || transport.kind === "sse") {
        remotes.push(...buildRemotes(option));
        foundSupported = true;
        continue;
      }
      if (transport.kind === "stdio") {
        const result = mapStdioPackage(option);
        if (result.package) {
          packages.push(result.package);
          foundSupported = true;
        } else {
          skipped.push({
            connectionOptionId: option.id,
            reason: result.unsupported,
          });
        }
        continue;
      }
      skipped.push({
        connectionOptionId: option.id,
        reason: `unsupported-transport-${transport.kind}`,
      });
    }
    if (!foundSupported) continue;
    const safeId = sanitizeId(entry.id);
    if (artifacts.has(safeId)) {
      throw new Error(
        `server.json name collision after id sanitization: ${entry.id} -> ${safeId}`,
      );
    }
    const meta = {
      catalogId: entry.id,
      descriptorVersion: DESCRIPTOR_VERSION,
      schemaDate: SCHEMA_URI.match(/schemas\/([^/]+)\//)?.[1],
      defaultMcpConnectionOptionId: mcpOptions[0].id,
      connectionOptions: entry.connectionOptions,
    };
    if (entry.installHint) meta.installHint = entry.installHint;
    if (entry.keywords?.length) meta.keywords = entry.keywords;

    if (entry.categories?.length) meta.categories = entry.categories;


    if (entry.popularityRank !== undefined) meta.popularityRank = entry.popularityRank;



    if (entry.notes) meta.notes = entry.notes;



    if (entry.description.length > 100) meta.originalDescription = entry.description;

    if (skipped.length) meta.skippedConnectionOptions = skipped;

    const artifact = {
      $schema: SCHEMA_URI ,
      name: `${NAMESPACE}/${safeId}`,
      description: truncate(entry.description),
      ...(entry.name ? { title: entry.name } : {}),
      ...(entry.docsUrl ? { websiteUrl: entry.docsUrl } : {}),
      repository: inferRepository(entry.docsUrl),
      version: DESCRIPTOR_VERSION,
      ...(remotes.length ? { remotes } : {}),
      ...(packages.length ? { packages } : {}),
      _meta: { [NAMESPACE]: meta },
    };
    if (artifact.repository === undefined) delete artifact.repository;
    artifacts.set(safeId, artifact);
  }
  return artifacts;
}


async function readCatalogEntries() {
  const files = (await readdir(CATALOG_DIR))
    .filter((file) => file.endsWith(".json"))
    .sort((left, right) => left.localeCompare(right));
  const entries = [];
  for (const file of files) {
    entries.push(JSON.parse(await readFile(path.join(CATALOG_DIR, file), "utf8")));
  }
  return entries;
}

function renderIndex(ids) {
  const imports = ids
    .map((id, index) => `import entry${index} from "./${id}.json" with { type: "json" };`)
    .join("\n");
  const entryLines = ids.map((_, index) => `  entry${index},`).join("\n");
  const header = `// This file is auto-generated by scripts/build-mcp-servers.mjs.

// Do not edit it manually. To regenerate after changing integrations/catalog/*.json,

// run: npm run build:mcp-servers

`;
  return `${header}${imports}

export const MCP_SERVER_ARTIFACTS = [
${entryLines}
];
`;
}

async function main({ check = false } = {}) {
  const entries = await readCatalogEntries();
  const artifacts = buildArtifacts(entries);
  const ids = [...artifacts.keys()].sort();
  const outputs = new Map(
    [...artifacts.entries()].map(([id, artifact]) => [
      `${id}.json`,
      `${JSON.stringify(artifact,null,2)}\n`,
    ]),
  );
  outputs.set("index.js", renderIndex(ids));

  if (check) {
    const expected = new Set(outputs.keys());
    const onDisk = new Set(await readdir(OUT_DIR).catch(() => []));
    const problems = [];
    for (const name of onDisk) {
      if (!expected.has(name)) problems.push(`unexpected file: ${name}`);
    }
    for (const [name, content] of outputs) {
      if (!onDisk.has(name)) {
        problems.push(`missing file: ${name}`);
        continue;
      }
      const current = await readFile(path.join(OUT_DIR, name), "utf8").catch(() => null);
      if (current !== content) problems.push(`out of sync: ${name}`);
    }
    if (problems.length) {
      console.error("integrations/mcp-servers is not in sync with integrations/catalog:");
      for (const problem of problems) console.error(`  - ${problem}`);
      console.error("Run: npm run build:mcp-servers");
      process.exit(1);
    }
    return;
  }

  await rm(OUT_DIR, { recursive: true, force: true });
  await mkdir(OUT_DIR, { recursive: true });
  for (const [name, content] of outputs) {
    await writeFile(path.join(OUT_DIR, name), content);
  }
}

const isCli = process.argv[1]?.endsWith("build-mcp-servers.mjs");
if (isCli) {
  main({ check: process.argv.includes("--check") }).catch((error) => {
    console.error(error);
    process.exit(1);
  });
}
