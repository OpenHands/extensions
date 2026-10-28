import { act } from "react";
import { describe, expect, it, vi } from "vitest";
import manifest from "../canvas-extension.json";
import { ROOT_ROUTE, normalizeRoute } from "./App";
import { activate } from "./extension";
import { fakeWorkers } from "./test-setup";
import type { CanvasHost, MountContext } from "./types";

function makeHost(overrides: Partial<CanvasHost> = {}) {
  let mount: ((context: MountContext) => void | (() => void)) | undefined;
  const unregister = vi.fn();
  const host: CanvasHost = {
    apiVersion: "1",
    extension: { name: "vite-showcase", version: "0.1.0", resolvedRef: "test-ref" },
    backend: { id: "backend-1", kind: "local", orgId: "org-1" },
    registerPage: vi.fn((_id, callback) => { mount = callback; return unregister; }),
    navigate: vi.fn(),
    ...overrides,
  };
  return { host, unregister, getMount: () => mount };
}

async function mountAt(path: string) {
  const fixture = makeHost();
  const deactivate = activate(fixture.host);
  const container = document.createElement("div");
  const navigate = vi.fn();
  let cleanup: void | (() => void);
  await act(async () => {
    cleanup = fixture.getMount()!({ container, path, navigate });
  });
  return { ...fixture, container, navigate, cleanup: cleanup!, deactivate };
}

describe("Vite Showcase activation", () => {
  it("registers every declared page and unregisters on deactivation", () => {
    const { host, unregister } = makeHost();
    const deactivate = activate(host);
    const pageIds = manifest.contributes.pages.map((page) => page.id);
    expect(pageIds).toEqual(["showcase"]);
    expect(host.registerPage).toHaveBeenCalledTimes(pageIds.length);
    expect(host.registerPage).toHaveBeenCalledWith("showcase", expect.any(Function));
    deactivate();
    expect(unregister).toHaveBeenCalledOnce();
  });

  it("rejects unsupported host API versions before registration", () => {
    const { host } = makeHost({ apiVersion: "2" });
    expect(() => activate(host)).toThrow("requires Canvas host API 1");
    expect(host.registerPage).not.toHaveBeenCalled();
  });
});

describe("Vite Showcase routing and lifecycle", () => {
  it.each([
    ["", "overview"], ["/", "overview"], ["overview", "overview"],
    ["/architecture/details", "architecture"], ["diagnostics", "diagnostics"], ["missing", "not-found"],
  ])("normalizes %s to %s", (path, route) => expect(normalizeRoute(path)).toBe(route));

  it("renders the root and navigates to a nested route", async () => {
    const { container, navigate, cleanup, deactivate } = await mountAt("");
    expect(container.textContent).toContain("Modern source.");
    const diagnostics = [...container.querySelectorAll("button")].find((button) => button.textContent === "Diagnostics");
    diagnostics?.click();
    expect(navigate).toHaveBeenCalledWith(`${ROOT_ROUTE}/diagnostics`);
    await act(async () => cleanup());
    deactivate();
  });

  it("renders diagnostics from host metadata and the Worker", async () => {
    const { container, cleanup, deactivate } = await mountAt("/diagnostics");
    await act(async () => { await Promise.resolve(); });
    expect(container.textContent).toContain("Version 1");
    expect(container.textContent).toContain("vite-showcase · 0.1.0");
    expect(container.textContent).toContain("local · backend-1");
    expect(container.textContent).toContain("/diagnostics");
    expect(container.textContent).toContain("fibonacci(32) = 2178309");
    await act(async () => cleanup());
    deactivate();
  });

  it("offers an explicit route back from an unknown nested path", async () => {
    const { container, navigate, cleanup, deactivate } = await mountAt("/does-not-exist");
    expect(container.textContent).toContain("That nested route is not in this bundle.");
    const back = [...container.querySelectorAll("button")].find((button) => button.textContent?.includes("Return to showcase root"));
    back?.click();
    expect(navigate).toHaveBeenCalledWith(ROOT_ROUTE);
    await act(async () => cleanup());
    deactivate();
  });

  it("aborts work and removes all mounted DOM during cleanup, then remounts", async () => {
    const removeListener = vi.spyOn(window, "removeEventListener");
    const { host, getMount } = makeHost();
    const deactivate = activate(host);
    const container = document.createElement("div");
    let firstCleanup: void | (() => void);
    await act(async () => { firstCleanup = getMount()!({ container, path: "architecture", navigate: vi.fn() }); });
    expect(container.querySelector("style[data-vite-showcase]")).toBeTruthy();
    const firstWorker = fakeWorkers.at(-1)!;
    await act(async () => firstCleanup!());
    expect(container.childElementCount).toBe(0);
    expect(firstWorker.terminate).toHaveBeenCalledOnce();
    expect(firstWorker.removeEventListener).toHaveBeenCalledWith("message", expect.any(Function));
    expect(removeListener).toHaveBeenCalledWith("keydown", expect.any(Function));
    let secondCleanup: void | (() => void);
    await act(async () => { secondCleanup = getMount()!({ container, path: "", navigate: vi.fn() }); });
    expect(container.textContent).toContain("Modern source.");
    await act(async () => secondCleanup!());
    expect(container.childElementCount).toBe(0);
    deactivate();
  });
});
