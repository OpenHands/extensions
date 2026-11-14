/* Board state on disk, reached through the agent-server file API.

   Replaces the vibe-manager FastAPI service. Every call goes through the
   Canvas host's `agentServer.request`, which targets the active backend and
   attaches the session key — so there is no base URL to configure, no
   credentials to manage, and no cross-origin request to be blocked.

   Layout is documented in store/SCHEMA.md: an index.json listing workspaces,
   and one file per ticket under workspaces/<ws>/tickets/<id>/ticket.json.

   Tickets are stored per file because the browser is not the only writer —
   the automation and the manager's CLI write from the shell, where no lock
   spans the file API, and the API has no conditional upload to build a
   compare-and-swap on (a stale If-Match is accepted, not rejected). While the
   whole board was one document, any two writers collided: measured 35/40
   concurrent UI+manager writes silently lost the manager's edit, and adding
   rev/writer tokens only reduced that to 8/40 because a writer can confirm
   its own write landed without noticing it destroyed someone else's. Giving
   each ticket its own file removes the shared document, so edits to different
   tickets cannot collide at all. Documents that remain shared (index.json,
   and a ticket against itself) still carry `rev`/`writer` and go through
   `mutateDoc`. */

/* The store lives under the agent-server user's home. The file API needs
   absolute paths and does not expand "~", so the home directory is resolved
   once from GET /api/file/home rather than assuming /root — the agent server
   may run as any user, and in a sandbox it usually does. */
export const STORE_SUBPATH = ".openhands/vibe-manager";

export const STATUSES = ["pending", "in_progress", "needs_input", "finished"];
export const VERIFIED = "verified";
export const UNFINISHED_STATUSES = new Set(["pending", "in_progress", "needs_input"]);

/* Primary colour of a workspace's theme, stored on its index.json record. The
   palette lives in the stylesheet (--accent-<id>); this is only the fallback
   for records written before the field existed. */
export const DEFAULT_ACCENT = "ember";

/* Colour theme, also a per-workspace setting on the record. */
export const DEFAULT_THEME = "dark";

/* Spend cap (USD) a new request gets unless the user changes it. The
   automation enforces it by watching the worker conversation's cost. */
export const DEFAULT_BUDGET = 10;

export function newId() {
  const bytes = new Uint8Array(6);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function nowTs() {
  return Date.now() / 1000;
}

/* Stamp a document for the next write: `rev` counts writes so a racing writer
   is detectable, `writer` identifies this one so we can tell our own write
   from someone else's. Both are read by the shell side too (vibestore.py). */
export function stamp(doc, fields) {
  return { ...doc, ...fields, rev: (doc.rev || 0) + 1, writer: newId() };
}

/* Tickets come back in directory-listing order, so the board imposes its own.
   `sort_order` is assigned per column by drag-to-reorder; created_at breaks
   ties, which is what makes a stale sort_order on a new ticket harmless. */
export function byPriority(a, b) {
  const order = (a.sort_order || 0) - (b.sort_order || 0);
  return order !== 0 ? order : (a.created_at || 0) - (b.created_at || 0);
}

/* The file API keeps `filename` in a query param and writes it verbatim, so
   the same sanitizing the old service did has to happen here. */
export function safeFilename(name) {
  const base = String(name || "").replace(/\\/g, "/").split("/").pop().trim();
  const cleaned = base.replace(/[^A-Za-z0-9._ ()[\]-]+/g, "_").slice(0, 120)
    .replace(/^[._ ]+|[._ ]+$/g, "");
  return cleaned || "file";
}

/* Resolve the active backend's {host, apiKey} from the registry Canvas keeps
   in localStorage.

   Needed ONLY for binary downloads. `host.agentServer.request` parses an
   octet-stream body as text, which corrupts image bytes, and the host API
   exposes no responseType/blob option — so attachment previews have to issue
   their own fetch. This is the same registry Canvas's own automation client
   reads, but it is undocumented surface: if the host API ever grows a blob
   helper, delete this and use it. */
export function resolveBackendCredentials(backendId) {
  try {
    const raw = localStorage.getItem("openhands-backends");
    if (!raw) return null;
    const backends = JSON.parse(raw);
    if (!Array.isArray(backends)) return null;
    const match = backends.find((b) => b && b.id === backendId) || backends[0];
    if (!match || typeof match.host !== "string") return null;
    return { host: match.host.replace(/\/+$/, ""), apiKey: match.apiKey || "" };
  } catch {
    return null;
  }
}

export class Store {
  constructor(host, root = null) {
    this.host = host;
    this.root = root;
    this.rootPromise = null;
    this.mutationChain = Promise.resolve();
    /* Completed board writes. The UI reads this to tell a poll response that
       predates a local write from one that reflects it. */
    this.writes = 0;
  }

  /* Run a read-modify-write cycle with no other cycle in flight.

     A cycle is a download, an in-memory edit and an upload of the whole
     document, which takes long enough that a second one started meanwhile
     (a second submit, an attachment, a drag-reorder) downloads the document
     from *before* the first upload and then writes that stale copy back —
     silently dropping the ticket just created. There is no compare-and-set in
     the file API, so for our own writes the fix is not to overlap them; the
     writers outside this tab are caught by `mutateDoc` instead.

     `fn` must not call `serialize` again; the helpers it uses (readBoard,
     writeTicket, readIndex, writeIndex) are deliberately unserialized. */
  serialize(fn) {
    const done = this.mutationChain.then(fn);
    // A rejected cycle must not poison the queue, nor look unhandled here.
    this.mutationChain = done.then(() => {}, () => {});
    return done;
  }

  /** Absolute store root, resolved from the agent server's home dir once. */
  async storeRoot() {
    if (this.root) return this.root;
    if (!this.rootPromise) {
      this.rootPromise = this.host.agentServer
        .request({ path: "/api/file/home" })
        .then((res) => {
          const home = (typeof res === "string" ? JSON.parse(res) : res)?.home;
          if (!home) throw new Error("agent server did not report a home directory");
          this.root = `${home.replace(/\/+$/, "")}/${STORE_SUBPATH}`;
          return this.root;
        })
        .catch((err) => {
          // Allow a later call to retry instead of caching the failure.
          this.rootPromise = null;
          throw err;
        });
    }
    return this.rootPromise;
  }

  async indexPath() {
    return `${await this.storeRoot()}/index.json`;
  }

  async boardPath(wsId) {
    return `${await this.storeRoot()}/workspaces/${wsId}/board.json`;
  }

  async ticketsDir(wsId) {
    return `${await this.storeRoot()}/workspaces/${wsId}/tickets`;
  }

  /* Each ticket is a DIRECTORY holding ticket.json, not a bare file: the file
     API can enumerate subdirectories (search_subdirs) but has no endpoint that
     lists files, so this is the only shape the board can be rebuilt from. */
  async ticketPath(wsId, ticketId) {
    return `${await this.ticketsDir(wsId)}/${ticketId}/ticket.json`;
  }

  /** Ticket ids present on disk, via the only listing endpoint there is. */
  async listTicketIds(wsId) {
    const dir = await this.ticketsDir(wsId);
    const ids = [];
    let pageId = null;
    do {
      /* Cache-busted like readJson: a cached listing would omit a ticket
         directory created moments ago, which is precisely the "my card never
         showed up" symptom this layout exists to fix. */
      const query = new URLSearchParams({ path: dir, limit: "100", _: Date.now() });
      if (pageId) query.set("page_id", pageId);
      let page;
      try {
        page = await this.readJsonResponse(`/api/file/search_subdirs?${query}`);
      } catch (err) {
        // No tickets/ dir yet: pre-migration workspace, or one with no tickets.
        if (isNotFound(err)) return null;
        throw err;
      }
      for (const item of page.items || []) ids.push(item.name);
      pageId = page.next_page_id || null;
    } while (pageId);
    return ids;
  }

  async attachmentPath(attId, filename) {
    return `${await this.storeRoot()}/attachments/${attId}/${filename}`;
  }

  /** Binary-safe download. See resolveBackendCredentials for why this exists. */
  async fetchBlob(path, contentType) {
    const creds = resolveBackendCredentials(this.host?.backend?.id);
    if (!creds) throw new Error("no backend credentials available for binary download");
    const res = await fetch(
      `${creds.host}/api/file/download?path=${encodeURIComponent(path)}`,
      { headers: creds.apiKey ? { "X-Session-API-Key": creds.apiKey } : {} },
    );
    if (!res.ok) {
      const err = new Error(`${res.status} ${res.statusText}`);
      err.status = res.status;
      throw err;
    }
    const blob = await res.blob();
    // The file API always says octet-stream; re-tag so <img> renders it.
    return contentType ? blob.slice(0, blob.size, contentType) : blob;
  }

  // ---------------------------------------------------------------- file API

  /** GET a JSON API response (not a stored file). */
  async readJsonResponse(path) {
    const raw = await this.host.agentServer.request({
      path, headers: { "Cache-Control": "no-cache" },
    });
    return typeof raw === "string" ? JSON.parse(raw) : raw;
  }

  async readJson(path, fallback) {
    let raw;
    try {
      /* The file API sends ETag/Last-Modified but no Cache-Control, so the
         browser is free to reuse a stale board for its heuristic freshness
         window. That stalls the poll and, because every write is a
         read-modify-write, lets a stale read drop the previous ticket. Defeat
         it per read; attachments stay cacheable, they never change. */
      raw = await this.host.agentServer.request({
        path: `/api/file/download?path=${encodeURIComponent(path)}&_=${Date.now()}`,
        headers: { "Cache-Control": "no-cache" },
      });
    } catch (err) {
      // A missing document is an expected state (no workspaces onboarded yet,
      // freshly selected workspace); anything else is a real failure.
      if (fallback !== undefined && isNotFound(err)) return fallback;
      throw err;
    }
    // The file API serves every file as application/octet-stream, so the
    // Canvas client parses the body as text rather than JSON.
    if (typeof raw !== "string") return raw;
    try {
      return JSON.parse(raw);
    } catch (err) {
      throw new Error(`corrupt JSON at ${path}: ${err.message}`);
    }
  }

  async createDirectory(path) {
    await this.host.agentServer.request({
      path: `/api/file/create_directory?path=${encodeURIComponent(path)}`,
      method: "POST",
    });
  }

  async writeJson(path, payload) {
    await this.writeFile(path, new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    }), path.split("/").pop());
  }

  /* Read, apply `mutate`, write back — retrying when another writer lands in
     between. Both checks are needed: the file API offers no conditional
     upload, so a race is detected rather than prevented. Re-reading before
     the upload catches a write that arrived while we were preparing ours
     (theirs would otherwise be overwritten); re-reading after it catches a
     writer that had already read the pre-change document and overwrote us
     (our ticket would otherwise be silently dropped). */
  async mutateDoc(path, read, write, mutate, attempts = 5) {
    for (let attempt = 0; attempt < attempts; attempt += 1) {
      const doc = await read();
      const base = doc.rev || 0;
      const result = mutate(doc);
      const current = await read();
      if ((current.rev || 0) !== base) continue;
      const token = await write(doc);
      const after = await read();
      // `rev > base + 1` means someone built on top of our write, so it landed.
      if (after.writer === token || (after.rev || 0) > base + 1) return result;
    }
    throw new Error(`${path.split("/").pop()} is being written concurrently; try again`);
  }

  async writeFile(path, blob, filename) {
    const dir = path.slice(0, path.lastIndexOf("/"));
    await this.host.agentServer.request({
      method: "POST",
      path: `/api/file/create_directory?path=${encodeURIComponent(dir)}`,
    });
    const form = new FormData();
    form.append("file", blob, filename);
    await this.host.agentServer.request({
      method: "POST",
      path: `/api/file/upload?path=${encodeURIComponent(path)}`,
      body: form,
    });
  }

  // -------------------------------------------------------------- workspaces

  async readIndex() {
    const idx = await this.readJson(await this.indexPath(), { version: 1, workspaces: [] });
    return idx && Array.isArray(idx.workspaces) ? idx : { version: 1, workspaces: [] };
  }

  /** Writes the index and returns the token that identifies this write. */
  async writeIndex(index) {
    const stamped = stamp(index, { version: 1 });
    await this.writeJson(await this.indexPath(), stamped);
    return stamped.writer;
  }

  async mutateIndex(mutate) {
    const path = await this.indexPath();
    return this.serialize(() => this.mutateDoc(
      path,
      () => this.readIndex(),
      (index) => this.writeIndex(index),
      mutate,
    ));
  }

  /** Selected workspaces plus the candidates the agent server knows about. */
  async listWorkspaces() {
    const index = await this.readIndex();
    const selected = index.workspaces;
    const seen = new Set(selected.map((w) => w.path));

    let available = [];
    try {
      const data = await this.host.agentServer.request({ path: "/api/workspaces" });
      const parents = data?.workspaceParents || [];
      const entries = await Promise.all(
        parents.map(async (parent) => {
          try {
            const res = await this.host.agentServer.request({
              path: `/api/file/search_subdirs?path=${encodeURIComponent(parent.path)}`,
            });
            return res?.items || [];
          } catch {
            return [];
          }
        }),
      );
      available = entries
        .flat()
        .filter((item) => item.name && !item.name.startsWith(".") && !item.name.startsWith("_"))
        .map((item) => ({ path: item.path, name: item.name }));
    } catch {
      // Without the agent server we can still show what is already onboarded.
      available = [];
    }

    const merged = [...available.filter((a) => !seen.has(a.path))];
    return { available: merged, selected };
  }

  async unfinishedCounts(workspaces) {
    const boards = await Promise.all(workspaces.map((workspace) => this.readBoard(workspace.id)));
    return Object.fromEntries(workspaces.map((workspace, position) => [
      workspace.id,
      boards[position].tickets.filter(
        (ticket) => UNFINISHED_STATUSES.has(ticket.status),
      ).length,
    ]));
  }

  async selectWorkspace(path) {
    const existing = (await this.readIndex()).workspaces.find((w) => w.path === path);
    if (existing) return existing;

    let created = false;
    const ws = await this.mutateIndex((index) => {
      const already = index.workspaces.find((w) => w.path === path);
      created = !already;
      if (already) return already;
      const fresh = {
        id: newId(),
        path,
        name: path.split("/").filter(Boolean).pop() || path,
        max_concurrent: 2,
        push_mode: "main",
        accent: DEFAULT_ACCENT,
        theme: DEFAULT_THEME,
        show_verified: false,
        // null = "manager's choice"; the default request settings the ⚙
        // popover edits, applied to every new ticket on this board.
        llm_profile: null,
        max_budget: DEFAULT_BUDGET,
        automation_id: null,
        manager_conversation_id: null,
        created_at: nowTs(),
      };
      index.workspaces.push(fresh);
      return fresh;
    });
    // Create tickets/ up front so listing an empty board returns [] (a 404
    // means "not migrated yet" and would send readBoard down the legacy path).
    if (created) await this.createDirectory(await this.ticketsDir(ws.id));
    return ws;
  }

  async updateWorkspace(wsId, patch) {
    return this.mutateIndex((index) => {
      const ws = index.workspaces.find((w) => w.id === wsId);
      if (!ws) throw new Error("workspace not found");
      Object.assign(ws, patch);
      return ws;
    });
  }

  // ------------------------------------------------------------------ boards

  /* Rebuild the board by listing tickets/ and reading each ticket.json. Reads
     run in parallel; a ticket that vanishes mid-read (deleted between the list
     and the download) is skipped rather than failing the whole board. */
  async readBoard(wsId) {
    const ids = await this.listTicketIds(wsId);
    if (ids === null) return this.readLegacyBoard(wsId);
    const tickets = await Promise.all(
      ids.map((id) => this.readTicket(wsId, id).catch((err) => {
        if (isNotFound(err)) return null;
        throw err;
      })),
    );
    return {
      version: 2,
      workspace_id: wsId,
      tickets: tickets.filter(Boolean).sort(byPriority),
    };
  }

  /* Workspaces written before the per-ticket split still have a board.json.
     Reading it keeps them working until `migrateWorkspace` splits them. */
  async readLegacyBoard(wsId) {
    const board = await this.readJson(await this.boardPath(wsId), null);
    if (!board) return { version: 2, workspace_id: wsId, tickets: [] };
    return { ...board, tickets: (board.tickets || []).sort(byPriority) };
  }

  async readTicket(wsId, ticketId) {
    return this.readJson(await this.ticketPath(wsId, ticketId), null);
  }

  /** Writes one ticket and returns the token identifying this write. */
  async writeTicket(wsId, ticket) {
    const stamped = stamp(ticket, {});
    await this.writeJson(await this.ticketPath(wsId, ticket.id), stamped);
    this.writes += 1;
    return stamped.writer;
  }

  /* Read, mutate, write back a SINGLE ticket. Two writers touching different
     tickets no longer share a document, so they cannot lose each other's work;
     `mutateDoc` still guards the case where both touch the same ticket. */
  async mutateTicket(wsId, ticketId, mutate) {
    const path = await this.ticketPath(wsId, ticketId);
    return this.serialize(() => this.mutateDoc(
      path,
      async () => {
        const ticket = await this.readTicket(wsId, ticketId);
        if (!ticket) throw new Error("ticket not found");
        return ticket;
      },
      (ticket) => this.writeTicket(wsId, ticket),
      mutate,
    ));
  }

  /* Create is not a mutation of an existing document: the id is fresh, so no
     other writer can be holding this path and there is nothing to race. */
  async putNewTicket(wsId, ticket) {
    await this.writeTicket(wsId, ticket);
    return ticket;
  }

  async getBoard(wsId) {
    const [index, board] = await Promise.all([this.readIndex(), this.readBoard(wsId)]);
    const workspace = index.workspaces.find((w) => w.id === wsId) || null;
    return { workspace, tickets: board.tickets };
  }

  // ----------------------------------------------------------------- tickets

  /* A new ticket goes to the bottom of pending. Serialized so two submits from
     this tab pick different slots; a writer outside the tab could still pick
     the same one, which is harmless — `sort_order` only orders a column, and
     byPriority breaks ties on created_at.
     `settings` carries the new-request choices: {llm_profile, max_budget}.
     A null profile is "manager's choice" — the manager keeps picking. */
  async createTicket(wsId, body, settings = {}) {
    const text = (body || "").trim();
    if (!text) throw new Error("empty ticket body");
    const budget = Number(settings.max_budget ?? DEFAULT_BUDGET);
    if (!(budget > 0)) throw new Error("max_budget must be positive");
    return this.serialize(() => this.createTicketNow(wsId, text, {
      llm_profile: settings.llm_profile || null,
      max_budget: budget,
    }));
  }

  async createTicketNow(wsId, text, settings) {
    const now = nowTs();
    const board = await this.readBoard(wsId);
    const maxOrder = board.tickets
      .filter((t) => t.status === "pending")
      .reduce((max, t) => Math.max(max, t.sort_order || 0), 0);
    return this.putNewTicket(wsId, {
      id: newId(),
      status: "pending",
      title: null,
      sort_order: maxOrder + 1,
      conversation_id: null,
      pr_url: null,
      manager_note: null,
      dispatched_entry_count: 0,
      llm_profile: settings.llm_profile,
      max_budget: settings.max_budget,
      created_at: now,
      updated_at: now,
      finished_at: null,
      verified_at: null,
      entries: [{ id: newId(), author: "user", body: text, created_at: now }],
      attachments: [],
    });
  }

  async appendEntry(wsId, ticketId, body, author = "user") {
    const text = (body || "").trim();
    if (!text) throw new Error("empty entry body");
    const now = nowTs();
    /* Read the pending tail BEFORE entering the serialized mutation: reopening
       needs it, and `mutateTicket` serializes, so reading inside would
       deadlock on our own queue. */
    const board = await this.readBoard(wsId);
    const maxOrder = board.tickets
      .filter((t) => t.status === "pending")
      .reduce((max, t) => Math.max(max, t.sort_order || 0), 0);
    return this.mutateTicket(wsId, ticketId, (ticket) => {
      ticket.entries.push({ id: newId(), author, body: text, created_at: now });
      ticket.updated_at = now;
      // A new user request reopens a finished/needs_input ticket immediately
      // (bottom of pending) instead of waiting for the manager cycle.
      // in_progress is left alone (a worker is running); verified is terminal.
      if (author === "user" && (ticket.status === "finished" || ticket.status === "needs_input")) {
        ticket.status = "pending";
        ticket.sort_order = maxOrder + 1;
      }
      return ticket;
    });
  }

  async verifyTicket(wsId, ticketId) {
    const now = nowTs();
    return this.mutateTicket(wsId, ticketId, (ticket) => {
      ticket.status = VERIFIED;
      ticket.verified_at = now;
      ticket.updated_at = now;
      return ticket;
    });
  }

  /* Reordering writes one file per moved card. Only tickets whose sort_order
     actually changed are written, so dragging within a column does not rewrite
     the whole board and cannot clobber a concurrent edit to a card that
     happened to sit in it. */
  async reorder(wsId, status, orderedIds) {
    if (!STATUSES.includes(status)) throw new Error("bad status");
    const board = await this.readBoard(wsId);
    const current = new Map(board.tickets.map((t) => [t.id, t]));
    const moved = orderedIds
      .map((id, idx) => ({ id, idx, ticket: current.get(id) }))
      .filter(({ idx, ticket }) =>
        ticket && ticket.status === status && (ticket.sort_order || 0) !== idx);
    for (const { id, idx } of moved) {
      await this.mutateTicket(wsId, id, (ticket) => { ticket.sort_order = idx; });
    }
  }

  // ------------------------------------------------------------- attachments

  async addAttachment(wsId, ticketId, file) {
    const attId = newId();
    const filename = safeFilename(file.name);
    const path = await this.attachmentPath(attId, filename);
    await this.writeFile(path, file, filename);
    return this.mutateTicket(wsId, ticketId, (ticket) => {
      const attachment = {
        id: attId,
        filename,
        content_type: file.type || "application/octet-stream",
        size: file.size,
        created_at: nowTs(),
        path,
      };
      ticket.attachments.push(attachment);
      return attachment;
    });
  }

  /* An <img src> cannot send the session key, so attachment bytes are fetched
     through the authenticated client and handed to the DOM as a blob URL.

     The host client parses octet-stream bodies as text, which would corrupt
     binary image data, so this goes through `fetchBlob` instead of `request`. */
  async attachmentUrl(attachment) {
    const blob = await this.fetchBlob(attachment.path, attachment.content_type);
    return URL.createObjectURL(blob);
  }
}

export function isNotFound(err) {
  const status = err?.status ?? err?.response?.status;
  if (status === 404) return true;
  return /\b404\b|not found/i.test(err?.message || "");
}
