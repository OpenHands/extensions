/* Manager-automation tests.

   The archive is checked with GNU tar rather than a hand-rolled parser: the
   consumer is the automation backend's `tar -xz`, so "our own reader accepts
   it" would prove nothing. The upload is exercised against the REAL automation
   backend through the ingress, because the whole claim of manager.js is that a
   browser can create the automation app.py used to create — a mock would only
   restate the code. No automation is created here; that has side effects.

   Run: node --test kanban-manager/test/manager.test.mjs
*/

import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { Manager, automationName, gzip, tar } from "../src/manager.js";

const here = dirname(fileURLToPath(import.meta.url));
const first = (...paths) => paths.find((p) => existsSync(p));

const INGRESS = process.env.VIBE_TEST_INGRESS || "http://127.0.0.1:8000";
const keyFile = first(
  join(here, "..", "..", "..", ".session-key"),
  "/root/git/vibe-manager/.session-key",
);
const KEY = process.env.OH_SESSION_API_KEYS_0
  || (keyFile ? readFileSync(keyFile, "utf8").trim() : "");

const AUTOMATION_DIR = join(here, "..", "src", "automation");
const MODULES = ["main.py", "vibestore.py", "vibectl.py"];

function realAutomationSources() {
  return Object.fromEntries(
    MODULES.map((name) => [name, readFileSync(join(AUTOMATION_DIR, name), "utf8")]),
  );
}

async function writeArchive(files) {
  const blob = await gzip(tar(files));
  const path = join(mkdtempSync(join(tmpdir(), "vibe-tar-")), "automation.tar.gz");
  writeFileSync(path, Buffer.from(await blob.arrayBuffer()));
  return path;
}

test("the archive is a gzipped tar GNU tar reads back byte for byte", async () => {
  const files = { ...realAutomationSources(), "config.json": '{"workspace_id": "w1"}\n' };
  const path = await writeArchive(files);

  const listed = execFileSync("tar", ["-tzf", path], { encoding: "utf8" })
    .trim().split("\n").sort();
  assert.deepEqual(listed, Object.keys(files).sort());

  for (const [name, content] of Object.entries(files)) {
    const extracted = execFileSync("tar", ["-xzOf", path, name], { encoding: "utf8" });
    assert.equal(extracted, content, `${name} round-trips`);
  }
});

test("sizes are byte counts, not character counts", async () => {
  // main.py is full of em dashes; a length in characters truncates the file
  // and every following header lands mid-stream.
  const path = await writeArchive({ "u.txt": "héllo — ünïcode\n" });
  assert.equal(
    execFileSync("tar", ["-xzOf", path, "u.txt"], { encoding: "utf8" }),
    "héllo — ünïcode\n",
  );
});

test("the automation name matches the one app.py bootstraps", () => {
  assert.equal(
    automationName({ id: "8b3f89df77ab", name: "vibe-manager" }),
    "Vibe Manager — vibe-manager (8b3f89df77ab)",
  );
});

/* --------------------------------------------------------------- live calls */

function hostAndCreds(base = INGRESS) {
  globalThis.localStorage = {
    getItem: (key) =>
      (key === "openhands-backends"
        ? JSON.stringify([{ id: "local", host: base, apiKey: KEY }])
        : null),
  };
  return {
    backend: { id: "local" },
    agentServer: {
      async request({ method = "GET", path, body }) {
        const res = await fetch(`${base}${path}`, {
          method,
          headers: { "Content-Type": "application/json", "X-Session-API-Key": KEY },
          ...(body !== undefined && method !== "GET" ? { body: JSON.stringify(body) } : {}),
        });
        if (!res.ok) {
          const err = new Error(`${res.status} ${res.statusText}`);
          err.status = res.status;
          throw err;
        }
        return res.json();
      },
    },
  };
}

const live = { skip: !KEY && "no session key available" };

test("the automation backend accepts the browser-built tarball", live, async () => {
  const manager = new Manager(hostAndCreds(), { storeRoot: async () => "/tmp/vibe-store" });
  const blob = await gzip(tar({
    ...realAutomationSources(),
    "config.json": '{"workspace_id": "probe"}\n',
  }));
  const tarballPath = await manager.upload({ id: "probe", path: "/tmp/probe" }, blob);
  assert.match(tarballPath, /^oh-internal:\/\/uploads\//);
});

test("an automation nobody created is not found", live, async () => {
  const manager = new Manager(hostAndCreds(), { storeRoot: async () => "/tmp/vibe-store" });
  assert.equal(await manager.findByName("Vibe Manager — nope (0000deadbeef)"), null);
});
