import { act } from "react";
import { describe, expect, it, vi } from "vitest";
import manifest from "../canvas-extension.json";
import { DEFAULT_QUERY, ROOT_ROUTE, normalizeRoute } from "./App";
import { activate } from "./extension";
import { failNextInitialization, fakeWorkers } from "./test-setup";
import type { CanvasHost, MountContext } from "./types";

function makeHost(overrides: Partial<CanvasHost> = {}) {
  let mount: ((context: MountContext) => void | (() => void)) | undefined;
  const unregister = vi.fn();
  const host: CanvasHost = {
    apiVersion: "1",
    extension: { name: "browser-sql-lab", version: "0.1.0", resolvedRef: "test-ref" },
    backend: { id: "backend/local", kind: "local", orgId: "org-1" },
    registerPage: vi.fn((_id, callback) => { mount = callback; return unregister; }),
    navigate: vi.fn(),
    ...overrides,
  };
  return { host, unregister, getMount: () => mount };
}

async function flush() {
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
}

async function mountAt(path: string) {
  const fixture = makeHost();
  const deactivate = activate(fixture.host);
  const container = document.createElement("div");
  const navigate = vi.fn();
  let cleanup: void | (() => void);
  await act(async () => { cleanup = fixture.getMount()!({ container, path, navigate }); });
  await flush();
  return { ...fixture, container, navigate, cleanup: cleanup!, deactivate, worker: fakeWorkers.at(-1)! };
}

describe("Browser SQL Lab activation", () => {
  it("registers exactly every declared page and unregisters on deactivation", () => {
    const { host, unregister } = makeHost();
    const deactivate = activate(host);
    expect(manifest.contributes.pages.map((page) => page.id)).toEqual(["sql-lab"]);
    expect(host.registerPage).toHaveBeenCalledOnce();
    expect(host.registerPage).toHaveBeenCalledWith("sql-lab", expect.any(Function));
    deactivate();
    expect(unregister).toHaveBeenCalledOnce();
  });

  it("rejects unsupported host API versions before registration", () => {
    const { host } = makeHost({ apiVersion: "2" });
    expect(() => activate(host)).toThrow("requires Canvas host API 1");
    expect(host.registerPage).not.toHaveBeenCalled();
  });
});

describe("Browser SQL Lab routing and UI", () => {
  it.each([
    ["", "lab"], ["/", "lab"], ["lab/details", "lab"], ["/about", "about"], ["missing", "not-found"],
  ])("normalizes %s to %s", (path, route) => expect(normalizeRoute(path)).toBe(route));

  it("initializes the backend-scoped namespace and navigates nested routes", async () => {
    const { container, navigate, cleanup, deactivate, worker } = await mountAt("");
    expect(container.textContent).toContain("SQL editor");
    expect(container.querySelector('[data-testid="database-namespace"]')?.textContent).toBe("browser-sql-lab::backend%2Flocal");
    expect(worker.requests).toContainEqual({ id: 1, type: "init", namespace: "browser-sql-lab::backend%2Flocal" });
    const about = [...container.querySelectorAll("button")].find((button) => button.textContent === "About");
    about?.click();
    expect(navigate).toHaveBeenCalledWith(`${ROOT_ROUTE}/about`);
    await act(async () => cleanup());
    deactivate();
  });

  it("renders query results and propagates actionable SQL errors", async () => {
    const { container, cleanup, deactivate } = await mountAt("");
    await act(async () => { (container.querySelector('[data-testid="run-query"]') as HTMLButtonElement).click(); });
    await flush();
    expect(container.textContent).toContain("Ursula K. Le Guin");
    expect(container.textContent).toContain("Query completed and browser-local changes were saved.");

    const editor = container.querySelector("textarea")!;
    await act(async () => {
      const valueSetter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!;
      valueSetter.call(editor, "SELECT * FROM missing_table");
      editor.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await act(async () => { (container.querySelector('[data-testid="run-query"]') as HTMLButtonElement).click(); });
    await flush();
    expect(container.textContent).toContain("no such table: missing_table");
    await act(async () => cleanup());
    deactivate();
  });

  it("requires confirmation, resets the database, and clears results", async () => {
    const { container, cleanup, deactivate, worker } = await mountAt("");
    const reset = [...container.querySelectorAll("button")].find((button) => button.textContent === "Reset")!;
    await act(async () => reset.click());
    expect(container.textContent).toContain("Reset this backend’s database?");
    await act(async () => { (container.querySelector('[data-testid="confirm-reset"]') as HTMLButtonElement).click(); });
    await flush();
    expect(worker.requests.some((request) => request.type === "reset")).toBe(true);
    expect(container.textContent).toContain("Database reset complete");
    await act(async () => cleanup());
    deactivate();
  });

  it("renders startup errors with a retry action", async () => {
    failNextInitialization("IndexedDB is unavailable. Allow site storage for Canvas, then reload the App.");
    const fixture = makeHost();
    const deactivate = activate(fixture.host);
    const container = document.createElement("div");
    let cleanup: void | (() => void);
    await act(async () => { cleanup = fixture.getMount()!({ container, path: "", navigate: vi.fn() }); });
    await flush();
    expect(container.textContent).toContain("Browser SQL Lab could not start.");
    expect(container.textContent).toContain("Allow site storage for Canvas");
    const retry = [...container.querySelectorAll("button")].find((button) => button.textContent === "Try initialization again")!;
    await act(async () => retry.click());
    await flush();
    expect(container.textContent).toContain("SQL editor");
    await act(async () => cleanup!());
    deactivate();
  });

  it("cleans up DOM, aborts RPC, terminates the Worker, and supports remount", async () => {
    const fixture = makeHost();
    const deactivate = activate(fixture.host);
    const container = document.createElement("div");
    let cleanup: void | (() => void);
    await act(async () => { cleanup = fixture.getMount()!({ container, path: "", navigate: vi.fn() }); });
    await flush();
    const firstWorker = fakeWorkers.at(-1)!;
    expect(container.textContent).toContain("SQL editor");
    await act(async () => cleanup!());
    expect(container.childElementCount).toBe(0);
    expect(firstWorker.terminate).toHaveBeenCalledOnce();
    expect(firstWorker.removeEventListener).toHaveBeenCalledWith("message", expect.any(Function));
    let secondCleanup: void | (() => void);
    await act(async () => { secondCleanup = fixture.getMount()!({ container, path: "about", navigate: vi.fn() }); });
    await flush();
    expect(container.textContent).toContain("A real database, folded into one file.");
    await act(async () => secondCleanup!());
    deactivate();
  });

  it("ships a meaningful starter query", () => {
    expect(DEFAULT_QUERY).toContain("GROUP BY author");
  });
});
