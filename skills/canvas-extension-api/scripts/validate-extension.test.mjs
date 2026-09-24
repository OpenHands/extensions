import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const validator = new URL("./validate-extension.mjs", import.meta.url);

async function createApp(entrypoint) {
  const root = await mkdtemp(path.join(os.tmpdir(), "canvas-extension-validator-"));
  await mkdir(path.join(root, "dist"), { recursive: true });
  await writeFile(
    path.join(root, "canvas-extension.json"),
    JSON.stringify({
      schema_version: 1,
      name: "validator-test",
      version: "1.0.0",
      entrypoint,
      contributes: {
        pages: [{ id: "home", title: "Home", path: "/home" }],
      },
    }),
  );
  await writeFile(
    path.join(root, "dist", entrypoint),
    "export function activate() {}",
  );
  return root;
}

test("--dist uses the manifest entrypoint name", async () => {
  const root = await createApp("bundle.mjs");
  try {
    const result = spawnSync(
      process.execPath,
      [validator.pathname, root, "--dist"],
      { encoding: "utf8" },
    );
    assert.equal(result.status, 0, result.stderr);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("--dist rejects sibling output chunks", async () => {
  const root = await createApp("extension.js");
  try {
    await writeFile(path.join(root, "dist", "lazy.js"), "export {};");
    const result = spawnSync(
      process.execPath,
      [validator.pathname, root, "--dist"],
      { encoding: "utf8" },
    );
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /Expected exactly dist\/extension\.js/);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
