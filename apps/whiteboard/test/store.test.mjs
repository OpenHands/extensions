import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { BoardStore, newBoardId, titleFromId } from "../src/store.js";

const ROOT = "/home/test/.openhands/apps/whiteboard/boards";

const notFound = () => {
  const err = new Error("Not Found");
  err.status = 404;
  return err;
};

/* An in-memory Agent Server file API: download, upload, create_directory
   and search_subdirs over a map of absolute paths. */
function fakeServer(files = {}) {
  const disk = new Map(Object.entries(files));
  const dirs = new Set();
  const requests = [];
  const query = (path) => new URL(`http://x${path}`).searchParams;
  const host = {
    agentServer: {
      async request(req) {
        requests.push(req);
        const { path, method = "GET", body } = req;
        if (path === "/api/file/home") return { home: "/home/test/" };
        if (path.startsWith("/api/file/download")) {
          const file = query(path).get("path");
          if (!disk.has(file)) throw notFound();
          return disk.get(file);
        }
        if (path.startsWith("/api/file/create_directory") && method === "POST") {
          dirs.add(query(path).get("path"));
          return {};
        }
        if (path.startsWith("/api/file/upload") && method === "POST") {
          disk.set(query(path).get("path"), await body.get("file").text());
          return {};
        }
        if (path.startsWith("/api/file/search_subdirs")) {
          const parent = query(path).get("path");
          const names = new Set();
          for (const file of [...disk.keys(), ...dirs]) {
            if (file.startsWith(`${parent}/`)) names.add(file.slice(parent.length + 1).split("/")[0]);
          }
          if (!names.size && ![...dirs].some((dir) => dir === parent)) throw notFound();
          return { items: [...names].map((name) => ({ name, path: `${parent}/${name}` })), next_page_id: null };
        }
        throw new Error(`unexpected request ${method} ${path}`);
      },
    },
  };
  return { host, disk, requests };
}

describe("BoardStore", () => {
  it("returns null for a board that was never saved", async () => {
    const { host, requests } = fakeServer();
    assert.equal(await new BoardStore(host).load("default"), null);
    const download = requests[1];
    assert.ok(download.path.startsWith(
      `/api/file/download?path=${encodeURIComponent(`${ROOT}/default/board.excalidraw`)}&_=`,
    ));
    assert.equal(download.headers["Cache-Control"], "no-cache");
  });

  it("round-trips a saved .excalidraw document", async () => {
    const { host, disk } = fakeServer();
    const store = new BoardStore(host);
    const scene = { type: "excalidraw", version: 2, elements: [{ id: "a" }], appState: {}, files: {} };
    await store.save("default", JSON.stringify(scene));
    assert.ok(disk.has(`${ROOT}/default/board.excalidraw`));
    assert.deepEqual(await store.load("default"), scene);
  });

  it("rejects documents that are not Excalidraw scenes", async () => {
    const { host } = fakeServer({ [`${ROOT}/default/board.excalidraw`]: '{"type":"other"}' });
    await assert.rejects(new BoardStore(host).load("default"), /not an Excalidraw document/);
  });

  it("propagates errors other than not-found", async () => {
    const host = {
      agentServer: {
        async request({ path }) {
          if (path === "/api/file/home") return { home: "/home/test" };
          const err = new Error("Internal Server Error");
          err.status = 500;
          throw err;
        },
      },
    };
    await assert.rejects(new BoardStore(host).load("default"), /Internal Server Error/);
    await assert.rejects(new BoardStore(host).list(), /Internal Server Error/);
  });

  it("lists nothing before any board exists", async () => {
    const { host } = fakeServer();
    assert.deepEqual(await new BoardStore(host).list(), []);
  });

  it("creates, renames and archives boards, listing the newest first", async () => {
    const { host, disk } = fakeServer({
      // A board saved before it had metadata still appears, titled from its id.
      [`${ROOT}/sprint-notes/board.excalidraw`]: '{"type":"excalidraw","elements":[]}',
    });
    const store = new BoardStore(host);
    const first = await store.create("  Q4   roadmap ");
    assert.equal(first.title, "Q4 roadmap");
    assert.match(first.id, /^q4-roadmap-[a-z0-9]{4}$/);
    await new Promise((resolve) => setTimeout(resolve, 2));
    const second = await store.create("");
    assert.equal(second.title, "Untitled board");

    let boards = await store.list();
    assert.deepEqual(boards.map((b) => b.title), ["Untitled board", "Q4 roadmap", "Sprint notes"]);

    await store.rename(first.id, "Launch plan");
    const meta = JSON.parse(disk.get(`${ROOT}/${first.id}/meta.json`));
    assert.equal(meta.title, "Launch plan");
    assert.equal(meta.createdAt, first.createdAt);

    await store.archive(second.id);
    boards = await store.list();
    assert.deepEqual(boards.map((b) => b.title), ["Launch plan", "Sprint notes"]);
    assert.ok(disk.has(`${ROOT}/${second.id}/meta.json`), "archiving deletes nothing");
    await assert.rejects(store.rename(first.id, "   "), /needs a name/);
  });

  it("preserves all concurrent metadata updates for a board", async () => {
    const { host } = fakeServer();
    const store = new BoardStore(host);
    await Promise.all([
      store.updateMeta("default", { updatedAt: "2026-01-01" }),
      store.rename("default", "Launch plan"),
      store.archive("default"),
    ]);
    const meta = await store.readMeta("default");
    assert.equal(meta.updatedAt, "2026-01-01");
    assert.equal(meta.title, "Launch plan");
    assert.equal(meta.archived, true);
  });

  it("continues metadata updates after an upload failure", async () => {
    const { host } = fakeServer();
    const request = host.agentServer.request;
    let fail = true;
    // Fail only the transport; exercise the real store's queued recovery.
    host.agentServer.request = async (req) => {
      if (fail && req.path.startsWith("/api/file/upload")) {
        fail = false;
        throw new Error("Controlled upload failure");
      }
      return request(req);
    };
    const store = new BoardStore(host);
    const failed = store.rename("default", "Failed title");
    const archived = store.archive("default");
    await assert.rejects(failed, /Controlled upload failure/);
    await archived;
    assert.equal((await store.readMeta("default")).archived, true);
    await store.rename("default", "Recovered title");
    assert.equal((await store.readMeta("default")).title, "Recovered title");
  });

  it("treats unreadable metadata as missing", async () => {
    const { host } = fakeServer({ [`${ROOT}/default/meta.json`]: "{not json" });
    assert.deepEqual(await new BoardStore(host).readMeta("default"), {
      id: "default", title: "Default", createdAt: null, updatedAt: null, archived: false,
    });
  });

  it("refuses board ids that could escape the boards directory", async () => {
    const { host, requests } = fakeServer();
    const store = new BoardStore(host);
    await assert.rejects(store.save("../secrets", "{}"), /Invalid board id/);
    await assert.rejects(store.rename("a/b", "x"), /Invalid board id/);
    assert.ok(requests.every((req) => !req.path.includes("secrets")));
  });

  it("requires an absolute home directory and retries after a failure", async () => {
    let calls = 0;
    const host = {
      agentServer: {
        request: async () => {
          calls += 1;
          return calls === 1 ? { home: "relative" } : { home: "/srv" };
        },
      },
    };
    const store = new BoardStore(host);
    await assert.rejects(store.root(), /absolute home/);
    assert.equal(await store.root(), "/srv/.openhands/apps/whiteboard/boards");
  });
});

describe("board ids and titles", () => {
  it("derives URL-safe ids from titles", () => {
    const zero = () => 0;
    assert.equal(newBoardId("Café Ideas!", zero), "cafe-ideas-0000");
    assert.equal(newBoardId("日本語", zero), "board-0000");
    assert.match(newBoardId("x".repeat(100)), /^x{40}-[a-z0-9]{4}$/);
  });

  it("titles boards that have no metadata", () => {
    assert.equal(titleFromId("sprint-plan"), "Sprint plan");
  });
});


