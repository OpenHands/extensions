import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import xtermStyles from "@xterm/xterm/css/xterm.css?inline";
import terminalStyles from "./terminal.css?inline";
import type { CanvasHost } from "./types";

const EXECUTE_PATH = "/api/bash/execute_bash_command";
const COMMAND_TIMEOUT_SECONDS = 300;

type BashOutput = {
  exit_code?: unknown;
  stdout?: unknown;
  stderr?: unknown;
};

type HomeResponse = { home?: unknown };

function node<K extends keyof HTMLElementTagNameMap>(tag: K, className?: string): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag);
  if (className) element.className = className;
  return element;
}

function parseObject<T>(value: unknown, message: string): T {
  if (typeof value !== "string") return value as T;
  try { return JSON.parse(value) as T; }
  catch { throw new Error(message); }
}

function validWorkingDirectory(value: unknown): value is string {
  return typeof value === "string" && value.startsWith("/") && value.length <= 4096 && !/[\0-\x1f\x7f]/.test(value);
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "The command request failed.";
}

export function mountTerminal(container: HTMLElement, host: CanvasHost): () => void {
  const shadow = container.attachShadow({ mode: "open" });
  const style = node("style");
  style.textContent = `${xtermStyles}\n${terminalStyles}`;
  const app = node("main", "terminal-app");
  const surface = node("div", "terminal-app__surface");
  surface.setAttribute("aria-label", "Terminal command runner");
  const status = node("div", "terminal-app__status");
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  status.hidden = true;
  app.append(surface, status);
  shadow.append(style, app);

  const terminal = new Terminal({
    cursorBlink: true,
    cursorStyle: "block",
    convertEol: true,
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    fontSize: 14,
    lineHeight: 1.2,
    scrollback: 10_000,
    theme: {
      background: "#06090d",
      foreground: "#e6edf5",
      cursor: "#5eead4",
      selectionBackground: "#31435a",
      black: "#111827",
      red: "#fb7185",
      green: "#86efac",
      yellow: "#fde047",
      blue: "#93c5fd",
      magenta: "#d8b4fe",
      cyan: "#67e8f9",
      white: "#f8fafc",
    },
  });
  const fitAddon = new FitAddon();
  terminal.loadAddon(fitAddon);
  terminal.open(surface);
  fitAddon.fit();
  terminal.focus();

  let cwd = "";
  let line = "";
  let ready = false;
  let running = false;
  let disposed = false;
  let historyIndex = 0;
  const history: string[] = [];

  const setStatus = (message = "", error = false): void => {
    status.textContent = message;
    status.classList.toggle("terminal-app__status--error", error);
    status.hidden = message.length === 0;
  };
  const prompt = (): void => terminal.write(`\x1b[32m${cwd}\x1b[0m $ `);
  const replaceLine = (value: string): void => {
    if (line.length > 0) terminal.write(`\x1b[${line.length}D\x1b[K`);
    line = value;
    terminal.write(line);
  };

  async function execute(command: string): Promise<void> {
    running = true;
    setStatus("Running…");
    try {
      const raw = await host.agentServer.request<BashOutput>({
        method: "POST",
        path: EXECUTE_PATH,
        body: { command, cwd, timeout: COMMAND_TIMEOUT_SECONDS },
      });
      if (disposed) return;
      const result = parseObject<BashOutput>(raw, "The Agent Server returned invalid command output.");
      const stdout = typeof result?.stdout === "string" ? result.stdout : "";
      const stderr = typeof result?.stderr === "string" ? result.stderr : "";
      if (stdout) terminal.write(stdout);
      if (stderr) terminal.write(`\x1b[31m${stderr}\x1b[0m`);
      if ((stdout || stderr) && !`${stdout}${stderr}`.endsWith("\n")) terminal.write("\r\n");
      if (typeof result?.exit_code === "number" && result.exit_code !== 0) {
        terminal.writeln(`\x1b[90m[exit ${result.exit_code}]\x1b[0m`);
      }
      setStatus();
    } catch (error) {
      if (disposed) return;
      const message = errorMessage(error);
      terminal.writeln(`\x1b[31m${message}\x1b[0m`);
      setStatus(message, true);
    } finally {
      if (!disposed) {
        running = false;
        prompt();
        terminal.focus();
      }
    }
  }

  const dataSubscription = terminal.onData((data) => {
    if (!ready || running) return;
    if (data === "\x1b[A" || data === "\x1b[B") {
      if (data === "\x1b[A" && historyIndex > 0) historyIndex -= 1;
      if (data === "\x1b[B" && historyIndex < history.length) historyIndex += 1;
      replaceLine(history[historyIndex] ?? "");
      return;
    }
    for (const character of data) {
      if (character === "\r" || character === "\n") {
        terminal.write("\r\n");
        const command = line.trim();
        line = "";
        if (!command) {
          prompt();
          continue;
        }
        history.push(command);
        historyIndex = history.length;
        void execute(command);
        return;
      }
      if (character === "\x7f") {
        if (line.length > 0) {
          line = line.slice(0, -1);
          terminal.write("\b \b");
        }
      } else if (character === "\x03") {
        line = "";
        terminal.write("^C\r\n");
        prompt();
      } else if (character === "\x0c") {
        terminal.clear();
        prompt();
        terminal.write(line);
      } else if (character >= " ") {
        line += character;
        terminal.write(character);
      }
    }
  });
  const resizeObserver = new ResizeObserver(() => {
    try { fitAddon.fit(); } catch { /* hidden mounts cannot be measured */ }
  });
  resizeObserver.observe(surface);
  surface.addEventListener("click", () => terminal.focus());

  void host.agentServer.request<HomeResponse | string>({ path: "/api/file/home" }).then((raw) => {
    if (disposed) return;
    const response = parseObject<HomeResponse>(raw, "The Agent Server returned an invalid home directory.");
    if (!validWorkingDirectory(response?.home)) throw new Error("The Agent Server did not report a valid home directory.");
    cwd = response.home;
    ready = true;
    terminal.writeln("\x1b[90mCommands run through the active backend.\x1b[0m");
    prompt();
    terminal.focus();
  }).catch((error) => {
    if (disposed) return;
    const message = errorMessage(error);
    terminal.writeln(`\x1b[31m${message}\x1b[0m`);
    setStatus(message, true);
  });

  return () => {
    disposed = true;
    ready = false;
    dataSubscription.dispose();
    resizeObserver.disconnect();
    terminal.dispose();
    shadow.replaceChildren();
    container.replaceChildren();
  };
}
