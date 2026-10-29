import { createRoot } from "react-dom/client";
import { App } from "./App";
import { DatabaseClient } from "./database-client";
import styles from "./styles.css?inline";
import type { CanvasHost } from "./types";

const PAGE_ID = "sql-lab";

export function activate(host: CanvasHost): () => void {
  if (host.apiVersion !== "1") {
    throw new Error(`Browser SQL Lab requires Canvas host API 1, received ${host.apiVersion}.`);
  }

  return host.registerPage(PAGE_ID, ({ container, path, navigate }) => {
    const controller = new AbortController();
    const client = new DatabaseClient();
    const style = document.createElement("style");
    style.dataset.browserSqlLab = "styles";
    style.textContent = styles;
    const mountPoint = document.createElement("div");
    mountPoint.dataset.browserSqlLab = "root";
    container.append(style, mountPoint);

    const root = createRoot(mountPoint);
    root.render(
      <App
        host={host}
        path={path}
        navigate={navigate}
        signal={controller.signal}
        client={client}
      />,
    );

    return () => {
      controller.abort();
      client.terminate();
      root.unmount();
      mountPoint.remove();
      style.remove();
    };
  });
}

export const __testing = { PAGE_ID };
