import styles from "./styles.css?inline";
import { mountTerminal } from "./terminal";
import type { CanvasHost, PageContext } from "./types";

function mountPage(host: CanvasHost, context: PageContext): () => void {
  const style = document.createElement("style");
  style.dataset.terminal = "styles";
  style.textContent = styles;
  const root = document.createElement("section");
  root.className = "terminal-shell";
  const terminalMount = document.createElement("div");
  terminalMount.className = "terminal-shell__mount";
  root.append(terminalMount);
  context.container.append(style, root);
  const disposeTerminal = mountTerminal(terminalMount, host);

  return () => {
    disposeTerminal();
    root.remove();
    style.remove();
  };
}

export function activate(host: CanvasHost): () => void {
  if (host.apiVersion !== "1") throw new Error("Terminal requires Canvas host API 1.");
  return host.registerPage("terminal", (context) => mountPage(host, context));
}
