import { createRoot } from "react-dom/client";
import { App } from "./App";
import type { CanvasHost } from "./types";
import styles from "./styles.css?inline";

export function activate(host: CanvasHost): () => void {
  if (host.apiVersion !== "1") throw new Error(`Conversation Search requires Canvas host API 1, received ${host.apiVersion}.`);
  return host.registerPage("search", ({ container, path, navigate }) => {
    const controller = new AbortController();
    const style = document.createElement("style");
    style.dataset.conversationSearchSidecar = "styles";
    style.textContent = styles;
    const mountPoint = document.createElement("div");
    mountPoint.dataset.conversationSearchSidecar = "root";
    container.append(style, mountPoint);
    const root = createRoot(mountPoint);
    root.render(<App host={host} path={path} navigate={navigate} signal={controller.signal} />);
    return () => { controller.abort(); root.unmount(); mountPoint.remove(); style.remove(); };
  });
}
