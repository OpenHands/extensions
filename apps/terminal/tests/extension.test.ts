import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { activate } from "../src/extension";
import type { AgentServerRequest } from "../src/types";

const xterm = vi.hoisted(() => ({
  writes: [] as string[],
  onData: undefined as ((data: string) => void) | undefined,
  disposed: false,
}));

vi.mock("@xterm/addon-fit", () => ({ FitAddon: class { fit(): void {} } }));
vi.mock("@xterm/xterm", () => ({
  Terminal: class {
    loadAddon(): void {}
    open(surface: HTMLElement): void {
      const terminal = document.createElement("div");
      terminal.className = "xterm";
      const textarea = document.createElement("textarea");
      textarea.className = "xterm-helper-textarea";
      terminal.append(textarea);
      surface.append(terminal);
    }
    focus(): void {}
    onData(callback: (data: string) => void): { dispose(): void } {
      xterm.onData = callback;
      return { dispose: () => { xterm.onData = undefined; } };
    }
    write(value: string): void { xterm.writes.push(value); }
    writeln(value: string): void { xterm.writes.push(`${value}\n`); }
    clear(): void { xterm.writes.length = 0; }
    dispose(): void { xterm.disposed = true; }
  },
}));

type Host = Parameters<typeof activate>[0];
type Mount = Parameters<Host["registerPage"]>[1];
type Request = (request: AgentServerRequest) => Promise<unknown>;

function createHarness(requestImpl?: Request): {
  host: Host;
  request: ReturnType<typeof vi.fn<Request>>;
  mount(): Mount;
  unregisterCount(): number;
} {
  let registeredMount: Mount | undefined;
  let unregisters = 0;
  const request = vi.fn(requestImpl ?? (async (call) => {
    if (call.path === "/api/file/home") return { home: "/workspace" };
    return { exit_code: 0, stdout: "command output\n", stderr: "" };
  }));
  const host: Host = {
    apiVersion: "1",
    extension: { name: "terminal", version: "0.5.0", resolvedRef: "test" },
    backend: { id: "local-test", kind: "local", orgId: null },
    agentServer: { request: request as Host["agentServer"]["request"] },
    registerPage(id, mount) {
      expect(id).toBe("terminal");
      registeredMount = mount;
      return () => { unregisters += 1; };
    },
  };
  return {
    host,
    request,
    mount() {
      if (!registeredMount) throw new Error("Page was not registered.");
      return registeredMount;
    },
    unregisterCount: () => unregisters,
  };
}

async function mounted(harness = createHarness()): Promise<{ container: HTMLElement; terminalMount: HTMLElement; dispose(): void }> {
  activate(harness.host);
  const container = document.createElement("div");
  document.body.append(container);
  const dispose = harness.mount()({ container, path: "" }) as () => void;
  await vi.waitFor(() => expect(xterm.onData).toBeTypeOf("function"));
  await vi.waitFor(() => expect(xterm.writes.join("")).toContain("/workspace"));
  return { container, terminalMount: container.querySelector(".terminal-shell__mount") as HTMLElement, dispose };
}

beforeEach(() => {
  xterm.writes.length = 0;
  xterm.onData = undefined;
  xterm.disposed = false;
  vi.stubGlobal("ResizeObserver", class { observe(): void {} disconnect(): void {} });
  vi.stubGlobal("fetch", vi.fn(() => { throw new Error("fetch must not be used"); }));
  vi.stubGlobal("WebSocket", class { constructor() { throw new Error("WebSocket must not be used"); } });
});

afterEach(() => {
  document.body.replaceChildren();
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("Terminal Canvas extension", () => {
  it("registers once and unregisters on activation cleanup", () => {
    const harness = createHarness();
    const dispose = activate(harness.host);
    expect(typeof harness.mount()).toBe("function");
    dispose();
    expect(harness.unregisterCount()).toBe(1);
  });

  it("rejects unsupported host versions", () => {
    const harness = createHarness();
    expect(() => activate({ ...harness.host, apiVersion: "2" })).toThrow("requires Canvas host API 1");
  });

  it("renders xterm directly without credentials or custom transport", async () => {
    localStorage.setItem("openhands-backends", "not used");
    const harness = createHarness();
    const { container, terminalMount, dispose } = await mounted(harness);
    expect(terminalMount.shadowRoot?.querySelector(".xterm")).not.toBeNull();
    expect(container.querySelector("iframe")).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
    expect(harness.request).toHaveBeenCalledWith({ path: "/api/file/home" });
    dispose();
    expect(container.childElementCount).toBe(0);
    expect(xterm.disposed).toBe(true);
  });

  it("executes entered commands through the authenticated Host API", async () => {
    const harness = createHarness();
    await mounted(harness);
    xterm.onData?.("printf hello");
    xterm.onData?.("\r");
    await vi.waitFor(() => expect(harness.request).toHaveBeenCalledTimes(2));
    expect(harness.request).toHaveBeenLastCalledWith({
      method: "POST",
      path: "/api/bash/execute_bash_command",
      body: { command: "printf hello", cwd: "/workspace", timeout: 300 },
    });
    await vi.waitFor(() => expect(xterm.writes.join("")).toContain("command output"));
  });

  it("renders stderr and nonzero exit status", async () => {
    const harness = createHarness(async (call) => call.path === "/api/file/home"
      ? { home: "/workspace" }
      : { exit_code: 7, stdout: "", stderr: "failed" });
    await mounted(harness);
    xterm.onData?.("false\r");
    await vi.waitFor(() => expect(xterm.writes.join("")).toContain("failed"));
    expect(xterm.writes.join("")).toContain("[exit 7]");
  });

  it("shows request failures without issuing another transport request", async () => {
    const harness = createHarness(async (call) => {
      if (call.path === "/api/file/home") return JSON.stringify({ home: "/workspace" });
      throw new Error("backend unavailable");
    });
    const { terminalMount } = await mounted(harness);
    xterm.onData?.("pwd\r");
    await vi.waitFor(() => expect(terminalMount.shadowRoot?.querySelector('[role="status"]')?.textContent).toBe("backend unavailable"));
    expect(xterm.writes.join("")).toContain("backend unavailable");
  });

  it("ignores command input while a request is running", async () => {
    let resolveCommand: ((value: unknown) => void) | undefined;
    const harness = createHarness(async (call) => {
      if (call.path === "/api/file/home") return { home: "/workspace" };
      return new Promise((resolve) => { resolveCommand = resolve; });
    });
    await mounted(harness);
    xterm.onData?.("sleep 1\r");
    xterm.onData?.("ignored\r");
    expect(harness.request).toHaveBeenCalledTimes(2);
    resolveCommand?.({ exit_code: 0, stdout: "done\n", stderr: "" });
    await vi.waitFor(() => expect(xterm.writes.join("")).toContain("done"));
  });
});
