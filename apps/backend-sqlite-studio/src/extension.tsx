import { createRoot } from "react-dom/client";
import { App } from "./App";
import styles from "./styles.css?inline";
import type { CanvasHost } from "./types";

const PAGES = ["studio", "handoff"] as const;

export function activate(host: CanvasHost): () => void {
  if (host.apiVersion !== "1") throw new Error(`Backend SQLite Studio requires Canvas host API 1, received ${host.apiVersion}.`);
  const unregister = PAGES.map((pageId) => host.registerPage(pageId, ({ container, path, navigate }) => {
    const controller = new AbortController();
    const style = document.createElement("style");
    style.dataset.backendSqliteStudio = "styles";
    style.textContent = styles;
    const mountPoint = document.createElement("div");
    mountPoint.dataset.backendSqliteStudio = "root";
    container.append(style, mountPoint);
    const root = createRoot(mountPoint);
    root.render(<App host={host} pageId={pageId} path={path} navigate={navigate} signal={controller.signal} />);
    return () => {
      controller.abort();
      root.unmount();
      mountPoint.remove();
      style.remove();
    };
  }));
  return () => { for (const remove of unregister) remove(); };
}

export const __testing = { PAGES };
