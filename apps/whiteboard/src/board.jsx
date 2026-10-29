/* The heavy half of the Whiteboard App: React, Excalidraw and its stylesheet.

   build.mjs bundles this module on its own, gzips it and embeds it in the
   shell (src/extension.js) as an inert string, so Canvas pays for parsing and
   evaluating it only when someone actually opens the whiteboard. */

import { createElement, useEffect, useLayoutEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import { Excalidraw, MainMenu, serializeAsJSON } from "@excalidraw/excalidraw";
import styles from "@excalidraw/excalidraw/index.css";

export { serializeAsJSON };

const UI_OPTIONS = {
  canvasActions: {
    // Excalidraw's own load/save dialogs target the user's disk; the App
    // persists boards on the Agent Server instead.
    loadScene: false,
    saveToActiveFile: false,
  },
};

/* Wrapper of the main-menu button in Excalidraw 0.18's desktop layout. It is
   not public API, so its absence (the compact layout puts the menu in the
   footer; another Excalidraw version may rename it) is a supported state. */
const MENU_ANCHOR = ".App-menu_top__left > div:first-child";

/* Hosts DOM nodes owned by the shell inside Excalidraw's top-right toolbar
   slot, the only slot Excalidraw offers. `menuNode` (the board picker) is
   moved next to the main-menu button instead whenever that button is
   rendered; Excalidraw re-renders this slot with its UI, so the placement is
   re-checked after every render and follows layout changes. The node carries
   data-placement="menu" or "toolbar" for styling. */
function ShellSlot({ node, menuNode }) {
  const ref = useRef(null);
  useEffect(() => {
    if (node) ref.current?.append(node);
    return () => {
      node?.remove();
      menuNode?.remove();
    };
  }, [node, menuNode]);
  useLayoutEffect(() => {
    if (!menuNode || !ref.current) return;
    const anchor = ref.current.closest(".excalidraw")?.querySelector(MENU_ANCHOR);
    const target = anchor ?? ref.current;
    menuNode.dataset.placement = anchor ? "menu" : "toolbar";
    if (menuNode.parentNode !== target) target.prepend(menuNode);
  });
  return createElement("div", { ref, style: { display: "flex", alignItems: "center", gap: "4px" } });
}

function Board({ initialData, onChange, toolbarElement, menuElement }) {
  const latest = useRef(onChange);
  latest.current = onChange;
  return createElement(Excalidraw, {
    initialData,
    langCode: "en",
    UIOptions: UI_OPTIONS,
    renderTopRightUI: toolbarElement || menuElement
      ? () => createElement(ShellSlot, { node: toolbarElement, menuNode: menuElement })
      : undefined,
    onChange: (elements, appState, files) => latest.current?.(elements, appState, files),
  }, createElement(BoardMenu));
}

/* Excalidraw's default main menu minus its "Excalidraw links" (social)
   section. Load/save-to-file items stay out, matching UI_OPTIONS. */
function BoardMenu() {
  const { DefaultItems, Separator } = MainMenu;
  return createElement(
    MainMenu,
    null,
    createElement(DefaultItems.Export),
    createElement(DefaultItems.SaveAsImage),
    createElement(DefaultItems.SearchMenu),
    createElement(DefaultItems.Help),
    createElement(DefaultItems.ClearCanvas),
    createElement(Separator),
    createElement(DefaultItems.ToggleTheme),
    createElement(DefaultItems.ChangeCanvasBackground),
  );
}

/** Mounts one Excalidraw instance into `element`; returns its disposer. */
export function mountBoard({ element, initialData, onChange, toolbarElement, menuElement }) {
  const style = document.createElement("style");
  style.dataset.whiteboard = "excalidraw";
  style.textContent = styles;
  element.append(style);
  const host = document.createElement("div");
  host.className = "whiteboard-excalidraw";
  host.style.cssText = "position:absolute;inset:0";
  element.append(host);
  const root = createRoot(host);
  root.render(createElement(Board, { initialData, onChange, toolbarElement, menuElement }));
  return () => {
    root.unmount();
    host.remove();
    style.remove();
  };
}
