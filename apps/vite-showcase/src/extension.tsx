import { createRoot } from "react-dom/client";
import { App } from "./App";
import styles from "./styles.css?inline";
import type { CanvasHost } from "./types";

const PAGE_ID = "showcase";

export function activate(host: CanvasHost): () => void {
  if (host.apiVersion !== "1") {
    throw new Error(`Vite Showcase requires Canvas host API 1, received ${host.apiVersion}.`);
  }

  return host.registerPage(PAGE_ID, ({ container, path, navigate }) => {
    const controller = new AbortController();
    const style = document.createElement("style");
    style.dataset.viteShowcase = "styles";
    style.textContent = styles;
    const mountPoint = document.createElement("div");
    mountPoint.dataset.viteShowcase = "root";
    container.append(style, mountPoint);

    const root = createRoot(mountPoint);
    root.render(<App host={host} path={path} navigate={navigate} signal={controller.signal} />);

    return () => {
      controller.abort();
      root.unmount();
      mountPoint.remove();
      style.remove();
    };
  });
}

export const __testing = { PAGE_ID };
