import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import manifest from "../canvas-extension.json";
import { normalizeRoute, ROOT_ROUTE } from "./App";
import { activate } from "./extension";
import { workspaceToken } from "./repository-service";
import type { CanvasHost, MountContext, RepositoryAnalysis, WorkerRequest } from "./types";

const WORKSPACE = "/workspace/demo";
const ANALYSIS: RepositoryAnalysis = {
  branch: "main",
  files: 4,
  bytes: 4096,
  sourceSamples: 2,
  historyEntries: 7,
  truncated: false,
  languages: [{ name: "TypeScript", files: 3, bytes: 3072, percent: 75 }],
  directories: [{ name: "src", files: 3, bytes: 3072, percent: 75 }],
  largeFiles: [{ path: "src/App.tsx", bytes: 2048, language: "TypeScript" }],
  churnHotspots: [{ path: "src/App.tsx", bytes: 2048, language: "TypeScript", changes: 7 }],
  dependencies: [{ name: "react", source: "package.json", kind: "dependency", references: 1 }],
  imports: [{ name: "react", source: "src/App.tsx", kind: "import", references: 2 }],
};

const workers: FakeWorker[] = [];

class FakeWorker {
  listeners = new Map<string, EventListener>();
  requests: WorkerRequest[] = [];
  terminate = vi.fn();
  constructor() { workers.push(this); }
  addEventListener(type: string, listener: EventListener) { this.listeners.set(type, listener); }
  removeEventListener(type: string, listener: EventListener) {
    if (this.listeners.get(type) === listener) this.listeners.delete(type);
  }
  postMessage(request: WorkerRequest) {
    this.requests.push(request);
    if (request.type === "analyze") {
      queueMicrotask(() => this.listeners.get("message")?.({ data: { id: request.id, ok: true, data: ANALYSIS } } as unknown as Event));
    }
  }
}

function makeHost(options: { probe?: string; failWorkspaces?: boolean } = {}) {
  let mount: ((context: MountContext) => void | (() => void)) | undefined;
  const unregister = vi.fn();
  const requests: Array<{ path: string; method?: string; body?: unknown }> = [];
  const host: CanvasHost = {
    apiVersion: "1",
    extension: { name: "wasm-repo-lens", version: "0.1.0", resolvedRef: "test" },
    backend: { id: "local", kind: "local" },
    agentServer: {
      async request(request) {
        requests.push(request);
        if (request.path === "/api/workspaces") {
          if (options.failWorkspaces) throw new Error("Agent Server unavailable");
          return { workspaceParents: [{ path: "/workspace" }] } as never;
        }
        if (request.path.startsWith("/api/file/search_subdirs")) {
          return { items: [{ path: WORKSPACE, name: "demo", is_dir: true }] } as never;
        }
        const body = request.body as { command: string; timeout: number };
        if (body.timeout === 10) return { exit_code: 0, stdout: options.probe ?? "WASM_REPO_LENS_PROBE\t0\t0\n", stderr: "" } as never;
        return { exit_code: 0, stdout: "V\t1\n", stderr: "" } as never;
      },
    },
    registerPage: vi.fn((_id, callback) => { mount = callback; return unregister; }),
    navigate: vi.fn(),
  };
  return { host, unregister, requests, getMount: () => mount };
}

async function flush() {
  await act(async () => { await Promise.resolve(); await Promise.resolve(); await new Promise((resolve) => setTimeout(resolve, 0)); });
}

async function mountAt(path: string, options: { probe?: string; failWorkspaces?: boolean } = {}) {
  const fixture = makeHost(options);
  const deactivate = activate(fixture.host);
  const container = document.createElement("div");
  const navigate = vi.fn();
  let cleanup: void | (() => void);
  await act(async () => { cleanup = fixture.getMount()!({ container, path, navigate }); });
  await flush();
  return { ...fixture, container, navigate, cleanup: cleanup!, deactivate, worker: workers.at(-1)! };
}

beforeEach(() => {
  workers.length = 0;
  vi.stubGlobal("Worker", FakeWorker);
});

afterEach(() => vi.unstubAllGlobals());

describe("WASM Repo Lens activation and routing", () => {
  it("registers exactly the manifest page and unregisters on deactivation", () => {
    const { host, unregister } = makeHost();
    const deactivate = activate(host);
    expect(manifest.contributes.pages.map((page) => page.id)).toEqual(["repo-lens"]);
    expect(host.registerPage).toHaveBeenCalledWith("repo-lens", expect.any(Function));
    deactivate();
    expect(unregister).toHaveBeenCalledOnce();
  });

  it("rejects unsupported host API versions before registration", () => {
    const fixture = makeHost();
    fixture.host.apiVersion = "2";
    expect(() => activate(fixture.host)).toThrow("requires Canvas host API 1");
    expect(fixture.host.registerPage).not.toHaveBeenCalled();
  });

  it.each([
    ["", { view: "lens", token: null }],
    ["lens", { view: "lens", token: null }],
    ["workspace/YQ", { view: "lens", token: "YQ" }],
    ["about", { view: "about" }],
    ["missing", { view: "not-found" }],
  ])("normalizes %s", (path, expected) => expect(normalizeRoute(path)).toEqual(expected));

  it("navigates nested routes", async () => {
    const { container, navigate, cleanup, deactivate } = await mountAt("");
    const boundary = [...container.querySelectorAll("button")].find((button) => button.textContent?.includes("Inspect the boundary"));
    boundary?.click();
    expect(navigate).toHaveBeenCalledWith(`${ROOT_ROUTE}/about`);
    await act(async () => cleanup());
    deactivate();
  });
});

describe("WASM Repo Lens UI", () => {
  it("discovers, probes, analyzes, and renders visualizations", async () => {
    const token = workspaceToken(WORKSPACE);
    const { container, requests, cleanup, deactivate } = await mountAt(`workspace/${token}`);
    expect(container.textContent).toContain("Available for branch and churn data");
    const analyze = container.querySelector('[data-testid="analyze"]') as HTMLButtonElement;
    await act(async () => analyze.click());
    await flush();
    expect(container.querySelector('[data-testid="analysis-dashboard"]')).not.toBeNull();
    expect(container.textContent).toContain("Language distribution");
    expect(container.textContent).toContain("TypeScript");
    expect(container.textContent).toContain("src/App.tsx");
    expect(container.textContent).toContain("Declared dependencies");
    const commands = requests.filter((request) => request.path === "/api/bash/execute_bash_command");
    expect(commands).toHaveLength(2);
    expect(commands.every((request) => (request.body as { cwd: string }).cwd === WORKSPACE)).toBe(true);
    expect(commands.every((request) => !(request.body as { command: string }).command.includes(WORKSPACE))).toBe(true);
    await act(async () => cleanup());
    deactivate();
  });

  it("shows safe prerequisite onboarding and copies the fixed agent prompt", async () => {
    const token = workspaceToken(WORKSPACE);
    const { container, cleanup, deactivate } = await mountAt(`workspace/${token}`, { probe: "WASM_REPO_LENS_PROBE\t0\t1\n" });
    expect(container.textContent).toContain("Install ripgrep (rg) through an OpenHands agent.");
    const copy = [...container.querySelectorAll("button")].find((button) => button.textContent === "Copy agent setup prompt")!;
    await act(async () => copy.click());
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(expect.stringContaining("Do not modify any repository files"));
    expect(container.textContent).toContain("Setup prompt copied.");
    await act(async () => cleanup());
    deactivate();
  });

  it("renders workspace failures and cleans up DOM, requests, and Worker", async () => {
    const failed = await mountAt("", { failWorkspaces: true });
    expect(failed.container.textContent).toContain("Workspace discovery failed");
    await act(async () => failed.cleanup());
    expect(failed.container.childElementCount).toBe(0);
    expect(failed.worker.terminate).toHaveBeenCalledOnce();
    failed.deactivate();

    const about = await mountAt("about");
    expect(about.container.textContent).toContain("Source crosses one boundary, once.");
    await act(async () => about.cleanup());
    about.deactivate();
  });
});
