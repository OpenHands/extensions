/* Tests run against the BUILT bundle (the manifest entrypoint), so they also
   cover the build. Excalidraw itself needs a real browser; it is exercised by
   test/blob-smoke.mjs. Here the board payload's import fails under Node, which
   doubles as coverage of the load-failure state.

   Run: npm test  (after npm run build)
*/

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";
import { parseHTML } from "linkedom";

const here = dirname(fileURLToPath(import.meta.url));
const MANIFEST = JSON.parse(readFileSync(join(here, "..", "canvas-extension.json"), "utf8"));
const BUNDLE = join(here, "..", MANIFEST.entrypoint);

const { document } = parseHTML("<!doctype html><html><head></head><body></body></html>");
globalThis.document = document;

const { activate, __testing } = await import(BUNDLE);

function makeHost({ request = async () => ({ home: "/home/test" }) } = {}) {
  const registrations = new Map();
  const host = {
    apiVersion: "1",
    extension: { name: "whiteboard", version: MANIFEST.version, resolvedRef: "test" },
    backend: { id: "local-test", kind: "local", orgId: null },
    registerPage(id, mount) {
      assert.ok(!registrations.has(id), `${id} registered twice`);
      registrations.set(id, mount);
      return () => registrations.delete(id);
    },
    navigate() {},
    agentServer: { request },
  };
  return { host, registrations };
}

const waitFor = async (predicate, timeout = 2000) => {
  const start = Date.now();
  while (!predicate()) {
    if (Date.now() - start > timeout) throw new Error("timed out");
    await new Promise((resolve) => setTimeout(resolve, 5));
  }
};

describe("whiteboard bundle", () => {
  it("is one self-contained ESM file", () => {
    const source = readFileSync(BUNDLE, "utf8");
    assert.doesNotMatch(source, /\bfrom\s*["'](?:\.?\.?\/|[A-Za-z@])/);
    assert.doesNotMatch(source, /sourceMappingURL=/);
    assert.doesNotMatch(source, /\brequire\s*\(/);
  });

  it("registers exactly the declared page and unregisters it", () => {
    const { host, registrations } = makeHost();
    const dispose = activate(host);
    assert.deepEqual([...registrations.keys()], MANIFEST.contributes.pages.map((page) => page.id));
    dispose();
    assert.equal(registrations.size, 0);
  });

  it("rejects an unsupported host API", () => {
    const { host } = makeHost();
    assert.throws(() => activate({ ...host, apiVersion: "2" }), /host API 1/);
  });

  it("offers a way back from an invalid board route and cleans up", () => {
    const { host, registrations } = makeHost();
    activate(host);
    const navigations = [];
    const container = document.createElement("div");
    const cleanup = registrations.get("board")({
      container,
      path: "Not_A_Board",
      navigate: (path) => navigations.push(path),
    });
    assert.match(container.querySelector('[role="alert"]').textContent, /not a valid board name/);
    container.querySelector("button").click();
    assert.deepEqual(navigations, ["/extensions/whiteboard/boards"]);
    cleanup();
    assert.equal(container.childElementCount, 0);
  });

  it("renders load failures safely with a retry, then cleans up", async () => {
    const requests = [];
    const { host, registrations } = makeHost({
      request: async (req) => {
        requests.push(req);
        if (req.path === "/api/file/home") return { home: "/home/test" };
        const err = new Error("Not Found");
        err.status = 404;
        throw err;
      },
    });
    activate(host);
    const container = document.createElement("div");
    const cleanup = registrations.get("board")({ container, path: "", navigate() {} });
    await waitFor(() => container.querySelector('[role="alert"]'));
    assert.match(container.textContent, /Unable to open the whiteboard/);
    assert.equal(container.querySelector("button").textContent, "Try again");
    assert.ok(requests.some((req) => req.path.startsWith(
      "/api/file/download?path=%2Fhome%2Ftest%2F.openhands%2Fapps%2Fwhiteboard%2Fboards%2Fdefault%2Fboard.excalidraw",
    )));
    cleanup();
    assert.equal(container.childElementCount, 0);
  });

  it("redirects away from an archived default board when another board exists", async () => {
    const files = {
      "/home/test/.openhands/apps/whiteboard/boards/default/meta.json": JSON.stringify({
        title: "Default",
        archived: true,
      }),
      "/home/test/.openhands/apps/whiteboard/boards/notes/meta.json": JSON.stringify({
        title: "Notes",
        createdAt: "2024-01-01T00:00:00.000Z",
        updatedAt: "2024-01-02T00:00:00.000Z",
      }),
    };
    const { host, registrations } = makeHost({
      request: async (req) => {
        if (req.path === "/api/file/home") return { home: "/home/test" };
        if (req.path.startsWith("/api/file/search_subdirs")) return { items: [{ name: "notes" }] };
        if (req.path.startsWith("/api/file/download")) {
          const filePath = new URL(req.path, "http://x").searchParams.get("path");
          if (filePath in files) return files[filePath];
          const err = new Error("Not Found");
          err.status = 404;
          throw err;
        }
        throw new Error(`unexpected request: ${req.path}`);
      },
    });
    activate(host);
    const navigations = [];
    const container = document.createElement("div");
    // The root route resolves to "default" (no last-board preference), which is archived.
    registrations.get("board")({ container, path: "", navigate: (path) => navigations.push(path) });
    await waitFor(() => navigations.length > 0);
    assert.deepEqual(navigations, ["/extensions/whiteboard/boards/notes"]);
  });

  it("offers to create a board when every board is archived, instead of reopening the archived default", async () => {
    const files = {
      "/home/test/.openhands/apps/whiteboard/boards/default/meta.json": JSON.stringify({
        title: "Default",
        archived: true,
      }),
    };
    const { host, registrations } = makeHost({
      request: async (req) => {
        if (req.path === "/api/file/home") return { home: "/home/test" };
        if (req.path.startsWith("/api/file/search_subdirs")) return { items: [] };
        if (req.method === "POST") return {};
        if (req.path.startsWith("/api/file/download")) {
          const filePath = new URL(req.path, "http://x").searchParams.get("path");
          if (filePath in files) return files[filePath];
          const err = new Error("Not Found");
          err.status = 404;
          throw err;
        }
        throw new Error(`unexpected request: ${req.path}`);
      },
    });
    activate(host);
    const navigations = [];
    const container = document.createElement("div");
    registrations.get("board")({ container, path: "", navigate: (path) => navigations.push(path) });
    await waitFor(() => container.querySelector("button"));
    assert.match(container.textContent, /All boards are archived/);
    assert.equal(container.querySelector("button").textContent, "Create a board");
    container.querySelector("button").click();
    await waitFor(() => navigations.length > 0);
    assert.match(navigations[0], /^\/extensions\/whiteboard\/boards\/untitled-board-[0-9a-z]{4}$/);
  });

  it("maps routes to board ids", () => {
    assert.equal(__testing.boardIdFromPath(""), "default");
    assert.equal(__testing.boardIdFromPath("sprint-plan/"), "sprint-plan");
    assert.equal(__testing.boardIdFromPath("a/b"), null);
    assert.equal(__testing.boardIdFromPath("../etc"), null);
  });

  it("ignores pointer-only changes when deciding to save", () => {
    const elements = [{ version: 3 }, { version: 7 }];
    const appState = { viewBackgroundColor: "#fff", cursorButton: "up" };
    const base = __testing.sceneSignature(elements, appState, {});
    assert.equal(__testing.sceneSignature(elements, { ...appState, cursorButton: "down" }, {}), base);
    assert.notEqual(__testing.sceneSignature([{ version: 3 }, { version: 8 }], appState, {}), base);
    assert.notEqual(__testing.sceneSignature(elements, { ...appState, viewBackgroundColor: "#000" }, {}), base);
    assert.notEqual(__testing.sceneSignature(elements, appState, { image: {} }), base);
  });
});
