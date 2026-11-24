/* Whiteboard persistence on the owning Agent Server.

   Each board is a directory below
   <agent-server-home>/.openhands/apps/whiteboard/boards/<id>/ holding:

   - board.excalidraw: a standard Excalidraw document, so it can be opened in
     excalidraw.com or read by an agent working on the same server;
   - meta.json: { title, createdAt, updatedAt, archived? }.

   A directory per board, rather than one shared index, is dictated by the
   file API: it can list subdirectories (search_subdirs) but not files, and it
   has no delete, rename or conditional write. Listing the directories keeps
   the disk the only source of truth, and two tabs creating boards never write
   the same document. Board ids are stable; renaming only changes the title,
   and "archive" hides a board without deleting anything.

   Only the Agent Server file API is used; the App never reads Canvas
   credentials. */

const STORE_SUBPATH = ".openhands/apps/whiteboard/boards";
export const BOARD_ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
export const MAX_TITLE_LENGTH = 80;

export function isNotFound(err) {
  const status = err?.status ?? err?.response?.status;
  if (status === 404) return true;
  return /\b404\b|not found/i.test(err?.message || "");
}

/** "sprint-plan" -> "Sprint plan": the title of a board with no metadata. */
export function titleFromId(id) {
  const words = id.replace(/-/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function normalizeTitle(title) {
  return String(title ?? "").replace(/\s+/g, " ").trim().slice(0, MAX_TITLE_LENGTH);
}

/** A new, URL-safe board id derived from its title. */
export function newBoardId(title, random = Math.random) {
  const slug = normalizeTitle(title)
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40)
    .replace(/-+$/, "");
  const suffix = Math.floor(random() * 36 ** 4).toString(36).padStart(4, "0");
  return `${slug || "board"}-${suffix}`;
}

export class BoardStore {
  constructor(host) {
    this.host = host;
    this.rootPromise = null;
    this.metadataWrites = new Map();
  }

  /** Absolute boards directory, resolved from the server's home once. */
  root() {
    if (!this.rootPromise) {
      this.rootPromise = this.host.agentServer
        .request({ path: "/api/file/home" })
        .then((res) => {
          const home = (typeof res === "string" ? JSON.parse(res) : res)?.home;
          if (typeof home !== "string" || !home.startsWith("/")) {
            throw new Error("The Agent Server did not report an absolute home directory.");
          }
          return `${home.replace(/\/+$/, "")}/${STORE_SUBPATH}`;
        })
        .catch((err) => {
          this.rootPromise = null;
          throw err;
        });
    }
    return this.rootPromise;
  }

  async boardDir(id) {
    if (!BOARD_ID.test(id)) throw new Error(`Invalid board id: ${id}`);
    return `${await this.root()}/${id}`;
  }

  /** Parsed JSON at `path`, or null when the file does not exist. */
  async readJson(path) {
    let raw;
    try {
      // The file API sends no Cache-Control; never reuse a stale document.
      raw = await this.host.agentServer.request({
        path: `/api/file/download?path=${encodeURIComponent(path)}&_=${Date.now()}`,
        headers: { "Cache-Control": "no-cache" },
      });
    } catch (err) {
      if (isNotFound(err)) return null;
      throw err;
    }
    // The file API serves files as octet-stream, so Canvas hands back text.
    return typeof raw === "string" ? JSON.parse(raw) : raw;
  }

  async writeFile(dir, name, text) {
    await this.host.agentServer.request({
      method: "POST",
      path: `/api/file/create_directory?path=${encodeURIComponent(dir)}`,
    });
    const form = new FormData();
    form.append("file", new Blob([text], { type: "application/json" }), name);
    await this.host.agentServer.request({
      method: "POST",
      path: `/api/file/upload?path=${encodeURIComponent(`${dir}/${name}`)}`,
      body: form,
    });
  }

  /** Visible boards, most recently updated first. */
  async list() {
    const root = await this.root();
    const ids = [];
    let pageId = null;
    do {
      const query = new URLSearchParams({ path: root, limit: "100", _: Date.now() });
      if (pageId) query.set("page_id", pageId);
      let page;
      try {
        page = await this.host.agentServer.request({
          path: `/api/file/search_subdirs?${query}`,
          headers: { "Cache-Control": "no-cache" },
        });
      } catch (err) {
        if (isNotFound(err)) return [];
        throw err;
      }
      if (typeof page === "string") page = JSON.parse(page);
      for (const item of page?.items ?? []) {
        if (BOARD_ID.test(item?.name)) ids.push(item.name);
      }
      pageId = page?.next_page_id || null;
    } while (pageId);
    const boards = await Promise.all(ids.map((id) => this.readMeta(id)));
    return boards
      .filter((board) => !board.archived)
      .sort((a, b) => (b.updatedAt || "").localeCompare(a.updatedAt || "") || a.title.localeCompare(b.title));
  }

  /** Board metadata; boards without (valid) metadata get defaults. */
  async readMeta(id) {
    let meta = null;
    try {
      meta = await this.readJson(`${await this.boardDir(id)}/meta.json`);
    } catch (err) {
      if (!(err instanceof SyntaxError)) throw err;
    }
    const title = normalizeTitle(meta?.title) || titleFromId(id);
    return {
      id,
      title,
      createdAt: typeof meta?.createdAt === "string" ? meta.createdAt : null,
      updatedAt: typeof meta?.updatedAt === "string" ? meta.updatedAt : null,
      archived: meta?.archived === true,
    };
  }

  /** Read-modify-write of meta.json; returns the stored metadata. */
  async updateMeta(id, changes) {
    const previous = this.metadataWrites.get(id) ?? Promise.resolve();
    const write = previous.catch(() => {}).then(async () => {
      const { id: _, ...current } = await this.readMeta(id);
      const next = { ...current, ...changes };
      if (!next.archived) delete next.archived;
      await this.writeFile(await this.boardDir(id), "meta.json", JSON.stringify(next, null, 2));
      return { id, ...next };
    });
    this.metadataWrites.set(id, write);
    try {
      return await write;
    } finally {
      if (this.metadataWrites.get(id) === write) this.metadataWrites.delete(id);
    }
  }

  async create(title) {
    const name = normalizeTitle(title) || "Untitled board";
    const now = new Date().toISOString();
    return this.updateMeta(newBoardId(name), { title: name, createdAt: now, updatedAt: now });
  }

  async rename(id, title) {
    const name = normalizeTitle(title);
    if (!name) throw new Error("A board needs a name.");
    return this.updateMeta(id, { title: name });
  }

  async archive(id) {
    return this.updateMeta(id, { archived: true });
  }

  /** The stored scene, or null when the board has never been saved. */
  async load(id) {
    const path = `${await this.boardDir(id)}/board.excalidraw`;
    const scene = await this.readJson(path);
    if (scene === null) return null;
    if (!scene || scene.type !== "excalidraw" || !Array.isArray(scene.elements)) {
      throw new Error(`${path} is not an Excalidraw document.`);
    }
    return scene;
  }

  /** Writes `json` (a serialized .excalidraw document) as the board. */
  async save(id, json) {
    await this.writeFile(await this.boardDir(id), "board.excalidraw", json);
  }
}
