/* The board picker: a button in Excalidraw's top-right toolbar slot that opens
   a panel listing boards, with create, rename and archive. Plain DOM, so it
   renders from the shell without React; its styles use Excalidraw's theme
   variables because it lives inside the Excalidraw tree. */

import { MAX_TITLE_LENGTH } from "./store.js";

export const PICKER_CLASS = "whiteboard-picker";
const C = PICKER_CLASS;

export const PICKER_STYLES = `
.${C} { position: relative; display: flex; align-items: center; }
/* Next to Excalidraw's main-menu button: beside it, and opening rightwards. */
.${C}[data-placement="menu"] { position: absolute; top: 0; left: calc(100% + 8px); }
.${C}[data-placement="menu"] .${C}__panel { left: 0; right: auto; }
.${C} button, .${C} input { font: inherit; }
.${C}__trigger {
  display: inline-flex; align-items: center; gap: 6px;
  height: 36px; max-width: 200px; padding: 0 10px;
  border: 0; border-radius: var(--border-radius-lg, 8px);
  background: var(--island-bg-color, #fff);
  box-shadow: var(--shadow-island, 0 0 0 1px rgba(0,0,0,.1));
  color: var(--color-on-surface, #1b1b1f);
  font-size: 13px; cursor: pointer;
}
.${C}__trigger span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.${C}__trigger:hover, .${C}__item:hover, .${C}__link:hover { background: var(--button-hover-bg, var(--color-surface-high, #f1f0ff)); }
.${C} button:focus-visible, .${C} input:focus-visible { outline: 2px solid var(--color-primary, #6965db); outline-offset: 1px; }
.${C}__panel {
  position: absolute; top: calc(100% + 8px); right: 0; z-index: var(--zIndex-popup, 1001);
  width: 280px; max-width: calc(100vw - 32px); box-sizing: border-box;
  display: flex; flex-direction: column; gap: 8px; padding: 8px;
  border-radius: var(--border-radius-lg, 8px);
  background: var(--island-bg-color, #fff);
  box-shadow: var(--shadow-island, 0 0 0 1px rgba(0,0,0,.1));
  color: var(--color-on-surface, #1b1b1f);
  font-size: 13px;
}
.${C}__panel[hidden] { display: none; }
.${C}__heading { margin: 4px 6px 0; font-size: 12px; font-weight: 600; opacity: .7; }
.${C}__list { display: flex; flex-direction: column; gap: 2px; max-height: 280px; overflow-y: auto; margin: 0; padding: 0; list-style: none; }
.${C}__item {
  display: flex; align-items: center; gap: 8px; width: 100%;
  min-height: 32px; padding: 0 8px; border: 0; border-radius: 6px;
  background: transparent; color: inherit; text-align: left; cursor: pointer;
}
.${C}__item span { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.${C}__item[aria-current="page"] { background: var(--color-surface-high, #f1f0ff); font-weight: 600; }
.${C}__note { margin: 4px 8px; opacity: .7; }
.${C}__note[role="alert"] { color: var(--color-danger, #e03131); opacity: 1; }
.${C}__divider { height: 1px; margin: 0 4px; background: var(--default-border-color, #e9ecef); }
.${C}__form { display: flex; gap: 6px; }
.${C}__input {
  flex: 1; min-width: 0; height: 32px; padding: 0 8px; box-sizing: border-box;
  border: 1px solid var(--input-border-color, #ced4da); border-radius: 6px;
  background: var(--input-bg-color, #fff); color: inherit;
}
.${C}__button {
  height: 32px; padding: 0 10px; border: 0; border-radius: 6px;
  background: var(--color-primary, #6965db); color: var(--color-surface-lowest, #fff); cursor: pointer;
}
.${C}__button:disabled { opacity: .5; cursor: not-allowed; }
.${C}__button--danger { background: var(--color-danger, #e03131); }
.${C}__actions { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; }
.${C}__link {
  height: 28px; padding: 0 8px; border: 0; border-radius: 6px;
  background: transparent; color: inherit; cursor: pointer; opacity: .85;
}
.${C}__confirm { margin: 0 4px; line-height: 1.4; }
`;

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  node.append(...children);
  return node;
}

/**
 * @param {object} options
 * @param {import("./store.js").BoardStore} options.store
 * @param {string} options.boardId    the open board
 * @param {(id: string) => void} options.openBoard
 * @param {(id: string) => void} options.onArchived  called after the open board is archived
 */
export function createBoardPicker({ store, boardId, openBoard, onArchived }) {
  let title = "";
  let open = false;
  let disposed = false;
  let generation = 0; // ignores list responses from an earlier opening
  const panelId = `${C}-panel-${Math.random().toString(36).slice(2, 8)}`;

  const label = el("span", { text: "Boards" });
  const caret = el("span", { "aria-hidden": "true", text: "▾" });
  const trigger = el("button", {
    type: "button",
    class: `${C}__trigger`,
    "aria-haspopup": "dialog",
    "aria-expanded": "false",
    "aria-controls": panelId,
    title: "Switch board",
    onclick: () => (open ? close() : show()),
  }, label, caret);
  const list = el("ul", { class: `${C}__list`, "aria-label": "Boards" });
  const footer = el("div", { class: `${C}__actions` });
  const panel = el("div", {
    id: panelId,
    class: `${C}__panel`,
    role: "dialog",
    "aria-label": "Boards",
    hidden: "",
  });
  const root = el("div", { class: C }, trigger, panel);

  const setTitle = (next) => {
    title = next;
    label.textContent = next;
    trigger.setAttribute("aria-label", `Board: ${next}. Switch board`);
  };

  const note = (text, alert = false) => el("li", {
    class: `${C}__note`,
    ...(alert ? { role: "alert" } : {}),
    text,
  });

  // ------------------------------------------------------------ board list

  const renderList = async () => {
    const mine = ++generation;
    list.replaceChildren(note("Loading boards…"));
    let boards;
    try {
      boards = await store.list();
    } catch (err) {
      if (mine === generation && !disposed) list.replaceChildren(note(`Could not list boards: ${err.message}`, true));
      return;
    }
    if (mine !== generation || disposed) return;
    // The open board is listed even before its first save creates it on disk.
    if (!boards.some((board) => board.id === boardId)) boards.unshift({ id: boardId, title });
    list.replaceChildren(...boards.map((board) => {
      const current = board.id === boardId;
      return el("li", {}, el("button", {
        type: "button",
        class: `${C}__item`,
        ...(current ? { "aria-current": "page" } : {}),
        onclick: () => {
          close();
          if (!current) openBoard(board.id);
        },
      }, el("span", { text: current ? title : board.title })));
    }));
  };

  // ------------------------------------------------------------ forms

  const titleForm = ({ value = "", placeholder, submitLabel, onSubmit, onCancel }) => {
    const input = el("input", {
      class: `${C}__input`,
      type: "text",
      maxlength: String(MAX_TITLE_LENGTH),
      placeholder,
      "aria-label": placeholder,
    });
    input.value = value;
    const submit = el("button", { type: "submit", class: `${C}__button`, text: submitLabel });
    const error = el("p", { class: `${C}__note`, role: "alert", hidden: "" });
    const form = el("form", {
      class: `${C}__form`,
      onsubmit: async (event) => {
        event.preventDefault();
        if (!input.value.trim()) return;
        submit.disabled = true;
        try {
          await onSubmit(input.value);
        } catch (err) {
          if (disposed) return;
          error.textContent = err.message;
          error.hidden = false;
          submit.disabled = false;
        }
      },
      onkeydown: (event) => {
        if (event.key === "Escape" && onCancel) {
          event.stopPropagation();
          onCancel();
        }
      },
    }, input, submit);
    if (onCancel) form.append(el("button", { type: "button", class: `${C}__link`, text: "Cancel", onclick: onCancel }));
    return { node: el("div", {}, form, error), input };
  };

  const createForm = () => titleForm({
    placeholder: "New board name",
    submitLabel: "Create",
    onSubmit: async (name) => {
      const board = await store.create(name);
      close();
      openBoard(board.id);
    },
  });

  const showActions = () => {
    footer.replaceChildren(
      el("button", { type: "button", class: `${C}__link`, text: "Rename board", onclick: showRename }),
      el("button", { type: "button", class: `${C}__link`, text: "Archive board", onclick: showArchive }),
    );
  };

  const showRename = () => {
    const { node, input } = titleForm({
      value: title,
      placeholder: "Board name",
      submitLabel: "Save",
      onSubmit: async (name) => {
        const board = await store.rename(boardId, name);
        setTitle(board.title);
        showActions();
        renderList();
      },
      onCancel: showActions,
    });
    footer.replaceChildren(node);
    input.focus();
    input.select();
  };

  const showArchive = () => {
    const confirm = el("button", {
      type: "button",
      class: `${C}__button ${C}__button--danger`,
      text: "Archive",
      onclick: async () => {
        confirm.disabled = true;
        try {
          await store.archive(boardId);
          close();
          onArchived(boardId);
        } catch (err) {
          if (!disposed) message.textContent = `Could not archive: ${err.message}`;
          confirm.disabled = false;
        }
      },
    });
    const message = el("p", {
      class: `${C}__confirm`,
      text: `Archive “${title}”? It leaves this list; its file stays on the Agent Server.`,
    });
    footer.replaceChildren(el("div", { style: "display:flex;flex-direction:column;gap:6px;width:100%" },
      message,
      el("div", { class: `${C}__actions` }, confirm, el("button", { type: "button", class: `${C}__link`, text: "Cancel", onclick: showActions })),
    ));
    confirm.focus();
  };

  // ------------------------------------------------------------ open/close

  const onPointerDown = (event) => {
    if (!root.contains(event.target)) close();
  };
  const onKeyDown = (event) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      close();
      trigger.focus();
    }
  };

  function show() {
    if (open || disposed) return;
    open = true;
    panel.replaceChildren(
      el("p", { class: `${C}__heading`, text: "Boards" }),
      list,
      el("div", { class: `${C}__divider` }),
      createForm().node,
      el("div", { class: `${C}__divider` }),
      footer,
    );
    showActions();
    panel.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
    document.addEventListener("pointerdown", onPointerDown, true);
    panel.addEventListener("keydown", onKeyDown);
    renderList();
  }

  function close() {
    if (!open) return;
    open = false;
    generation += 1;
    panel.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
    document.removeEventListener("pointerdown", onPointerDown, true);
    panel.removeEventListener("keydown", onKeyDown);
  }

  return {
    element: root,
    setTitle,
    dispose() {
      close();
      disposed = true;
      root.remove();
    },
  };
}
