/* Whiteboard App shell. Kept deliberately small: it registers the page and
   owns persistence, while Excalidraw itself arrives as a gzipped payload that
   is decompressed and evaluated on the first mount (see build.mjs). */

import payload from "virtual:board-payload";
import { PICKER_STYLES, createBoardPicker } from "./picker.js";
import { BOARD_ID, BoardStore, titleFromId } from "./store.js";

const PAGE_ID = "board";
const DEFAULT_BOARD = "default";
const SAVE_DELAY_MS = 800;
const ROOT_CLASS = "whiteboard-app";
const THEME_KEY_PREFIX = "openhands.apps.whiteboard.theme";
const LAST_BOARD_KEY_PREFIX = "openhands.apps.whiteboard.last-board";
// How often a mount refreshes the board's "updated" time while saving.
const META_REFRESH_MS = 60_000;

const STYLES = `
.${ROOT_CLASS} {
  position: relative;
  height: 100vh;
  width: 100%;
  overflow: hidden;
  color: var(--oh-foreground, #eef2f7);
  font: inherit;
}
.${ROOT_CLASS}__state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px;
  text-align: center;
  font-size: 14px;
  color: var(--oh-muted, #a3b0c4);
}
.${ROOT_CLASS}__state[role="alert"] { color: var(--oh-danger, #e76a5e); }
.${ROOT_CLASS}__button {
  height: 36px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid var(--oh-border, #4b5468);
  background: var(--oh-color-base-secondary, #21252f);
  color: var(--oh-contrast, #fff);
  font: inherit;
  cursor: pointer;
}
.${ROOT_CLASS}__button:focus-visible { outline: 2px solid var(--oh-focus, #fff); outline-offset: 2px; }
.${ROOT_CLASS}__toolbar { display: flex; align-items: center; gap: 4px; }
.${ROOT_CLASS}__status {
  display: inline-flex;
  align-items: center;
  height: 36px;
  padding: 0 10px;
  border-radius: 8px;
  font-size: 12px;
  white-space: nowrap;
  color: var(--color-gray-60, #7a7a7a);
}
.${ROOT_CLASS}__status[data-state="error"] { color: var(--color-danger, #e03131); }
${PICKER_STYLES}`;

function decodeBase64(text) {
  if (typeof Uint8Array.fromBase64 === "function") return Uint8Array.fromBase64(text);
  const binary = atob(text);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

/* Decompress and evaluate the Excalidraw payload once per activation. A
   failure clears the cache so the next mount can retry. */
let boardModule = null;
function loadBoardModule() {
  if (!boardModule) {
    boardModule = (async () => {
      const bytes = decodeBase64(payload);
      const source = await new Response(
        new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip")),
      ).text();
      const url = URL.createObjectURL(new Blob([source], { type: "text/javascript" }));
      try {
        return await import(/* @vite-ignore */ url);
      } finally {
        URL.revokeObjectURL(url);
      }
    })().catch((err) => {
      boardModule = null;
      throw err;
    });
  }
  return boardModule;
}

/* Excalidraw reports every pointer move through onChange. Saving only when
   the drawing itself changed keeps writes proportional to edits: element
   versions increase on every edit (including deletion), files are
   append-only, and the background colour is the one document-level setting
   users commonly change. */
function sceneSignature(elements, appState, files) {
  let versions = 0;
  for (const element of elements) versions += element.version;
  return `${elements.length}:${versions}:${Object.keys(files || {}).length}:${appState.viewBackgroundColor}`;
}

/* Per-viewer conveniences kept in localStorage, namespaced by backend: the
   UI theme (.excalidraw files do not carry it; dark matches Canvas) and the
   last board opened (what the page root shows). Storage can be unavailable,
   which only loses the convenience. */
function readLocal(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeLocal(key, value) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    // Not persisting a preference is harmless.
  }
}

/** The board a route remainder names, the fallback for the root, or null. */
function boardIdFromPath(path, fallback = DEFAULT_BOARD) {
  const id = (path || "").replace(/^\/+|\/+$/g, "");
  if (!id) return BOARD_ID.test(fallback ?? "") ? fallback : DEFAULT_BOARD;
  return BOARD_ID.test(id) ? id : null;
}

function stateMessage(root, text, { alert = false, action } = {}) {
  const box = document.createElement("div");
  box.className = `${ROOT_CLASS}__state`;
  if (alert) box.setAttribute("role", "alert");
  else box.setAttribute("aria-live", "polite");
  const message = document.createElement("p");
  message.style.margin = "0";
  message.textContent = text;
  box.append(message);
  if (action) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `${ROOT_CLASS}__button`;
    button.textContent = action.label;
    button.addEventListener("click", action.onClick);
    box.append(button);
  }
  root.replaceChildren(box);
}

export function activate(host) {
  if (host.apiVersion !== "1") {
    throw new Error(`Whiteboard requires Canvas host API 1, received ${host.apiVersion}.`);
  }
  const store = new BoardStore(host);
  const saves = new Map();
  const themeKey = `${THEME_KEY_PREFIX}:${host.backend.id}`;
  const lastBoardKey = `${LAST_BOARD_KEY_PREFIX}:${host.backend.id}`;
  const pageRoot = `/extensions/${encodeURIComponent(host.extension.name)}/boards`;
  const boardRoute = (id) => `${pageRoot}/${id}`;

  return host.registerPage(PAGE_ID, ({ container, path, navigate }) => {
    let disposed = false;
    let unmountBoard = null;
    let saveTimer = null;
    let lastSignature = null;
    let metaRefreshedAt = 0;
    let picker = null;

    const style = document.createElement("style");
    style.dataset.whiteboard = "shell";
    style.textContent = STYLES;
    const root = document.createElement("div");
    root.className = ROOT_CLASS;
    container.append(style, root);

    const toolbar = document.createElement("div");
    toolbar.className = `${ROOT_CLASS}__toolbar`;
    const status = document.createElement("span");
    status.className = `${ROOT_CLASS}__status`;
    status.setAttribute("role", "status");
    const setStatus = (state, text) => {
      status.dataset.state = state;
      status.textContent = text;
    };

    const boardId = boardIdFromPath(path, readLocal(lastBoardKey));
    if (!boardId) {
      stateMessage(root, `"${path}" is not a valid board name.`, {
        alert: true,
        action: { label: "Open your boards", onClick: () => navigate(pageRoot) },
      });
      return () => {
        disposed = true;
        root.remove();
        style.remove();
      };
    }

    // Save ordering and failed edits must survive navigation between mounts.
    if (!saves.has(boardId)) {
      saves.set(boardId, { pending: null, revision: 0, saving: Promise.resolve() });
    }
    const save = saves.get(boardId);

    /* Saving also stamps meta.json with the update time (which orders the
       board list), at most once a minute per mount. The first save of a
       board that has no metadata yet creates it. */
    const refreshMeta = async () => {
      if (Date.now() - metaRefreshedAt < META_REFRESH_MS) return;
      metaRefreshedAt = Date.now();
      const now = new Date().toISOString();
      const meta = await store.readMeta(boardId);
      await store.updateMeta(boardId, { createdAt: meta.createdAt ?? now, updatedAt: now });
    };

    const flush = () => {
      clearTimeout(saveTimer);
      saveTimer = null;
      if (!save.pending) return save.saving;
      const snapshot = save.pending;
      save.pending = null;
      save.saving = save.saving
        .then(() => store.save(boardId, snapshot.json))
        .then(() => refreshMeta().catch(() => {
          // The drawing is saved; a stale list order is not worth an error.
          metaRefreshedAt = 0;
        }))
        .then(
          () => { if (!disposed && save.revision === snapshot.revision && !save.pending) setStatus("saved", "Saved"); },
          (err) => {
            // A newer edit may already be queued rather than pending.
            if (save.revision === snapshot.revision) save.pending ??= snapshot;
            if (!disposed && save.revision === snapshot.revision) setStatus("error", `Save failed: ${err.message}`);
          },
        );
      return save.saving;
    };

    const start = async () => {
      stateMessage(root, "Loading whiteboard…");
      try {
        // allSettled: an archived board redirects regardless of whether the
        // (heavy, irrelevant in that case) board module loaded successfully.
        const [boardResult, sceneResult, metaResult] = await Promise.allSettled([
          loadBoardModule(),
          (async () => {
            await flush();
            return save.pending ? JSON.parse(save.pending.json) : store.load(boardId);
          })(),
          store.readMeta(boardId),
        ]);
        if (disposed) return;
        const meta = metaResult.status === "fulfilled" ? metaResult.value : { title: titleFromId(boardId) };
        if (meta.archived) {
          const visible = await store.list().catch(() => []);
          if (disposed) return;
          if (visible[0]) {
            navigate(boardRoute(visible[0].id));
            return;
          }
          stateMessage(root, "All boards are archived.", {
            action: {
              label: "Create a board",
              onClick: async () => {
                try {
                  const created = await store.create();
                  if (!disposed) navigate(boardRoute(created.id));
                } catch (err) {
                  if (!disposed) {
                    stateMessage(root, `Could not create a board: ${err.message}`, {
                      alert: true,
                      action: { label: "Try again", onClick: start },
                    });
                  }
                }
              },
            },
          });
          return;
        }
        if (boardResult.status === "rejected") throw boardResult.reason;
        if (sceneResult.status === "rejected") throw sceneResult.reason;
        const board = boardResult.value;
        const scene = sceneResult.value;
        writeLocal(lastBoardKey, boardId);
        root.replaceChildren();
        if (save.pending) setStatus("error", "Save failed: unsaved edits retained; edit to retry.");
        else setStatus("saved", scene ? "Saved" : "New board");
        picker?.dispose();
        picker = createBoardPicker({
          store,
          boardId,
          openBoard: (id) => navigate(boardRoute(id)),
          onArchived: async (id) => {
            if (readLocal(lastBoardKey) === id) writeLocal(lastBoardKey, null);
            const remaining = await store.list().catch(() => []);
            if (disposed) return;
            // When nothing remains, pageRoot falls back to DEFAULT_BOARD, which
            // start() now recognizes as archived rather than silently reopening it.
            navigate(remaining[0] ? boardRoute(remaining[0].id) : pageRoot);
          },
        });
        picker.setTitle(meta.title);
        toolbar.replaceChildren(status);
        let theme = readLocal(themeKey) === "light" ? "light" : "dark";
        const initialData = {
          elements: scene?.elements ?? [],
          appState: { ...scene?.appState, theme },
          files: scene?.files ?? {},
        };
        unmountBoard = board.mountBoard({
          element: root,
          initialData,
          toolbarElement: toolbar,
          menuElement: picker.element,
          onChange: (elements, appState, files) => {
            if (appState.theme !== theme) {
              theme = appState.theme;
              writeLocal(themeKey, theme);
            }
            const signature = sceneSignature(elements, appState, files);
            if (lastSignature === null) {
              // Excalidraw's first onChange reflects the loaded scene.
              lastSignature = signature;
              return;
            }
            if (signature === lastSignature) return;
            lastSignature = signature;
            save.pending = {
              revision: ++save.revision,
              json: board.serializeAsJSON(elements, appState, files, "local"),
            };
            setStatus("saving", "Saving…");
            clearTimeout(saveTimer);
            saveTimer = setTimeout(flush, SAVE_DELAY_MS);
          },
        });
      } catch (err) {
        if (disposed) return;
        stateMessage(root, `Unable to open the whiteboard: ${err.message}`, {
          alert: true,
          action: { label: "Try again", onClick: start },
        });
      }
    };
    start();

    return () => {
      disposed = true;
      // Persist the last edits even when the user navigates away mid-delay.
      flush();
      picker?.dispose();
      unmountBoard?.();
      root.remove();
      style.remove();
    };
  });
}

export const __testing = { PAGE_ID, sceneSignature, boardIdFromPath, loadBoardModule };
