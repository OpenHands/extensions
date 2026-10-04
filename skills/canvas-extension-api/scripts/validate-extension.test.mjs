import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const validator = new URL("./validate-extension.mjs", import.meta.url);

async function createApp(entrypoint, manifestOverrides = {}) {
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
      ...manifestOverrides,
    }),
  );
  await writeFile(
    path.join(root, "dist", entrypoint),
    "export function activate() {}",
  );
  return root;
}

function validate(root, ...options) {
  return spawnSync(process.execPath, [validator.pathname, root, ...options], {
    encoding: "utf8",
  });
}

const backend = {
  schema_version: 1,
  artifacts: {
    "linux-amd64": {
      path: "backend/linux-amd64.tar.gz",
      sha256: "a".repeat(64),
    },
    "linux-arm64": {
      path: "backend/linux-arm64.tar.gz",
      sha256: "b".repeat(64),
    },
  },
  argv: ["{artifact_dir}/bin/service", "--port", "{port}", "--data", "{data_dir}"],
  health: { path: "/health", timeout_seconds: 30, interval_seconds: 0.1 },
  inherit_environment: ["LANG", "TZ"],
};

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

test("accepts a package-owned backend declaration", async () => {
  const root = await createApp("extension.js", { backend });
  try {
    const result = validate(root, "--dist");
    assert.equal(result.status, 0, result.stderr);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("rejects a backend artifact path outside the package", async () => {
  const root = await createApp("extension.js", {
    backend: {
      ...backend,
      artifacts: {
        "linux-amd64": {
          path: "../service.tar.gz",
          sha256: "a".repeat(64),
        },
      },
    },
  });
  try {
    const result = validate(root, "--dist");
    assert.notEqual(result.status, 0);
    assert.match(
      result.stderr,
      /backend\.artifacts\[linux-amd64\]\.path must be a contained relative \.tar\.gz path/,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("rejects a backend argument vector that is not a structured list", async () => {
  const root = await createApp("extension.js", {
    backend: { ...backend, argv: "service --port {port}" },
  });
  try {
    const result = validate(root, "--dist");
    assert.notEqual(result.status, 0);
    assert.match(
      result.stderr,
      /backend\.argv must be a non-empty array of strings/,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("rejects a backend executable outside the prepared artifact", async () => {
  const root = await createApp("extension.js", {
    backend: { ...backend, argv: ["bin/service", "--port", "{port}"] },
  });
  try {
    const result = validate(root, "--dist");
    assert.notEqual(result.status, 0);
    assert.match(
      result.stderr,
      /backend\.argv\[0\] must execute from \{artifact_dir\}/,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("rejects a backend executable that traverses outside the artifact", async () => {
  const root = await createApp("extension.js", {
    backend: { ...backend, argv: ["{artifact_dir}/../outside"] },
  });
  try {
    const result = validate(root, "--dist");
    assert.notEqual(result.status, 0);
    assert.match(
      result.stderr,
      /backend\.argv\[0\] must resolve inside \{artifact_dir\}/,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("rejects unsupported backend argument placeholders", async () => {
  const root = await createApp("extension.js", {
    backend: { ...backend, argv: ["{artifact_dir}/bin/service", "{secret}"] },
  });
  try {
    const result = validate(root, "--dist");
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /backend\.argv contains unsupported placeholder \{secret\}/);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("rejects invalid backend health settings", async () => {
  const root = await createApp("extension.js", {
    backend: { ...backend, health: { path: "health", timeout_seconds: 0 } },
  });
  try {
    const result = validate(root, "--dist");
    assert.notEqual(result.status, 0);
    assert.match(
      result.stderr,
      /backend\.health\.path must be a root-relative HTTP path/,
    );
    assert.match(
      result.stderr,
      /backend\.health\.timeout_seconds must be greater than 0 and at most 300/,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});



test("accepts omitted managed backend health defaults", async () => {
  const root = await createApp("extension.js", {
    backend: { ...backend, health: {} },
  });
  try {
    const result = validate(root, "--dist");
    assert.equal(result.status, 0, result.stderr);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("rejects disallowed or duplicate inherited environment names", async () => {
  const root = await createApp("extension.js", {
    backend: { ...backend, inherit_environment: ["LANG", "SECRET", "LANG"] },
  });
  try {
    const result = validate(root, "--dist");
    assert.notEqual(result.status, 0);
    assert.match(
      result.stderr,
      /backend\.inherit_environment must contain unique names from the supported non-credential allowlist/,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("preserves browser-only packages without a backend declaration", async () => {
  const root = await createApp("extension.js");
  try {
    const result = validate(root, "--dist");
    assert.equal(result.status, 0, result.stderr);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("preserves manual sidecars with no managed backend declaration", async () => {
  const root = await createApp("extension.js", {
    description: "Connects to a deployment-owned sidecar configured by an operator.",
  });
  try {
    const result = validate(root, "--dist");
    assert.equal(result.status, 0, result.stderr);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
