/* Tests run against the BUILT bundle (dist/extension.js), not the sources, so
   they also cover the build: CSS scoping, the rem rescale, and the absence of
   bare imports are all properties of the artifact Canvas actually loads.

   Run: npm test  (after npm run build)
*/

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { after, before, describe, it } from "node:test";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseHTML } from "linkedom";

const here = dirname(fileURLToPath(import.meta.url));
const MANIFEST = JSON.parse(
  readFileSync(join(here, "..", "canvas-extension.json"), "utf8"),
);
// The bundle is wherever the manifest says the entrypoint is.
const DIST = join(here, "..", MANIFEST.entrypoint);

/* linkedom gives us a DOM without a browser. The bundle reads these as
   globals at module scope, so they must exist before it is imported. */
function installDom() {
  const { window, document } = parseHTML(
    "<!doctype html><html><head></head><body></body></html>",
  );
  const store = new Map();
  const localStorage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
  };
  /* linkedom exposes HTMLSelectElement.value as a getter only; real browsers
     have a setter that selects the matching <option>. The extension assigns
     select.value (as any DOM code would), so add the missing setter rather
     than contort the extension to suit the test double. */
  const selectValue = Object.getOwnPropertyDescriptor(
    window.HTMLSelectElement.prototype,
    "value",
  );
  if (selectValue && !selectValue.set) {
    Object.defineProperty(window.HTMLSelectElement.prototype, "value", {
      get: selectValue.get,
      set(next) {
        for (const option of this.querySelectorAll("option")) {
          if (option.getAttribute("value") === next) option.setAttribute("selected", "");
          else option.removeAttribute("selected");
        }
      },
      configurable: true,
    });
  }

  globalThis.window = window;
  globalThis.document = document;
  globalThis.localStorage = localStorage;
  globalThis.HTMLElement = window.HTMLElement;
  if (!window.location) window.location = { pathname: "/" };
  return { window, document, store };
}

const dom = installDom();
const { activate, mountBoard } = await import(`file://${DIST}`);

/** Minimal host double matching the v1 ABI. */
function makeHost(overrides = {}) {
  const registered = [];
  return {
    apiVersion: "1",
    extension: { name: "kanban-manager", version: "0.1.0", resolvedRef: "test" },
    backend: { id: "test-backend", kind: "local", orgId: null },
    registerPage(id, mount) {
      registered.push({ id, mount });
      return () => registered.splice(0, registered.length);
    },
    navigate() {},
    agentServer: { request: async () => ({}) },
    registered,
    ...overrides,
  };
}

/* The board reaches the agent server only through host.agentServer.request,
   so a host whose request() is programmable is the whole seam. Returns the
   host plus the recorded calls. */
/* Reads use a cache-busting `_` param, so pull `path` out of the query
   properly rather than splitting on "path=". */
function filePath(url) {
  return new URL(url, "http://x").searchParams.get("path") || "";
}

function hostWithStore({
  home = "/home/tester",
  files = {},
  workspaces = {},
  /* What /api/file/search_subdirs reports under every workspace parent. */
  subdirs = [],
  /* Automation backend doubles, keyed by id. `null` for an id the backend
     doesn't have, which is how a deleted automation looks. */
  automations = {},
  /* Agent-server conversation metadata keyed by id, each optionally carrying
     `events` for the action-summary search. An id that isn't here 404s, which
     is how a deleted conversation looks. */
  conversations = {},
  createdAutomationId = "auto-created",
  /* Metadata (and seeded `events`) the agent server answers with for a
     conversation created through POST /api/conversations — the manager chat. */
  createdConversationId = "conv-created",
  createdConversation = null,
  /* Awaited before a download is served, so a test can hold a read open and
     make a response land after something else happened. */
  beforeRead = null,
  /* The same, for a directory listing — the read the board is assembled from. */
  beforeList = null,
  /* The agent server's LLM profiles, which fill the request-settings picker. */
  profiles = { profiles: [], active_profile: null },
} = {}) {
  const calls = [];
  const disk = new Map(Object.entries(files));
  const host = makeHost({
    agentServer: {
      async request({ path, method = "GET", body } = {}) {
        calls.push({ path, method, body });
        if (path === "/api/file/home") return { home };
        if (path === "/api/profiles") return profiles;
        if (path === "/api/workspaces") return workspaces;
        if (path.startsWith("/api/automation/v1")) {
          const rest = path.slice("/api/automation/v1".length);
          if (method === "POST" && rest === "") return { id: createdAutomationId };
          if (rest.startsWith("?")) return { automations: [] };
          const id = rest.split("/")[1]?.split("?")[0];
          if (method === "PATCH") {
            if (automations[id]) Object.assign(automations[id], body);
            return automations[id] || {};
          }
          if (rest.endsWith("/runs?limit=10")) return { runs: [] };
          if (!automations[id]) {
            const err = new Error("404 not found");
            err.status = 404;
            throw err;
          }
          return automations[id];
        }
        if (path === "/api/conversations" && method === "POST") {
          conversations[createdConversationId] = createdConversation || {
            id: createdConversationId, execution_status: "running", events: [],
          };
          return { id: createdConversationId };
        }
        if (path.startsWith("/api/conversations/")) {
          const rest = path.slice("/api/conversations/".length);
          const meta = conversations[rest.split(/[?/]/)[0]];
          if (!meta) {
            const err = new Error("404 not found");
            err.status = 404;
            throw err;
          }
          if (rest.includes("/events/search")) return { items: meta.events || [] };
          if (rest.endsWith("/events") && method === "POST") {
            // A user message becomes an event on the conversation, which is
            // how the chat window gets it back.
            meta.events = [...(meta.events || []), {
              id: `ev-${(meta.events || []).length + 1}`,
              kind: "MessageEvent",
              source: "user",
              timestamp: new Date(Date.now() + 1000).toISOString(),
              llm_message: {
                role: body?.role,
                content: (body?.content || []).map((c) => ({ type: "text", ...c })),
              },
            }];
            return {};
          }
          return meta;
        }
        if (path.startsWith("/api/file/download")) {
          const target = filePath(path);
          if (!disk.has(target)) {
            const err = new Error(`404 not found: ${target}`);
            err.status = 404;
            throw err;
          }
          /* A real response carries the bytes as they were when it was
             served, so snapshot before yielding: a caller must not see a
             later write through the object it read, and a held read must
             answer with what the file said when it was requested. */
          const served = structuredClone(disk.get(target));
          if (beforeRead) await beforeRead(target);
          return served;
        }
        if (path.startsWith("/api/file/search_subdirs")) {
          // Outside the store this listing is the workspace picker walking the
          // agent server's workspace parents.
          if (!filePath(path).startsWith(`${home}/.openhands/vibe-manager`)) {
            return { items: subdirs };
          }
          // Tickets are enumerated by listing directories, so the fake disk
          // has to derive the immediate child dirs of `path` from its keys.
          const dir = `${filePath(path)}/`;
          const names = new Set();
          for (const key of disk.keys()) {
            if (!key.startsWith(dir)) continue;
            const rest = key.slice(dir.length);
            if (rest.includes("/")) names.add(rest.split("/")[0]);
          }
          if (!names.size && ![...disk.keys()].some((k) => k.startsWith(dir))) {
            const err = new Error(`404 not found: ${dir}`);
            err.status = 404;
            throw err;
          }
          const items = [...names].map((name) => ({ name }));
          if (beforeList) await beforeList(filePath(path));
          return { items, next_page_id: null };
        }
        if (path.startsWith("/api/file/create_directory")) return {};
        if (path.startsWith("/api/file/upload")) {
          /* The real endpoint takes multipart and stores the file's bytes, so
             unwrap the FormData the store sends and keep parsed JSON on the
             fake disk (which is what download hands back). */
          const target = filePath(path);
          const file = body instanceof FormData ? body.get("file") : null;
          disk.set(target, file ? JSON.parse(await file.text()) : body);
          return {};
        }
        return {};
      },
    },
  });
  return { host, calls, disk };
}

function makeContainer() {
  const el = dom.document.createElement("div");
  dom.document.body.appendChild(el);
  return el;
}

describe("activate", () => {
  it("registers exactly the pages declared in the manifest", () => {
    const host = makeHost();
    activate(host);
    assert.equal(host.registered.length, 1);
    assert.deepEqual(
      host.registered.map((r) => r.id),
      MANIFEST.contributes.pages.map((p) => p.id),
    );
  });

  it("returns the unregister function so Canvas can dispose activation", () => {
    const unregister = () => {};
    const host = makeHost({ registerPage: () => unregister });
    assert.equal(activate(host), unregister);
  });

  it("fails clearly on an unsupported host API version", () => {
    const host = makeHost({ apiVersion: "2" });
    assert.throws(() => activate(host), /requires Canvas host API 1/);
  });
});

describe("mount", () => {
  it("needs no configuration: opens the store on the connected backend", async () => {
    dom.store.clear();
    const { host, calls } = hostWithStore();
    const container = makeContainer();
    const dispose = mountBoard({ container, path: "", navigate: () => {}, host });

    await waitFor(() => calls.some((c) => c.path === "/api/workspaces"));

    assert.equal(calls[0].path, "/api/file/home", "resolves the store root first");
    assert.equal(
      container.querySelector("#api-setup").hasAttribute("hidden"),
      true,
      "no setup screen: there is nothing to configure",
    );
    dispose();
  });

  it("reads the board out of the agent server filesystem", async () => {
    dom.store.clear();
    const workspace = { id: "w1", name: "demo", path: "/git/demo", max_concurrent: 2 };
    const home = "/home/tester";
    const root = `${home}/.openhands/vibe-manager`;
    const { host, calls } = hostWithStore({
      home,
      files: {
        [`${root}/index.json`]: { workspaces: [workspace] },
        [`${root}/workspaces/w1/tickets/t1/ticket.json`]: {
          id: "t1",
          status: "pending",
          entries: [{ id: "e1", author: "user", body: "hello", created_at: 1 }],
        },
      },
    });

    const container = makeContainer();
    const dispose = mountBoard({ container, path: "demo", navigate: () => {}, host });

    await waitFor(() => container.textContent.includes("hello"));
    assert.ok(
      calls.some((c) => c.path.includes(
        encodeURIComponent(`${root}/workspaces/w1/tickets/t1/ticket.json`))),
      "ticket read from the store path under the resolved home",
    );
    dispose();
  });

  it("renders all five lanes", async () => {
    dom.store.clear();
    const { host } = hostWithStore();
    const container = makeContainer();
    const dispose = mountBoard({ container, path: "", navigate: () => {}, host });
    await waitFor(() => container.querySelector("#empty-state"));
    assert.equal(container.querySelectorAll(".col").length, 5);
    dispose();
  });

  it("surfaces an unreachable agent server instead of failing silently", async () => {
    dom.store.clear();
    const host = makeHost({
      agentServer: {
        request: async () => {
          throw new Error("502 Bad Gateway");
        },
      },
    });
    const container = makeContainer();
    const dispose = mountBoard({ container, path: "", navigate: () => {}, host });

    await waitFor(() => {
      const err = container.querySelector("#api-setup-error");
      return err && !err.hasAttribute("hidden");
    });
    assert.match(
      container.querySelector("#api-setup-error").textContent,
      /Couldn't reach the agent server/,
    );
    dispose();
  });

  it("tolerates a malformed board file without throwing", async () => {
    dom.store.clear();
    const home = "/home/tester";
    const root = `${home}/.openhands/vibe-manager`;
    const { host } = hostWithStore({
      home,
      files: { [`${root}/index.json`]: { nonsense: true } },
    });
    const container = makeContainer();
    const dispose = mountBoard({ container, path: "", navigate: () => {}, host });
    await waitFor(() => container.querySelector("#workspace-select"));
    dispose();
  });

  it("disposer removes all DOM and stops polling", async () => {
    dom.store.clear();
    const { host, calls } = hostWithStore();
    const container = makeContainer();
    const dispose = mountBoard({ container, path: "", navigate: () => {}, host });
    await waitFor(() => calls.length > 0);

    dispose();
    assert.equal(container.childElementCount, 0, "container emptied");

    const afterDispose = calls.length;
    await sleep(60);
    assert.equal(calls.length, afterDispose, "no further requests after dispose");
  });

  it("removes its stylesheet only when the last mount is disposed", () => {
    dom.store.clear();
    const a = makeContainer();
    const b = makeContainer();
    const disposeA = mountBoard({
      container: a, path: "", navigate: () => {}, host: hostWithStore().host,
    });
    const disposeB = mountBoard({
      container: b, path: "", navigate: () => {}, host: hostWithStore().host,
    });

    assert.ok(dom.document.getElementById("vibe-ext-style"), "style injected");
    disposeA();
    assert.ok(
      dom.document.getElementById("vibe-ext-style"),
      "style survives while a mount remains",
    );
    disposeB();
    assert.equal(
      dom.document.getElementById("vibe-ext-style"),
      null,
      "style removed with the last mount",
    );
  });

  it("scopes the light theme to its own root, never the host document", () => {
    dom.store.clear();
    dom.store.set("vibe.theme", "light");
    const container = makeContainer();
    const dispose = mountBoard({
      container,
      path: "",
      navigate: () => {},
      host: hostWithStore().host,
    });
    const root = container.querySelector(".vibe-ext");
    assert.equal(root.getAttribute("data-theme"), "light");
    assert.equal(
      dom.document.documentElement.getAttribute("data-theme"),
      null,
      "host <html> untouched",
    );
    dispose();
  });

  /* The primary colour is a per-workspace field on index.json, and the theme
     is derived from it in CSS — so the whole feature is "the root carries the
     workspace's accent, and picking one writes it back". */
  it("themes the board with the workspace's primary colour", async () => {
    dom.store.clear();
    const home = "/home/tester";
    const root = `${home}/.openhands/vibe-manager`;
    const indexPath = `${root}/index.json`;
    const workspace = {
      id: "w1",
      name: "demo",
      path: "/git/demo",
      max_concurrent: 2,
      accent: "teal",
    };
    const { host, disk } = hostWithStore({
      home,
      files: {
        [indexPath]: { workspaces: [workspace] },
        [`${root}/workspaces/w1/board.json`]: { tickets: [] },
      },
    });

    const container = makeContainer();
    const dispose = mountBoard({ container, path: "demo", navigate: () => {}, host });
    const extRoot = container.querySelector(".vibe-ext");

    await waitFor(() => extRoot.getAttribute("data-accent") === "teal");
    assert.equal(
      container.querySelectorAll(".accent-swatch").length,
      10,
      "ten primaries to choose from",
    );
    assert.equal(
      container
        .querySelector('.accent-swatch[data-accent="teal"]')
        .getAttribute("aria-checked"),
      "true",
    );
    assert.equal(
      dom.document.documentElement.getAttribute("data-accent"),
      null,
      "host <html> untouched",
    );

    container.querySelector('.accent-swatch[data-accent="rose"]').dispatchEvent(
      new dom.window.Event("click", { bubbles: true }),
    );
    await waitFor(() => disk.get(indexPath)?.workspaces[0].accent === "rose");
    await waitFor(() => extRoot.getAttribute("data-accent") === "rose");
    dispose();
  });

  /* Preferences are workspace settings in the store, not browser state: the
     board adopts the record's theme and writes a toggle straight back to it. */
  it("takes the theme and the verified toggle from the workspace record", async () => {
    dom.store.clear();
    const home = "/home/tester";
    const root = `${home}/.openhands/vibe-manager`;
    const indexPath = `${root}/index.json`;
    const workspace = {
      id: "w1",
      name: "demo",
      path: "/git/demo",
      max_concurrent: 2,
      theme: "light",
      show_verified: false,
    };
    const { host, disk } = hostWithStore({
      home,
      files: {
        [indexPath]: { workspaces: [workspace] },
        [`${root}/workspaces/w1/board.json`]: { tickets: [] },
      },
    });

    const container = makeContainer();
    const dispose = mountBoard({ container, path: "demo", navigate: () => {}, host });
    const extRoot = container.querySelector(".vibe-ext");
    await waitFor(() => extRoot.getAttribute("data-theme") === "light");

    const toggle = container.querySelector("#show-verified");
    assert.equal(
      toggle.closest(".col").dataset.status,
      "finished",
      "the switch rides the Finished column's header, beside the lane it reveals",
    );
    assert.equal(toggle.textContent.trim(), "", "an icon, not a label");
    assert.equal(toggle.getAttribute("aria-label"), "Show verified");

    toggle.dispatchEvent(new dom.window.Event("click", { bubbles: true }));
    await waitFor(() => disk.get(indexPath)?.workspaces[0].show_verified === true);
    assert.equal(toggle.getAttribute("aria-pressed"), "true");
    assert.equal(toggle.getAttribute("aria-label"), "Hide verified");
    assert.ok(toggle.classList.contains("active"), "on state is visible, not just spoken");
    dispose();
  });

  /* The control is deliberately unlabelled and sits with the workspace it
     belongs to, so its identity is "the dot beside the workspace picker". */
  it("puts the primary-colour picker beside the workspace picker, as a bare dot", async () => {
    dom.store.clear();
    const container = makeContainer();
    const dispose = mountBoard({
      container,
      path: "",
      navigate: () => {},
      host: hostWithStore().host,
    });

    const picker = container.querySelector(".control-workspace");
    assert.equal(picker.nextElementSibling.id, "ctl-accent");
    const toggle = container.querySelector("#accent-toggle");
    assert.equal(toggle.textContent.trim(), "", "no text label, just the dot");
    assert.ok(toggle.querySelector(".accent-dot"));
    assert.equal(toggle.getAttribute("aria-label"), "Primary colour");
    dispose();
  });

  it("falls back to the default primary for a workspace without one", async () => {
    dom.store.clear();
    const home = "/home/tester";
    const root = `${home}/.openhands/vibe-manager`;
    const { host } = hostWithStore({
      home,
      files: {
        [`${root}/index.json`]: {
          workspaces: [{ id: "w1", name: "demo", path: "/git/demo", max_concurrent: 2 }],
        },
        [`${root}/workspaces/w1/board.json`]: { tickets: [] },
      },
    });

    const container = makeContainer();
    const dispose = mountBoard({ container, path: "demo", navigate: () => {}, host });
    await waitFor(
      () => container.querySelector(".vibe-ext").getAttribute("data-accent") === "ember",
    );
    dispose();
  });

  it("treats the route remainder as the workspace name", async () => {
    dom.store.clear();
    const home = "/home/tester";
    const root = `${home}/.openhands/vibe-manager`;
    const workspace = {
      id: "w1",
      name: "demo",
      path: "/git/demo",
      max_concurrent: 3,
      push_mode: "main",
    };
    const { host, calls } = hostWithStore({
      home,
      files: {
        [`${root}/index.json`]: { workspaces: [workspace] },
        [`${root}/workspaces/w1/tickets/`]: {},
      },
    });

    const container = makeContainer();
    const dispose = mountBoard({ container, path: "demo", navigate: () => {}, host });

    // Resolving the name to w1 and listing its tickets is the whole behaviour.
    await waitFor(() =>
      calls.some((c) => c.path.startsWith("/api/file/search_subdirs")
        && c.path.includes(encodeURIComponent(`${root}/workspaces/w1/tickets`))),
    );
    dispose();
  });

  /* Submitting is the one path that writes. It regressed silently once
     (the composer passed {body} where the store wanted a string), so these
     assert the ticket actually lands in the store, not just that a handler
     ran. */
  describe("submitting a new request", () => {
    const home = "/home/tester";
    const root = `${home}/.openhands/vibe-manager`;
    const ticketsDir = `${root}/workspaces/w1/tickets`;
    const workspace = { id: "w1", name: "demo", path: "/git/demo", max_concurrent: 2 };

    async function mountWithComposer(opts = {}) {
      dom.store.clear();
      const ctx = hostWithStore({
        home,
        files: {
          [`${root}/index.json`]: { workspaces: [workspace] },
          [`${ticketsDir}/`]: {},
        },
        ...opts,
      });
      const container = makeContainer();
      const dispose = mountBoard({ container, path: "demo", navigate: () => {}, host: ctx.host });
      /* The composer is in the initial markup, so waiting for it would race
         the workspace lookup and submit into a board that isn't open yet. */
      await waitFor(() =>
        ctx.calls.some((c) => c.path.startsWith("/api/file/search_subdirs")
          && c.path.includes(encodeURIComponent(ticketsDir))),
      );
      return { ...ctx, container, dispose };
    }

    // Tickets are separate files now, so collect them off the fake disk.
    const written = (disk) => [...disk.entries()]
      .filter(([k]) => k.startsWith(`${ticketsDir}/`) && k.endsWith("/ticket.json"))
      .map(([, v]) => v);

    /* linkedom has no KeyboardEvent constructor, so carry the fields the
       handler actually reads on a plain Event. */
    function keydown(key, props = {}) {
      const e = new dom.window.Event("keydown", { bubbles: true, cancelable: true });
      Object.assign(e, { key, shiftKey: false, metaKey: false, ctrlKey: false, ...props });
      return e;
    }

    it("creates the ticket when the form is submitted", async () => {
      const { container, disk, dispose } = await mountWithComposer();
      container.querySelector("#new-ticket-body").value = "ship it";
      container.querySelector("#new-ticket-form").dispatchEvent(
        new dom.window.Event("submit", { bubbles: true, cancelable: true }),
      );

      await waitFor(() => written(disk).length === 1);
      const [ticket] = written(disk);
      assert.equal(ticket.status, "pending");
      assert.equal(ticket.entries[0].body, "ship it", "body survives the round trip");
      assert.equal(ticket.entries[0].author, "user");
      assert.equal(ticket.llm_profile, null, "defaults to the manager's choice of model");
      assert.equal(ticket.max_budget, 10, "defaults to a $10 budget");
      dispose();
    });

    it("offers the agent server's profiles, manager's choice first", async () => {
      const { container, dispose } = await mountWithComposer({
        profiles: {
          profiles: [
            { name: "fable", model: "anthropic/claude-fable-5" },
            { name: "opus", model: "anthropic/claude-opus-5" },
          ],
          active_profile: "opus",
        },
      });
      const options = () => [...container.querySelectorAll("#settings-profile option")];
      await waitFor(() => options().length === 3);
      assert.deepEqual(
        options().map((o) => [o.getAttribute("value"), o.textContent]),
        [["", "Manager's choice"], ["fable", "fable"], ["opus", "opus (default)"]],
      );
      dispose();
    });

    it("stores the agent and budget on the workspace and uses them for tickets", async () => {
      const { container, disk, dispose } = await mountWithComposer({
        profiles: {
          profiles: [{ name: "opus", model: "anthropic/claude-opus-5" }],
          active_profile: "opus",
        },
      });
      const menu = container.querySelector("#settings-menu");
      assert.equal(menu.hasAttribute("hidden"), true, "settings start collapsed");
      container.querySelector("#settings-toggle").dispatchEvent(
        new dom.window.Event("click", { bubbles: true }),
      );
      assert.equal(menu.hasAttribute("hidden"), false, "the ⚙ button reveals them");
      assert.ok(
        container.querySelector("#settings-menu #push-mode"),
        "where changes land lives in the settings popover",
      );

      await waitFor(
        () => container.querySelectorAll("#settings-profile option").length === 2,
      );
      const profile = container.querySelector("#settings-profile");
      profile.value = "opus";
      profile.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
      const budget = container.querySelector("#settings-budget");
      budget.value = "25";
      budget.dispatchEvent(new dom.window.Event("change", { bubbles: true }));

      // The settings are the workspace's, not the form's: they land in the store.
      const indexPath = `${root}/index.json`;
      await waitFor(() => disk.get(indexPath)?.workspaces[0].llm_profile === "opus");
      await waitFor(() => disk.get(indexPath)?.workspaces[0].max_budget === 25);

      container.querySelector("#new-ticket-body").value = "spare no expense";
      container.querySelector("#new-ticket-form").dispatchEvent(
        new dom.window.Event("submit", { bubbles: true, cancelable: true }),
      );

      await waitFor(() => written(disk).length === 1);
      const [ticket] = written(disk);
      assert.equal(ticket.llm_profile, "opus");
      assert.equal(ticket.max_budget, 25);
      dispose();
    });

    it("creates the ticket when Enter is pressed in the composer", async () => {
      const { container, disk, dispose } = await mountWithComposer();
      const ta = container.querySelector("#new-ticket-body");
      ta.value = "via enter";
      ta.dispatchEvent(keydown("Enter"));

      await waitFor(() => written(disk).length === 1);
      assert.equal(written(disk)[0].entries[0].body, "via enter");
      dispose();
    });

    it("leaves Shift+Enter to insert a newline", async () => {
      const { container, disk, dispose } = await mountWithComposer();
      const ta = container.querySelector("#new-ticket-body");
      ta.value = "not yet";
      ta.dispatchEvent(keydown("Enter", { shiftKey: true }));

      await sleep(80);
      assert.equal(written(disk).length, 0, "no ticket written");
      dispose();
    });

    it("ignores an empty composer", async () => {
      const { container, disk, dispose } = await mountWithComposer();
      container.querySelector("#new-ticket-body").value = "   ";
      container.querySelector("#new-ticket-form").dispatchEvent(
        new dom.window.Event("submit", { bubbles: true, cancelable: true }),
      );

      await sleep(80);
      assert.equal(written(disk).length, 0, "whitespace is not a request");
      dispose();
    });

    /* The board is polled every 5s, so a read is usually in flight when the
       user submits. That response was captured before the ticket existed, and
       rendering it drops the brand new card out of pending until the next
       poll — the "cards don't always show up" report. */
    it("keeps the new card when a read from before it lands late", async () => {
      dom.store.clear();
      let release;
      const held = new Promise((resolve) => { release = resolve; });
      let boardReads = 0;
      const ctx = hostWithStore({
        home,
        files: {
          [`${root}/index.json`]: { workspaces: [workspace] },
          [`${ticketsDir}/`]: {},
        },
        // The board is now assembled from a listing, so that is the read to
        // hold open to reproduce a stale poll landing after a submit.
        beforeList: async (target) => {
          if (target === ticketsDir && ++boardReads === 1) await held;
        },
      });
      const container = makeContainer();
      const dispose = mountBoard({
        container, path: "demo", navigate: () => {}, host: ctx.host,
      });

      try {
        await waitFor(() => boardReads >= 1);
        container.querySelector("#new-ticket-body").value = "ship it";
        container.querySelector("#new-ticket-form").dispatchEvent(
          new dom.window.Event("submit", { bubbles: true, cancelable: true }),
        );

        const pending = () =>
          container.querySelector('.col-cards[data-status="pending"]').textContent;
        await waitFor(() => written(ctx.disk).length === 1);
        await waitFor(() => pending().includes("ship it"));

        release();
        await sleep(80);
        assert.match(pending(), /ship it/, "the card is still in pending");
      } finally {
        // Without this a failure leaves the poll timer holding the runner open.
        release();
        dispose();
      }
    });
  });
});

/* The manager control is the only part of the board that writes to the
   automation backend, and "no manager yet" is the state a fresh install is in
   — so these drive it end to end: the orange offer, the tarball upload, the
   created automation landing on the workspace, and stopping it again. */
describe("manager control", () => {
  const home = "/home/tester";
  const root = `${home}/.openhands/vibe-manager`;
  const indexPath = `${root}/index.json`;

  function workspace(extra = {}) {
    return {
      id: "w1",
      name: "demo",
      path: "/git/demo",
      max_concurrent: 2,
      push_mode: "main",
      automation_id: null,
      ...extra,
    };
  }

  /* The tarball upload is a raw fetch (the host client would JSON-stringify
     the gzip bytes), so the backend registry Canvas keeps in localStorage and
     `fetch` itself are part of the seam. */
  function stubUpload() {
    const uploads = [];
    dom.store.set(
      "openhands-backends",
      JSON.stringify([{ id: "test-backend", host: "https://canvas.example", apiKey: "k" }]),
    );
    const original = globalThis.fetch;
    globalThis.fetch = async (url, init) => {
      uploads.push({ url: String(url), init });
      return {
        ok: true,
        status: 201,
        json: async () => ({ tarball_path: "oh-internal://uploads/abc" }),
      };
    };
    return { uploads, restore: () => { globalThis.fetch = original; } };
  }

  async function mount(ws, options = {}) {
    dom.store.clear();
    const ctx = hostWithStore({
      home,
      files: {
        [indexPath]: { workspaces: [ws] },
        [`${root}/workspaces/w1/board.json`]: { version: 1, workspace_id: "w1", tickets: [] },
      },
      ...options,
    });
    const container = makeContainer();
    const dispose = mountBoard({ container, path: "demo", navigate: () => {}, host: ctx.host });
    await waitFor(() => !container.querySelector("#mgr-badge").hasAttribute("hidden"));
    return { ...ctx, container, dispose };
  }

  const badgeText = (container) => container.querySelector("#mgr-text").textContent;

  it("offers to start a manager when the workspace has none", async () => {
    const { container, dispose } = await mount(workspace());
    const badge = container.querySelector("#mgr-badge");
    assert.equal(badgeText(container), "Start manager");
    assert.ok(badge.classList.contains("start"), "orange start state");
    assert.equal(
      container.querySelector("#mgr-stop").hasAttribute("hidden"),
      true,
      "nothing to stop yet",
    );
    dispose();
  });

  it("creates the automation and records it on the workspace", async () => {
    const { container, calls, disk, dispose } = await mount(workspace(), {
      createdAutomationId: "auto-9",
    });
    // After the mount: it clears localStorage, where the backend registry lives.
    const upload = stubUpload();
    try {
      container.querySelector("#mgr-badge").dispatchEvent(
        new dom.window.Event("click", { bubbles: true }),
      );
      await waitFor(() => disk.get(indexPath).workspaces[0].automation_id === "auto-9");

      assert.equal(upload.uploads.length, 1, "tarball uploaded once");
      const [{ url, init }] = upload.uploads;
      assert.match(url, /^https:\/\/canvas\.example\/api\/automation\/v1\/uploads\?/);
      assert.equal(init.headers["Content-Type"], "application/gzip");
      assert.ok(init.body instanceof Blob, "the gzip bytes go up as a blob");

      const created = calls.find((c) => c.method === "POST" && c.path === "/api/automation/v1");
      assert.ok(created, "automation created");
      assert.equal(created.body.trigger.schedule, "* * * * *");
      assert.equal(created.body.entrypoint, "python3 main.py");
      assert.equal(created.body.tarball_path, "oh-internal://uploads/abc");
      assert.match(created.body.name, /demo \(w1\)/, "app.py's naming, so it is not duplicated");
    } finally {
      upload.restore();
      dispose();
    }
  });

  it("shows the running manager with a way to stop it", async () => {
    const { container, dispose } = await mount(workspace({ automation_id: "auto-1" }), {
      automations: { "auto-1": { id: "auto-1", enabled: true } },
    });
    await waitFor(() => !container.querySelector("#mgr-stop").hasAttribute("hidden"));
    assert.equal(container.querySelector("#mgr-badge").classList.contains("start"), false);
    dispose();
  });

  /* Status and start/stop are one control, not two things that happen to sit
     next to each other. */
  it("keeps the status and the stop button in one group", async () => {
    const { container, dispose } = await mount(workspace({ automation_id: "auto-1" }), {
      automations: { "auto-1": { id: "auto-1", enabled: true } },
    });
    await waitFor(() => !container.querySelector("#mgr-stop").hasAttribute("hidden"));
    const group = container.querySelector("#mgr-group");
    assert.equal(container.querySelector("#mgr-badge").parentElement, group);
    assert.equal(container.querySelector("#mgr-stop").parentElement, group);
    assert.equal(group.getAttribute("role"), "group");
    dispose();
  });

  it("stopping disables the automation and offers to start it again", async () => {
    const automations = { "auto-1": { id: "auto-1", enabled: true } };
    const { container, calls, dispose } = await mount(
      workspace({ automation_id: "auto-1" }),
      { automations },
    );
    await waitFor(() => !container.querySelector("#mgr-stop").hasAttribute("hidden"));
    container.querySelector("#mgr-stop").dispatchEvent(
      new dom.window.Event("click", { bubbles: true }),
    );

    await waitFor(() => badgeText(container) === "Start manager");
    const patch = calls.find((c) => c.method === "PATCH" && c.path === "/api/automation/v1/auto-1");
    assert.deepEqual(patch.body, { enabled: false });
    assert.equal(automations["auto-1"].enabled, false, "the automation is kept, disabled");
    assert.equal(container.querySelector("#mgr-stop").hasAttribute("hidden"), true);
    dispose();
  });

  it("offers a start when the workspace points at an automation that is gone", async () => {
    const { container, dispose } = await mount(workspace({ automation_id: "auto-gone" }), {
      automations: {},
    });
    await waitFor(() => badgeText(container) === "Start manager");
    dispose();
  });
});

describe("workspace picker", () => {
  /* The store reports a candidate as {path, name} only, so the old
     `${name}${is_git ? "" : " (not git)"}` label tagged every available
     workspace as "not git". Names, nothing else. */
  it("lists candidate workspaces by name alone", async () => {
    dom.store.clear();
    const { host } = hostWithStore({
      workspaces: { workspaceParents: [{ path: "/git" }] },
      subdirs: [{ path: "/git/demo", name: "demo" }],
    });
    const container = makeContainer();
    const dispose = mountBoard({ container, path: "", navigate: () => {}, host });
    await waitFor(() =>
      [...container.querySelectorAll("#workspace-select option")].some(
        (o) => o.getAttribute("value") === "/git/demo",
      ),
    );
    const option = [...container.querySelectorAll("#workspace-select option")].find(
      (o) => o.getAttribute("value") === "/git/demo",
    );
    assert.equal(option.textContent, "demo");
    dispose();
  });

  it("links unfinished projects with their own colours and visible tooltips", async () => {
    dom.store.clear();
    const home = "/home/tester";
    const root = `${home}/.openhands/vibe-manager`;
    const workspaces = [
      {
        id: "w-alpha", name: "Alpha", path: "/git/alpha",
        max_concurrent: 2, accent: "jade",
      },
      {
        id: "w-beta", name: "Beta", path: "/git/beta",
        max_concurrent: 2, accent: "azure",
      },
      {
        id: "w-done", name: "Done", path: "/git/done",
        max_concurrent: 2, accent: "slate",
      },
    ];
    const ticket = (id, status) => ({
      id, status, entries: [{ id: `e-${id}`, author: "user", body: id, created_at: 1 }],
    });
    const files = {
      [`${root}/index.json`]: { workspaces },
      [`${root}/workspaces/w-alpha/board.json`]: {
        tickets: [ticket("pending", "pending"), ticket("working", "in_progress"),
          ticket("finished", "finished")],
      },
      [`${root}/workspaces/w-beta/board.json`]: {
        tickets: [ticket("waiting", "needs_input"), ticket("verified", "verified")],
      },
      [`${root}/workspaces/w-done/board.json`]: {
        tickets: [ticket("done", "finished"), ticket("checked", "verified")],
      },
    };
    const { host } = hostWithStore({ home, files });
    const navigated = [];
    const container = makeContainer();
    const dispose = mountBoard({
      container, path: "Alpha", navigate: (target) => navigated.push(target), host,
    });

    try {
      await waitFor(() => container.querySelectorAll(".workspace-indicator").length === 1);
      let indicator = container.querySelector(".workspace-indicator");
      assert.equal(indicator.dataset.path, "/git/beta", "the active Alpha badge is hidden");
      assert.equal(indicator.dataset.accent, "azure", "Beta uses its own primary colour");
      assert.equal(indicator.textContent, "1");
      assert.equal(indicator.hasAttribute("title"), false, "native title tooltips are not used");
      assert.equal(indicator.getAttribute("aria-label"), "Beta: 1 unfinished card");
      const tooltip = indicator.parentElement.querySelector('[role="tooltip"]');
      assert.equal(tooltip.textContent, "Beta");
      assert.equal(indicator.getAttribute("aria-describedby"), tooltip.id);
      assert.equal(
        container.querySelector("#workspace-indicators").nextElementSibling.id,
        "workspace-select",
        "indicators sit immediately left of the project picker",
      );
      assert.match(
        document.getElementById("vibe-ext-style").textContent,
        /workspace-indicator-item:hover[^}]+workspace-indicator-tooltip/,
        "the rendered tooltip is exposed on hover",
      );

      indicator.dispatchEvent(new dom.window.Event("click", { bubbles: true }));
      await waitFor(() => navigated.includes("/extensions/kanban-manager/board/Beta"));
      assert.equal(container.querySelector("#workspace-select").value, "/git/beta");
      await waitFor(() =>
        container.querySelector('.workspace-indicator[data-path="/git/alpha"]') !== null,
      );
      indicator = container.querySelector(".workspace-indicator");
      assert.equal(indicator.dataset.path, "/git/alpha", "the new active Beta badge is hidden");
      assert.equal(indicator.dataset.accent, "jade", "Alpha keeps its own primary colour");
      assert.equal(indicator.textContent, "2");
      assert.equal(indicator.parentElement.querySelector('[role="tooltip"]').textContent, "Alpha");
    } finally {
      dispose();
    }
  });
});

describe("worker activity indicator", () => {
  function conversation(status, summary) {
    return {
      execution_status: status,
      agent: { llm: { model: "anthropic/claude-fable-5" } },
      events: [
        {
          tool_call: { name: "terminal", arguments: JSON.stringify({ summary }) },
          timestamp: "2026-08-29T19:37:00Z",
        },
      ],
    };
  }

  function ticket(id, convId) {
    return {
      id,
      status: "in_progress",
      conversation_id: convId,
      entries: [{ id: `e-${id}`, author: "user", body: "beat counter", created_at: 1 }],
    };
  }

  /* The pulsing dot means "this worker is still acting". It kept pulsing after
     the conversation ended, so a finished card claimed live telemetry. */
  it("pulses for a running worker and shows a checkmark once it ends", async () => {
    dom.store.clear();
    const home = "/home/tester";
    const root = `${home}/.openhands/vibe-manager`;
    const { host } = hostWithStore({
      home,
      files: {
        [`${root}/index.json`]: {
          workspaces: [{ id: "w1", name: "demo", path: "/git/demo", max_concurrent: 3 }],
        },
        [`${root}/workspaces/w1/board.json`]: {
          tickets: [
            ticket("t-run", "c-run"),
            ticket("t-done", "c-done"),
            ticket("t-err", "c-err"),
          ],
        },
      },
      conversations: {
        "c-run": conversation("running", "Editing the beat counter"),
        "c-done": conversation("finished", "Pushed beat/cycle divisor readout to main"),
        "c-err": conversation("error", "Pushed beat/cycle divisor readout to main"),
      },
    });

    const container = makeContainer();
    const dispose = mountBoard({ container, path: "demo", navigate: () => {}, host });
    const card = (id) => container.querySelector(`.card[data-id="${id}"]`);
    // dispose() in a finally: a failed assertion would otherwise leave the
    // poll timers running and the test runner would never exit.
    try {
      // Summaries and statuses are fetched in the background during the first
      // render, so they only reach the DOM on the next 5s board poll.
      await waitFor(() => card("t-done")?.querySelector(".card-activity"), 8000);

      assert.ok(card("t-run").classList.contains("live"), "running worker keeps the live rail");
      assert.ok(card("t-run").querySelector(".activity-dot"), "running worker pulses");
      assert.equal(card("t-run").querySelector(".activity-check"), null);

      for (const id of ["t-done", "t-err"]) {
        assert.equal(card(id).classList.contains("live"), false, `${id} drops the live rail`);
        assert.ok(card(id).querySelector(".card-activity.done"), `${id} marked done`);
        assert.equal(card(id).querySelector(".activity-dot"), null, `${id} stops pulsing`);
        assert.equal(card(id).querySelector(".activity-check").textContent, "✓");
      }
    } finally {
      dispose();
    }
  });
});

describe("budget and spend", () => {
  const home = "/home/tester";
  const root = `${home}/.openhands/vibe-manager`;

  function conversation(spends) {
    return {
      execution_status: "running",
      agent: { llm: { model: "anthropic/claude-fable-5" } },
      stats: {
        usage_to_metrics: Object.fromEntries(
          Object.entries(spends).map(([usage, cost]) => [usage, { accumulated_cost: cost }]),
        ),
      },
    };
  }

  function ticket(id, convId, maxBudget) {
    return {
      id,
      status: convId ? "in_progress" : "pending",
      conversation_id: convId,
      max_budget: maxBudget,
      entries: [{ id: `e-${id}`, author: "user", body: "spend wisely", created_at: 1 }],
    };
  }

  /* The card has to answer "what is this ticket allowed to spend, and what has
     it spent?" — the same total the poller pauses a worker at. */
  it("shows spend against the budget on every card", async () => {
    dom.store.clear();
    const { host } = hostWithStore({
      home,
      files: {
        [`${root}/index.json`]: {
          workspaces: [{ id: "w1", name: "demo", path: "/git/demo", max_concurrent: 3 }],
        },
        [`${root}/workspaces/w1/board.json`]: {
          tickets: [
            ticket("t-spend", "c-spend", 25),
            ticket("t-over", "c-over", 10),
            ticket("t-idle", null, 10),
          ],
        },
      },
      conversations: {
        // Two LLMs on one conversation: the chip shows their sum.
        "c-spend": conversation({ default: 4, condenser: 0.25 }),
        "c-over": conversation({ default: 12.5 }),
      },
    });

    const container = makeContainer();
    const dispose = mountBoard({ container, path: "demo", navigate: () => {}, host });
    const chip = (id) => container.querySelector(`.card[data-id="${id}"] .chip.budget`);
    try {
      // A ticket with no conversation has nothing to fetch: it reports $0.00
      // of its budget as soon as the board renders.
      await waitFor(() => chip("t-idle"));
      assert.equal(chip("t-idle").textContent, "$0.00 / $10.00");

      // The spends are fetched in the background, so they reach the DOM on the
      // next 5s board poll.
      await waitFor(() => chip("t-spend")?.textContent === "$4.25 / $25.00", 8000);
      assert.equal(
        chip("t-spend").getAttribute("title"),
        "spent $4.25 of the $25.00 budget",
      );
      assert.equal(chip("t-spend").classList.contains("over"), false);

      assert.equal(chip("t-over").textContent, "$12.50 / $10.00");
      assert.ok(chip("t-over").classList.contains("over"), "a ticket past its cap stands out");
      assert.equal(chip("t-idle").classList.contains("over"), false);
    } finally {
      dispose();
    }
  });
});

describe("talk to the manager", () => {
  const home = "/home/tester";
  const root = `${home}/.openhands/vibe-manager`;
  const boardPath = `${root}/workspaces/w1/board.json`;
  const workspace = {
    id: "w1", name: "demo", path: "/git/demo", max_concurrent: 2, push_mode: "main",
  };
  const skillTurn = {
    id: "e1", kind: "MessageEvent", source: "user", timestamp: "2026-05-21T10:00:00",
    llm_message: {
      role: "user",
      content: [{ type: "text", text: "<!-- vibe-manager-skill -->\nYou are the Vibe Manager…" }],
    },
  };
  const greeting = {
    id: "e2", kind: "MessageEvent", source: "agent", timestamp: "2026-05-21T10:00:05",
    llm_message: {
      role: "assistant",
      content: [{ type: "text", text: "3 queued, 1 agent working." }],
    },
  };

  /* The agent settings come back through a raw fetch, because they need an
     X-Expose-Secrets header the host client does not forward. */
  function stubSettings() {
    dom.store.set(
      "openhands-backends",
      JSON.stringify([{ id: "test-backend", host: "https://canvas.example", apiKey: "k" }]),
    );
    const original = globalThis.fetch;
    const calls = [];
    globalThis.fetch = async (url, init) => {
      calls.push({ url: String(url), init });
      return {
        ok: true,
        status: 200,
        json: async () => ({ agent_settings: { llm: { model: "m" }, tools: [] } }),
      };
    };
    return { calls, restore: () => { globalThis.fetch = original; } };
  }

  async function mount() {
    dom.store.clear();
    const ctx = hostWithStore({
      home,
      files: {
        [`${root}/index.json`]: { workspaces: [workspace] },
        [boardPath]: { version: 1, workspace_id: "w1", tickets: [] },
      },
      createdConversation: {
        id: "conv-created",
        execution_status: "running",
        events: [skillTurn, greeting],
      },
    });
    const container = makeContainer();
    const dispose = mountBoard({ container, path: "demo", navigate: () => {}, host: ctx.host });
    await waitFor(() => ctx.calls.some((c) => c.path.includes(encodeURIComponent(boardPath))));
    return { ...ctx, container, dispose };
  }

  const click = (el) => el.dispatchEvent(new dom.window.Event("click", { bubbles: true }));

  it("starts a conversation pre-loaded with the manager skill", async () => {
    const { container, calls, dispose } = await mount();
    const settings = stubSettings();
    try {
      click(container.querySelector("#manager-chat-open"));
      await waitFor(() =>
        calls.some((c) => c.path === "/api/conversations" && c.method === "POST"));
      const body = calls.find((c) => c.path === "/api/conversations" && c.method === "POST").body;

      // Same workspace association the manager's own conversations get.
      assert.deepEqual(body.workspace, { kind: "LocalWorkspace", working_dir: "/git/demo" });
      assert.equal(body.worktree, false);
      assert.deepEqual(body.tags, { workspace: "/git/demo", viberole: "manager_chat" });
      assert.equal(body.agent_settings.tools, null, "default exec toolset, not a bare agent");

      const skill = body.initial_message.content[0].text;
      assert.match(skill, /## Manager/, "records requests under a Manager section");
      assert.match(skill, /AGENTS\.md/);
      assert.ok(skill.includes(`${root}/bin/w1/vibectl.py`), "knows how to read the board");
      assert.match(skill, /execution_status/, "knows how to read the conversations");
      assert.ok(skill.includes("/git/demo"), "names the project");
    } finally {
      settings.restore();
      dispose();
    }
  });

  it("shows the conversation as a chat and sends what the user types", async () => {
    const { container, calls, dispose } = await mount();
    const settings = stubSettings();
    try {
      click(container.querySelector("#manager-chat-open"));
      assert.equal(container.querySelector("#manager-chat").hasAttribute("hidden"), false);

      // The seeded skill is not a chat turn: only the greeting shows.
      await waitFor(() => container.querySelectorAll("#manager-chat-log .chat-msg").length === 1);
      const first = container.querySelector("#manager-chat-log .chat-msg");
      assert.ok(first.classList.contains("assistant"));
      assert.equal(first.querySelector(".chat-msg-body").textContent, "3 queued, 1 agent working.");
      assert.equal(first.querySelector(".chat-msg-head").textContent, "manager");
      // A running manager pulses, like a live card.
      assert.ok(container.querySelector("#manager-chat-activity .activity-dot"));

      container.querySelector("#manager-chat-body").value = "prioritise the login bug";
      container.querySelector("#manager-chat-form").dispatchEvent(
        new dom.window.Event("submit", { bubbles: true, cancelable: true }),
      );
      await waitFor(() =>
        calls.some((c) => c.path === "/api/conversations/conv-created/events" && c.method === "POST"));
      const sent = calls.find(
        (c) => c.path === "/api/conversations/conv-created/events" && c.method === "POST").body;
      assert.equal(sent.content[0].text, "prioritise the login bug");
      assert.equal(sent.run, true);

      // It comes back from the conversation itself — no optimistic copy.
      await waitFor(() => container.querySelectorAll("#manager-chat-log .chat-msg.user").length === 1);
      assert.equal(
        container.querySelector(".chat-msg.user .chat-msg-body").textContent,
        "prioritise the login bug",
      );
      assert.equal(container.querySelector("#manager-chat-body").value, "");

      // Escape closes it and stops the poll.
      const escape = new dom.window.Event("keydown", { bubbles: true, cancelable: true });
      Object.assign(escape, { key: "Escape" });
      dom.document.dispatchEvent(escape);
      assert.equal(container.querySelector("#manager-chat").hasAttribute("hidden"), true);
    } finally {
      settings.restore();
      dispose();
    }
  });
});

describe("bundle", () => {
  const source = readFileSync(DIST, "utf8");

  it("is loadable as browser ESM with no bare or remote imports", () => {
    /* An import specifier lives on one line. The pattern must say so: the
       bundle also carries the automation's python sources, whose `import json`
       lines would otherwise pair up with a quote several lines later. */
    const bare = source.match(/^\s*import\s+[^"'\n]*["'][^./][^"'\n]*["']/gm) || [];
    assert.deepEqual(bare, [], "no bare imports");
    assert.equal(/from\s*["']https?:/.test(source), false, "no remote imports");
    assert.equal(/\brequire\(/.test(source), false, "no CJS require");
  });

  it("exports activate", () => {
    assert.match(source, /export\s*\{[\s\S]*?\bactivate\b/);
  });

  it("embeds the stylesheet with every selector scoped", () => {
    // Guards the build's scoping transform: a page-level selector escaping
    // into the bundle would restyle Canvas itself.
    assert.match(source, /\.vibe-ext \{ --vibe-rem/);
    assert.equal(
      /\n(html|body|:root)\s*[,{]/.test(source),
      false,
      "no unscoped page-level selectors",
    );
  });

  it("only registers page ids declared in the manifest", () => {
    const ids = MANIFEST.contributes.pages.map((p) => p.id);
    const registered = [...source.matchAll(/registerPage\(\s*"([^"]+)"/g)].map((m) => m[1]);
    assert.ok(registered.length > 0, "registerPage called with a literal id");
    for (const id of registered) {
      assert.ok(ids.includes(id), `${id} is declared in the manifest`);
    }
  });
});

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitFor(predicate, timeout = 2000) {
  const started = Date.now();
  for (;;) {
    if (predicate()) return;
    if (Date.now() - started > timeout) throw new Error("waitFor timed out");
    await sleep(10);
  }
}
