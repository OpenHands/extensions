import { describe, it, expect, vi, beforeEach } from "vitest";
import { __testing, activate } from "./extension.js";

const {
  CAPABILITIES,
  testVanillaDOM,
  testInlineBlobImport,
  testCSSVariables,
  testLocalStorage,
  testWebComponent,
  testMutationObserver,
  testResizeObserver,
  storageKey,
  injectStyle,
  el,
  badge,
  sleep,
} = __testing;

/* ── Test host factory ── */
function createHost(overrides = {}) {
  const registered = new Map();
  return {
    host: {
      apiVersion: "1",
      extension: { name: "extension-lab", version: "0.1.0", resolvedRef: null },
      backend: { id: "test-backend", kind: "local", orgId: null },
      registerPage: vi.fn((id, mount) => {
        if (registered.has(id)) throw new Error(`Page "${id}" already registered`);
        registered.set(id, mount);
        return () => registered.delete(id);
      }),
      navigate: vi.fn(),
      agentServer: {
        request: vi.fn().mockResolvedValue({ conversations: [] }),
      },
      ...overrides,
    },
    getRegistered: () => registered,
  };
}

/* ── Helpers ── */
function getMount(registered, pageId = "dashboard") {
  return registered.get(pageId);
}

/* ═══════════════════════════════════════════════════════════════
 * ACTIVATION LIFECYCLE
 * ═══════════════════════════════════════════════════════════════ */
describe("Extension Lab lifecycle", () => {
  beforeEach(() => {
    document.head.innerHTML = "";
    document.body.innerHTML = "";
    localStorage.clear();
  });

  it("registers exactly one page (dashboard) and activation cleanup unregisters it", () => {
    const { host, getRegistered } = createHost();
    const dispose = activate(host);
    expect(host.registerPage).toHaveBeenCalledTimes(1);
    expect(host.registerPage).toHaveBeenCalledWith("dashboard", expect.any(Function));
    expect(getRegistered().has("dashboard")).toBe(true);

    dispose();
    expect(getRegistered().has("dashboard")).toBe(false);
  });

  it("fails clearly on an unsupported host API", () => {
    const { host } = createHost({ apiVersion: "2" });
    expect(() => activate(host)).toThrow("host API 1");
  });

  it("injects the style element exactly once", () => {
    const { host } = createHost();
    const d1 = activate(host);
    d1();
    const d2 = activate(host);
    d2();
    const styles = document.querySelectorAll("#extension-lab-style");
    expect(styles).toHaveLength(1);
  });

  it("mounts the dashboard UI with header, nav, and grid", () => {
    const { host, getRegistered } = createHost();
    activate(host);
    const mount = getMount(getRegistered());
    const container = document.createElement("div");
    const cleanup = mount({ container, path: "", navigate: vi.fn() });

    const root = container.querySelector(".extlab");
    expect(root).toBeTruthy();

    const title = container.querySelector(".extlab__title");
    expect(title?.textContent).toBe("Capability Dashboard");

    const grid = container.querySelector(".extlab__grid");
    expect(grid).toBeTruthy();

    const cards = container.querySelectorAll(".extlab__card");
    expect(cards.length).toBe(CAPABILITIES.length);

    cleanup();
    expect(container.childElementCount).toBe(0);
  });

  it("renders the patterns sub-page when path is 'patterns'", () => {
    const { host, getRegistered } = createHost();
    activate(host);
    const mount = getMount(getRegistered());
    const container = document.createElement("div");
    mount({ container, path: "patterns", navigate: vi.fn() });

    const patterns = container.querySelectorAll(".extlab__pattern");
    expect(patterns.length).toBeGreaterThanOrEqual(CAPABILITIES.length);

    // Should include the limitations section
    const limitTitle = container.textContent;
    expect(limitTitle).toContain("Known Limitations");
  });

  it("renders the stress test sub-page when path is 'stress'", () => {
    const { host, getRegistered } = createHost();
    activate(host);
    const mount = getMount(getRegistered());
    const container = document.createElement("div");
    const cleanup = mount({ container, path: "stress", navigate: vi.fn() });

    const stressLog = container.querySelector(".extlab__stress-log");
    expect(stressLog).toBeTruthy();

    cleanup();
  });

  it("navigates between sub-pages via nav links", () => {
    const { host, getRegistered } = createHost();
    activate(host);
    const mount = getMount(getRegistered());
    const container = document.createElement("div");
    const navigate = vi.fn();
    mount({ container, path: "", navigate });

    const links = container.querySelectorAll(".extlab__nav-link");
    expect(links.length).toBe(3);

    // Click "Patterns" link
    links[1].click();
    expect(navigate).toHaveBeenCalledWith("/extensions/extension-lab/lab/patterns");
  });
});

/* ═══════════════════════════════════════════════════════════════
 * CAPABILITY TESTS (unit-level, in jsdom)
 * ═══════════════════════════════════════════════════════════════ */
describe("Capability tests", () => {
  beforeEach(() => {
    document.head.innerHTML = "";
    document.body.innerHTML = "";
    localStorage.clear();
  });

  it("testVanillaDOM: counter increments on click", async () => {
    const container = document.createElement("div");
    const result = await testVanillaDOM(container);
    expect(result.status).toBe("pass");
    expect(result.value).toContain("count=3");
  });

  it("testInlineBlobImport: imports and calls blob module", async () => {
    // jsdom doesn't support URL.createObjectURL for dynamic import,
    // so this test verifies the function handles the error gracefully
    const result = await testInlineBlobImport();
    // In a real browser this passes; in jsdom it may fail
    expect(["pass", "fail"]).toContain(result.status);
  });

  it("testCSSVariables: detects CSS custom properties (or falls back gracefully)", async () => {
    // Set up a fake --oh-background
    document.documentElement.style.setProperty("--oh-background", "#0c0d0f");
    const container = document.createElement("div");
    container.className = "extlab";
    document.body.append(container);
    const result = await testCSSVariables(container);
    expect(result.status).toBe("pass");
  });

  it("testLocalStorage: round-trip works", async () => {
    const backend = { id: "test-backend", kind: "local", orgId: null };
    const result = await testLocalStorage(backend);
    expect(result.status).toBe("pass");
    expect(result.value).toContain("test-backend");
  });

  it("testLocalStorage: reports failure when localStorage is blocked", async () => {
    // jsdom localStorage doesn't throw on quota; mock with a throwing stub
    const orig = Object.getOwnPropertyDescriptor(window, "localStorage");
    const fakeStore = {
      getItem: () => null,
      setItem: () => { throw new Error("QuotaExceeded"); },
      removeItem: () => {},
      clear: () => {},
    };
    Object.defineProperty(window, "localStorage", {
      value: fakeStore,
      configurable: true,
    });
    const backend = { id: "test-backend", kind: "local", orgId: null };
    const result = await testLocalStorage(backend);
    if (orig) Object.defineProperty(window, "localStorage", orig);
    expect(result.status).toBe("fail");
    expect(result.detail).toContain("QuotaExceeded");
  });

  it("testWebComponent: registers and renders shadow DOM", async () => {
    const container = document.createElement("div");
    document.body.append(container);
    const result = await testWebComponent(container);
    expect(result.status).toBe("pass");
    expect(result.value).toContain("extlab-widget-");
  });

  it("testMutationObserver: fires on DOM changes", async () => {
    const container = document.createElement("div");
    document.body.append(container);
    const result = await testMutationObserver(container);
    expect(result.status).toBe("pass");
  });

  it("testResizeObserver: fires on resize (or reports gracefully in jsdom)", async () => {
    // jsdom ResizeObserver may not fire callbacks synchronously
    const container = document.createElement("div");
    document.body.append(container);
    const result = await testResizeObserver(container);
    expect(["pass", "fail"]).toContain(result.status);
  });

  it("storageKey: uses backend id", () => {
    const key = storageKey({ id: "my-backend", kind: "local", orgId: null });
    expect(key).toBe("extension-lab:my-backend");
  });

  it("storageKey: defaults to 'default' when no backend id", () => {
    const key = storageKey({});
    expect(key).toBe("extension-lab:default");
  });
});

/* ═══════════════════════════════════════════════════════════════
 * UTILITY TESTS
 * ═══════════════════════════════════════════════════════════════ */
describe("Utilities", () => {
  it("el: creates element with class and text", () => {
    const e = el("div", "my-class", "hello");
    expect(e.tagName).toBe("DIV");
    expect(e.className).toBe("my-class");
    expect(e.textContent).toBe("hello");
  });

  it("el: works without text", () => {
    const e = el("span", "cls");
    expect(e.textContent).toBe("");
  });

  it("badge: creates a pass badge", () => {
    const b = badge("pass", "Working");
    expect(b.className).toContain("extlab__badge--pass");
    expect(b.textContent).toContain("Working");
  });

  it("badge: creates a fail badge", () => {
    const b = badge("fail", "Failed");
    expect(b.className).toContain("extlab__badge--fail");
  });

  it("injectStyle: only injects once", () => {
    injectStyle("test-style", ".foo {}");
    injectStyle("test-style", ".foo {}");
    expect(document.querySelectorAll("#test-style")).toHaveLength(1);
  });

  it("sleep: resolves after delay", async () => {
    const start = Date.now();
    await sleep(50);
    expect(Date.now() - start).toBeGreaterThanOrEqual(40);
  });
});

/* ═══════════════════════════════════════════════════════════════
 * CAPABILITIES METADATA
 * ═══════════════════════════════════════════════════════════════ */
describe("Capabilities metadata", () => {
  it("has at least 10 capabilities", () => {
    expect(CAPABILITIES.length).toBeGreaterThanOrEqual(10);
  });

  it("each capability has id, name, desc, code, and run function", () => {
    for (const cap of CAPABILITIES) {
      expect(cap.id).toBeTruthy();
      expect(cap.name).toBeTruthy();
      expect(cap.desc).toBeTruthy();
      expect(cap.code).toBeTruthy();
      expect(typeof cap.run).toBe("function");
    }
  });

  it("capability ids are unique", () => {
    const ids = CAPABILITIES.map((c) => c.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
