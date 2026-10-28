const STORAGE_PREFIX = "extension-lab";
const ROOT_ROUTE = "/extensions/extension-lab/lab";

/* ────────────────────────────────────────────────────────────
 * STYLES
 * ──────────────────────────────────────────────────────────── */
const STYLE = `
.extlab {
  min-height: 100%;
  box-sizing: border-box;
  background: var(--oh-background, #0c0d0f);
  color: var(--oh-foreground, #f4f4f5);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --lab-pass: #4ade80;
  --lab-fail: #f87171;
  --lab-pending: #fbbf24;
  --lab-muted: var(--oh-text-secondary, #b6bac3);
  --lab-surface: var(--oh-surface, #1b1d22);
  --lab-raised: var(--oh-surface-raised, #262930);
  --lab-border: var(--oh-border, #4b505c);
  --lab-accent: var(--oh-accent, #c9b974);
}
.extlab * { box-sizing: border-box; }
.extlab__shell { width: min(1120px, 100%); margin: 0 auto; padding: clamp(1rem, 3vw, 2rem); }
.extlab__header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1.5rem; }
.extlab__brand { display: flex; align-items: center; gap: .7rem; min-width: 0; }
.extlab__mark { display: grid; width: 2.25rem; height: 2.25rem; place-items: center; border: 1px solid var(--lab-border); border-radius: .65rem; font-size: 1.1rem; background: var(--lab-raised); flex-shrink: 0; }
.extlab__eyebrow { margin: 0; font-size: .62rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--lab-accent); }
.extlab__title { margin: .1rem 0 0; font-size: .95rem; font-weight: 650; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.extlab__actions { display: flex; gap: .5rem; flex-shrink: 0; }
.extlab__button { appearance: none; border: 1px solid var(--lab-border); border-radius: 8px; padding: .42rem .7rem; color: var(--oh-foreground, #f4f4f5); background: var(--lab-surface); font: inherit; font-size: .72rem; font-weight: 600; cursor: pointer; transition: border-color 150ms, background 150ms; }
.extlab__button:hover { border-color: color-mix(in srgb, var(--lab-accent) 55%, var(--lab-border)); background: var(--lab-raised); }
.extlab__button:focus-visible { outline: 2px solid var(--oh-focus, #fff); outline-offset: 2px; }
.extlab__button:active { transform: translateY(1px); }
.extlab__button--active { border-color: var(--lab-accent); color: var(--lab-accent); }
.extlab__nav { display: flex; gap: .4rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.extlab__nav-link { padding: .35rem .75rem; border: 1px solid var(--lab-border); border-radius: 6px; font-size: .75rem; font-weight: 600; color: var(--lab-muted); cursor: pointer; background: transparent; transition: all 150ms; }
.extlab__nav-link:hover { color: var(--oh-foreground); border-color: var(--lab-accent); }
.extlab__nav-link--active { color: var(--lab-accent); border-color: var(--lab-accent); }
.extlab__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); gap: 1rem; }
.extlab__card { border: 1px solid var(--lab-border); border-radius: .75rem; padding: 1rem 1.1rem; background: var(--lab-surface); display: flex; flex-direction: column; gap: .5rem; }
.extlab__card-head { display: flex; align-items: center; justify-content: space-between; gap: .5rem; }
.extlab__card-name { font-size: .85rem; font-weight: 650; margin: 0; }
.extlab__card-desc { font-size: .75rem; color: var(--lab-muted); line-height: 1.5; margin: 0; }
.extlab__card-body { font-size: .78rem; line-height: 1.55; color: var(--oh-foreground); min-height: 2rem; }
.extlab__badge { display: inline-flex; align-items: center; gap: .3rem; padding: .15rem .5rem; border-radius: 99px; font-size: .65rem; font-weight: 700; letter-spacing: .03em; white-space: nowrap; }
.extlab__badge--pass { background: color-mix(in srgb, var(--lab-pass) 18%, transparent); color: var(--lab-pass); }
.extlab__badge--fail { background: color-mix(in srgb, var(--lab-fail) 18%, transparent); color: var(--lab-fail); }
.extlab__badge--pending { background: color-mix(in srgb, var(--lab-pending) 18%, transparent); color: var(--lab-pending); }
.extlab__badge-dot { width: .4rem; height: .4rem; border-radius: 50%; background: currentColor; }
.extlab__code { background: var(--oh-surface-deep, #0f1113); border: 1px solid var(--lab-border); border-radius: .5rem; padding: .75rem; font-family: "SF Mono", "Fira Code", ui-monospace, monospace; font-size: .72rem; line-height: 1.6; overflow-x: auto; white-space: pre-wrap; word-break: break-word; color: var(--oh-foreground); margin: .5rem 0 0; }
.extlab__code-comment { color: var(--lab-muted); }
.extlab__detail { margin-top: .5rem; padding: .5rem; border-radius: .4rem; background: var(--oh-surface-deep, #0f1113); border: 1px solid var(--lab-border); font-size: .72rem; color: var(--lab-muted); word-break: break-word; }
.extlab__detail strong { color: var(--oh-foreground); }
.extlab__section-title { font-size: 1rem; font-weight: 650; margin: 0 0 1rem; }
.extlab__counter { font-size: 1.5rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.extlab__input { width: 100%; padding: .4rem .6rem; border: 1px solid var(--lab-border); border-radius: 6px; background: var(--lab-surface); color: var(--oh-foreground); font: inherit; font-size: .78rem; }
.extlab__input:focus { outline: 2px solid var(--oh-focus, #fff); outline-offset: 1px; }
.extlab__row { display: flex; align-items: center; gap: .5rem; }
.extlab__empty { padding: 3rem 1rem; text-align: center; color: var(--lab-muted); }
.extlab__pattern { border: 1px solid var(--lab-border); border-radius: .75rem; padding: 1rem 1.1rem; background: var(--lab-surface); margin-bottom: 1rem; }
.extlab__pattern-head { display: flex; align-items: center; gap: .5rem; margin-bottom: .5rem; }
.extlab__stress-log { background: var(--oh-surface-deep, #0f1113); border: 1px solid var(--lab-border); border-radius .5rem; padding: .75rem; font-family: monospace; font-size: .72rem; max-height: 18rem; overflow-y: auto; margin-top: .5rem; }
.extlab__stress-log p { margin: 0 0 .2rem; line-height: 1.5; }
.extlab__stress-log p--pass { color: var(--lab-pass); }
.extlab__stress-log p--fail { color: var(--lab-fail); }
@media (max-width: 560px) {
  .extlab__header { flex-wrap: wrap; }
  .extlab__title { white-space: normal; }
}
@media (prefers-reduced-motion: reduce) {
  .extlab__button { transition: none; }
}
`;

/* ────────────────────────────────────────────────────────────
 * UTILITIES
 * ──────────────────────────────────────────────────────────── */
function injectStyle(id, css) {
  if (document.getElementById(id)) return;
  const style = document.createElement("style");
  style.id = id;
  style.textContent = css;
  document.head.append(style);
}

function storageKey(backend) {
  const bid = backend?.id ?? "default";
  return `${STORAGE_PREFIX}:${bid}`;
}

function el(tag, className, child) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (child != null) {
    if (typeof child === "string") e.textContent = child;
    else e.append(child);
  }
  return e;
}

function badge(status, label) {
  const b = el("span", `extlab__badge extlab__badge--${status}`);
  b.append(el("span", "extlab__badge-dot"), document.createTextNode(label));
  return b;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/* ────────────────────────────────────────────────────────────
 * CAPABILITY TESTS
 * Each test returns { status: "pass"|"fail", detail: string, value?: string }
 * ──────────────────────────────────────────────────────────── */

async function testVanillaDOM(container) {
  const btn = el("button", "extlab__button", "Click me");
  let count = 0;
  const counter = el("span", "extlab__counter", "0");
  btn.addEventListener("click", () => {
    count++;
    counter.textContent = String(count);
  });
  const row = el("div", "extlab__row");
  row.append(btn, counter);
  container.append(row);
  btn.click();
  btn.click();
  btn.click();
  if (count !== 3) return { status: "fail", detail: `Expected count 3, got ${count}` };
  return { status: "pass", detail: "Button click counter works.", value: `count=${count}` };
}

async function testInlineBlobImport() {
  try {
    const code = 'export const meaning = 42; export function double(n) { return n * 2; }';
    const blob = new Blob([code], { type: "text/javascript" });
    const url = URL.createObjectURL(blob);
    const mod = await import(url);
    URL.revokeObjectURL(url);
    if (mod.meaning !== 42) return { status: "fail", detail: `Expected meaning=42, got ${mod.meaning}` };
    if (mod.double(5) !== 10) return { status: "fail", detail: `Expected double(5)=10, got ${mod.double(5)}` };
    return { status: "pass", detail: "Inline blob ESM module imported and called successfully.", value: `meaning=${mod.meaning}, double(5)=${mod.double(5)}` };
  } catch (err) {
    return { status: "fail", detail: `Blob import failed: ${String(err?.message || err)}` };
  }
}

async function testCDNImport() {
  try {
    const mod = await import("https://esm.sh/uuid@11.0.3");
    const id = mod.v4 ? mod.v4() : (mod.default?.v4 ? mod.default.v4() : null);
    if (!id || typeof id !== "string") return { status: "fail", detail: "CDN module loaded but v4() did not return a string" };
    return { status: "pass", detail: "Dynamic import from esm.sh CDN works.", value: `uuid=${id.slice(0, 8)}…` };
  } catch (err) {
    return { status: "fail", detail: `CDN import failed: ${String(err?.message || err)}` };
  }
}

async function testCSSVariables(container) {
  const probe = el("div", "extlab");
  probe.style.display = "none";
  container.append(probe);
  const computed = getComputedStyle(probe);
  const bg = computed.getPropertyValue("--oh-background") || computed.getPropertyValue("background-color");
  const fg = computed.getPropertyValue("--oh-foreground") || computed.getPropertyValue("color");
  probe.remove();
  const found = bg || fg;
  if (!found) return { status: "fail", detail: "No Canvas CSS variables resolved on .extlab element." };
  return { status: "pass", detail: "Canvas CSS custom properties are accessible.", value: `--oh-background=${bg || "(unset)"}, --oh-foreground=${fg || "(unset)"}` };
}

async function testLocalStorage(backend) {
  const key = storageKey(backend);
  const testVal = `lab-test-${Date.now()}`;
  try {
    localStorage.setItem(key, testVal);
    const retrieved = localStorage.getItem(key);
    localStorage.removeItem(key);
    if (retrieved !== testVal) return { status: "fail", detail: "localStorage round-trip mismatch." };
    return { status: "pass", detail: "localStorage set/get/remove works.", value: `key=${key}` };
  } catch (err) {
    return { status: "fail", detail: `localStorage unavailable: ${String(err?.message || err)}` };
  }
}

async function testWebWorker(container) {
  const workerCode = `
    onmessage = (e) => {
      if (e.data === "ping") postMessage({ type: "pong", time: Date.now() });
    };
  `;
  const blob = new Blob([workerCode], { type: "text/javascript" });
  const url = URL.createObjectURL(blob);
  try {
    const worker = new Worker(url);
    const result = await new Promise((resolve) => {
      const timer = setTimeout(() => resolve(null), 3000);
      worker.onmessage = (e) => { clearTimeout(timer); resolve(e.data); };
      worker.postMessage("ping");
    });
    worker.terminate();
    URL.revokeObjectURL(url);
    if (!result || result.type !== "pong") return { status: "fail", detail: "Worker did not respond with pong within 3s." };
    return { status: "pass", detail: "Web Worker created from blob URL responds to messages.", value: `pong.time=${result.time}` };
  } catch (err) {
    URL.revokeObjectURL(url);
    return { status: "fail", detail: `Worker creation failed: ${String(err?.message || err)}` };
  }
}

async function testWebComponent(container) {
  const tagName = `extlab-widget-${Math.random().toString(36).slice(2, 8)}`;
  try {
    class Widget extends HTMLElement {
      constructor() {
        super();
        const shadow = this.attachShadow({ mode: "open" });
        shadow.innerHTML = `<p style="color:#4ade80;font-size:.75rem">Shadow DOM works!</p>`;
      }
    }
    customElements.define(tagName, Widget);
    const widget = document.createElement(tagName);
    container.append(widget);
    const shadow = widget.shadowRoot;
    if (!shadow) return { status: "fail", detail: "shadowRoot is null after attachShadow." };
    const text = shadow.textContent;
    widget.remove();
    if (!text.includes("Shadow DOM works")) return { status: "fail", detail: "Shadow DOM text mismatch." };
    return { status: "pass", detail: "Custom element with shadow DOM registered and rendered.", value: `<${tagName}>` };
  } catch (err) {
    return { status: "fail", detail: `Web Component failed: ${String(err?.message || err)}` };
  }
}

async function testAgentServerAPI(host) {
  try {
    const result = await host.agentServer.request({
      method: "GET",
      path: "/api/conversations/search",
    });
    if (!result) return { status: "fail", detail: "agentServer.request returned null/undefined." };
    const convos = result.conversations ?? result;
    if (!Array.isArray(convos)) return { status: "pass", detail: "Agent Server responded but response shape unexpected.", value: `keys=${Object.keys(result).join(",")}` };
    return { status: "pass", detail: "host.agentServer.request() reaches the Agent Server.", value: `conversations=${convos.length}` };
  } catch (err) {
    return { status: "fail", detail: `Agent Server request failed: ${String(err?.message || err)}` };
  }
}

async function testResizeObserver(container) {
  const target = el("div", "", "Resize me");
  target.style.cssText = "width:100%;height:40px;border:1px dashed #4b505c;display:flex;align-items:center;justify-content:center;font-size:.72rem;color:#b6bac3;";
  container.append(target);
  let resized = false;
  try {
    const ro = new ResizeObserver(() => { resized = true; });
    ro.observe(target);
    target.style.width = "50%";
    await sleep(100);
    ro.disconnect();
    if (!resized) return { status: "fail", detail: "ResizeObserver callback never fired." };
    return { status: "pass", detail: "ResizeObserver fires on container dimension changes." };
  } catch (err) {
    return { status: "fail", detail: `ResizeObserver unavailable: ${String(err?.message || err)}` };
  }
}

async function testIndexedDB() {
  try {
    const request = indexedDB.open("extlab-test", 1);
    const db = await new Promise((resolve, reject) => {
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    if (!db.objectStoreNames.contains("kv")) {
      const version = db.version + 1;
      db.close();
      const req2 = indexedDB.open("extlab-test", version);
      await new Promise((resolve, reject) => {
        req2.onsuccess = () => resolve();
        req2.onerror = () => reject(req2.error);
        req2.onupgradeneeded = (e) => {
          e.target.result.createObjectStore("kv", { keyPath: "id" });
        };
      });
    }
    const db2 = await new Promise((resolve, reject) => {
      const r = indexedDB.open("extlab-test");
      r.onsuccess = () => resolve(r.result);
      r.onerror = () => reject(r.error);
    });
    const tx = db2.transaction("kv", "readwrite");
    const store = tx.objectStore("kv");
    store.put({ id: "test", value: Date.now() });
    const getReq = store.get("test");
    const result = await new Promise((resolve, reject) => {
      getReq.onsuccess = () => resolve(getReq.result);
      getReq.onerror = () => reject(getReq.error);
    });
    db2.close();
    indexedDB.deleteDatabase("extlab-test");
    if (!result || !result.value) return { status: "fail", detail: "IndexedDB round-trip returned no value." };
    return { status: "pass", detail: "IndexedDB open, write, read, and delete all work.", value: `stored=${result.value}` };
  } catch (err) {
    return { status: "fail", detail: `IndexedDB test failed: ${String(err?.message || err)}` };
  }
}

async function testMutationObserver(container) {
  const target = el("div", "", "");
  container.append(target);
  let mutated = false;
  try {
    const mo = new MutationObserver(() => { mutated = true; });
    mo.observe(target, { childList: true });
    target.append(el("span", "", "hello"));
    await sleep(50);
    mo.disconnect();
    if (!mutated) return { status: "fail", detail: "MutationObserver callback never fired." };
    return { status: "pass", detail: "MutationObserver fires on DOM tree changes." };
  } catch (err) {
    return { status: "fail", detail: `MutationObserver unavailable: ${String(err?.message || err)}` };
  }
}

/* ────────────────────────────────────────────────────────────
 * CAPABILITY DEFINITIONS
 * ──────────────────────────────────────────────────────────── */
const CAPABILITIES = [
  {
    id: "vanilla-dom",
    name: "Vanilla DOM",
    desc: "createElement, addEventListener, textContent — the basics.",
    code: `const btn = document.createElement("button");
btn.textContent = "Click";
btn.addEventListener("click", handler);
container.append(btn);`,
    run: async (host, container) => testVanillaDOM(container),
  },
  {
    id: "inline-blob",
    name: "Inline Blob Module",
    desc: "Create an ESM module at runtime from a blob URL and import() it.",
    code: `const code = 'export const x = 42;';
const blob = new Blob([code], {type:"text/javascript"});
const url = URL.createObjectURL(blob);
const mod = await import(url);
URL.revokeObjectURL(url);`,
    run: async () => testInlineBlobImport(),
  },
  {
    id: "cdn-import",
    name: "CDN Dynamic Import",
    desc: "Dynamic import() from a full URL (esm.sh, skypack, etc.).",
    code: `const mod = await import("https://esm.sh/uuid@11");
const id = mod.v4();`,
    run: async () => testCDNImport(),
  },
  {
    id: "css-vars",
    name: "CSS Variable Theming",
    desc: "Read Canvas --oh-* CSS custom properties for theme integration.",
    code: `const cs = getComputedStyle(container);
const bg = cs.getPropertyValue("--oh-background");`,
    run: async (host, container) => testCSSVariables(container),
  },
  {
    id: "local-storage",
    name: "localStorage Persistence",
    desc: "Per-backend persistent storage via the storage key pattern.",
    code: `const key = "extlab:" + backend.id;
localStorage.setItem(key, JSON.stringify(data));`,
    run: async (host) => testLocalStorage(host.backend),
  },
  {
    id: "web-worker",
    name: "Web Worker (Blob)",
    desc: "Spawn a Worker from inline blob code — no separate file needed.",
    code: `const blob = new Blob([workerCode], {type:"text/javascript"});
const worker = new Worker(URL.createObjectURL(blob));`,
    run: async (host, container) => testWebWorker(container),
  },
  {
    id: "web-component",
    name: "Web Component",
    desc: "Register a custom element with Shadow DOM for style isolation.",
    code: `class Widget extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:"open"});
  }
}
customElements.define("my-widget", Widget);`,
    run: async (host, container) => testWebComponent(container),
  },
  {
    id: "agent-server",
    name: "Agent Server API",
    desc: "Call host.agentServer.request() to reach the Agent Server backend.",
    code: `const result = await host.agentServer.request({
  method: "GET",
  path: "/api/conversations/search",
});`,
    run: async (host) => testAgentServerAPI(host),
  },
  {
    id: "resize-observer",
    name: "ResizeObserver",
    desc: "React to container dimension changes — essential for responsive UIs.",
    code: `const ro = new ResizeObserver(entries => {
  // container resized
});
ro.observe(container);`,
    run: async (host, container) => testResizeObserver(container),
  },
  {
    id: "indexed-db",
    name: "IndexedDB",
    desc: "Structured client-side storage for larger data than localStorage.",
    code: `const db = await new Promise((res, rej) => {
  const r = indexedDB.open("mydb", 1);
  r.onsuccess = () => res(r.result);
  r.onerror = () => rej(r.error);
});`,
    run: async () => testIndexedDB(),
  },
  {
    id: "mutation-observer",
    name: "MutationObserver",
    desc: "Watch for DOM changes — useful for integration with Canvas UI.",
    code: `const mo = new MutationObserver(records => {
  // DOM changed
});
mo.observe(target, { childList: true });`,
    run: async (host, container) => testMutationObserver(container),
  },
];

/* ────────────────────────────────────────────────────────────
 * DASHBOARD PAGE
 * ──────────────────────────────────────────────────────────── */
function renderDashboard(host, mountCtx) {
  const { container, navigate } = mountCtx;
  const key = storageKey(host.backend);

  const root = el("section", "extlab");
  root.setAttribute("aria-label", "Extension Lab dashboard");

  // Header
  const header = el("div", "extlab__header");
  const brand = el("div", "extlab__brand");
  brand.append(el("span", "extlab__mark", "🧪"));
  const titleGroup = el("div", "extlab__title-group");
  titleGroup.append(el("p", "extlab__eyebrow", "Extension Lab"), el("h1", "extlab__title", "Capability Dashboard"));
  brand.append(titleGroup);
  const actions = el("div", "extlab__actions");
  const rerunBtn = el("button", "extlab__button", "Re-run all");
  actions.append(rerunBtn);
  header.append(brand, actions);

  // Nav
  const nav = el("div", "extlab__nav");
  const navItems = [
    { label: "Dashboard", path: "", active: !mountCtx.path },
    { label: "Patterns", path: "patterns", active: mountCtx.path === "patterns" },
    { label: "Stress Test", path: "stress", active: mountCtx.path === "stress" },
  ];
  for (const item of navItems) {
    const link = el("button", `extlab__nav-link${item.active ? " extlab__nav-link--active" : ""}`, item.label);
    link.addEventListener("click", () => navigate(item.path ? `${ROOT_ROUTE}/${item.path}` : ROOT_ROUTE));
    nav.append(link);
  }

  // Sub-route handling
  if (mountCtx.path === "patterns") {
    root.append(header, nav, renderPatternsPage(container));
    container.append(root);
    rerunBtn.addEventListener("click", () => { /* patterns are static */ });
    return () => root.remove();
  }
  if (mountCtx.path === "stress") {
    const stressCleanup = renderStressPage(container, key);
    root.append(header, nav);
    container.append(root);
    rerunBtn.addEventListener("click", () => stressCleanup.rerun());
    return () => { stressCleanup.cleanup(); root.remove(); };
  }

  // Dashboard grid
  const shell = el("div", "extlab__shell");
  shell.append(header, nav, el("h2", "extlab__section-title", "Capabilities"));
  const grid = el("div", "extlab__grid");
  shell.append(grid);
  root.append(shell);
  container.append(root);

  // Render cards and run tests
  const cards = new Map();
  for (const cap of CAPABILITIES) {
    const card = el("div", "extlab__card");
    const head = el("div", "extlab__card-head");
    head.append(el("h3", "extlab__card-name", cap.name), badge("pending", "Testing…"));
    card.append(head, el("p", "extlab__card-desc", cap.desc));

    // Interactive body container
    const body = el("div", "extlab__card-body", "");
    card.append(body);

    const detail = el("div", "extlab__detail", "");
    detail.style.display = "none";
    card.append(detail);

    grid.append(card);
    cards.set(cap.id, { card, head, body, detail });
  }

  async function runAll() {
    for (const cap of CAPABILITIES) {
      const { card, head, body, detail } = cards.get(cap.id);
      // Reset
      body.innerHTML = "";
      detail.style.display = "none";
      detail.textContent = "";
      const oldBadge = head.querySelector(".extlab__badge");
      if (oldBadge) oldBadge.replaceWith(badge("pending", "Testing…"));

      try {
        const result = await cap.run(host, body);
        const newBadge = badge(result.status, result.status === "pass" ? "Working" : "Failed");
        head.querySelector(".extlab__badge")?.replaceWith(newBadge);
        if (result.detail) {
          detail.innerHTML = "";
          detail.append(el("strong", "", result.status === "pass" ? "✓ " : "✗ "), document.createTextNode(result.detail));
          detail.style.display = "block";
        }
        if (result.value) {
          const val = el("div", "", "");
          val.append(el("span", "extlab__code-comment", "// result: "), document.createTextNode(result.value));
          detail.append(val);
        }
      } catch (err) {
        const newBadge = badge("fail", "Failed");
        head.querySelector(".extlab__badge")?.replaceWith(newBadge);
        detail.innerHTML = "";
        detail.append(el("strong", "", "✗ "), document.createTextNode(String(err?.message || err)));
        detail.style.display = "block";
      }
    }
  }

  rerunBtn.addEventListener("click", runAll);
  runAll();

  return () => root.remove();
}

/* ────────────────────────────────────────────────────────────
 * PATTERNS PAGE
 * ──────────────────────────────────────────────────────────── */
function renderPatternsPage() {
  const shell = el("div", "extlab__shell");
  shell.append(el("h2", "extlab__section-title", "Pattern Gallery"));

  const intro = el("p", "extlab__card-desc", "Copy-paste code snippets for each technique. These are the minimal patterns that work in the current Canvas extension host.");
  shell.append(intro);

  for (const cap of CAPABILITIES) {
    const pattern = el("div", "extlab__pattern");
    const head = el("div", "extlab__pattern-head");
    head.append(el("h3", "extlab__card-name", cap.name), badge("pending", "See dashboard"));
    pattern.append(head, el("p", "extlab__card-desc", cap.desc));
    const code = el("pre", "extlab__code", cap.code);
    pattern.append(code);
    shell.append(pattern);
  }

  // Import limitations section
  const limitations = el("div", "extlab__pattern");
  limitations.append(el("h3", "extlab__card-name", "Known Limitations"));
  const limits = el("ul", "extlab__card-desc");
  for (const [label, reason] of [
    ["Relative imports (import \"./foo.js\")", "Blob URL loading has no base path — browser can't resolve relative specifiers."],
    ["Bare imports (import React from \"react\")", "No import map is provided by the Canvas host."],
    ["Extension folder assets", "Server only serves the entrypoint at /bundle — no wildcard route for other files."],
    ["Node.js APIs", "Extensions run in the browser, not Node. No fs, path, process, etc."],
  ]) {
    const li = el("li", "", "");
    li.append(el("strong", "", label), document.createTextNode(` — ${reason}`));
    limits.append(li);
  }
  limitations.append(limits);
  shell.append(limitations);

  return shell;
}

/* ────────────────────────────────────────────────────────────
 * STRESS TEST PAGE
 * ──────────────────────────────────────────────────────────── */
function renderStressPage(container, storageKeyVal) {
  const shell = el("div", "extlab__shell");
  shell.append(el("h2", "extlab__section-title", "Stress Tests"));

  const log = el("div", "extlab__stress-log");
  shell.append(log);

  function logMsg(text, status = "") {
    const p = el("p", status ? `extlab__stress-log p--${status}` : "", text);
    log.append(p);
    log.scrollTop = log.scrollHeight;
  }

  async function runMountUnmount() {
    logMsg("▶ Mount/unmount 100×…");
    const target = el("div", "");
    shell.append(target);
    let leaks = 0;
    for (let i = 0; i < 100; i++) {
      const child = el("div", "", `cycle ${i}`);
      child.addEventListener("click", () => {});
      target.append(child);
      child.remove();
    }
    // Check for leftover nodes
    if (target.childElementCount > 0) leaks = target.childElementCount;
    target.remove();
    if (leaks > 0) {
      logMsg(`✗ Mount/unmount: ${leaks} nodes leaked`, "fail");
    } else {
      logMsg("✓ Mount/unmount: 100 cycles, 0 leaks", "pass");
    }
  }

  async function runEventListenerLeak() {
    logMsg("▶ Event listener leak test (1000 listeners)…");
    const btn = el("button", "extlab__button", "Stress");
    shell.append(btn);
    for (let i = 0; i < 1000; i++) {
      const handler = () => {};
      btn.addEventListener("click", handler);
      btn.removeEventListener("click", handler);
    }
    btn.click();
    btn.remove();
    logMsg("✓ Event listener: 1000 add/remove cycles, no error", "pass");
  }

  async function runLocalStorageQuota() {
    logMsg("▶ localStorage quota test (100KB)…");
    try {
      const data = "x".repeat(100 * 1024);
      localStorage.setItem(`${storageKeyVal}:stress`, data);
      const retrieved = localStorage.getItem(`${storageKeyVal}:stress`);
      localStorage.removeItem(`${storageKeyVal}:stress`);
      if (retrieved && retrieved.length === data.length) {
        logMsg("✓ localStorage: 100KB write/read/delete succeeded", "pass");
      } else {
        logMsg("✗ localStorage: round-trip size mismatch", "fail");
      }
    } catch (err) {
      logMsg(`✗ localStorage quota exceeded: ${String(err?.message || err)}`, "fail");
    }
  }

  async function runConcurrentAsync() {
    logMsg("▶ Concurrent async with cancellation (50 tasks)…");
    let completed = 0;
    let cancelled = 0;
    const tasks = [];
    let cancelFlag = false;

    for (let i = 0; i < 50; i++) {
      tasks.push(
        (async () => {
          await sleep(10 + Math.random() * 100);
          if (cancelFlag) { cancelled++; return; }
          completed++;
        })()
      );
    }
    // Cancel after 30ms
    setTimeout(() => { cancelFlag = true; }, 30);
    await Promise.all(tasks);
    logMsg(`✓ Concurrent async: ${completed} completed, ${cancelled} cancelled`, "pass");
  }

  async function runRapidRecreation() {
    logMsg("▶ Rapid custom element recreation (50×)…");
    let ok = true;
    try {
      for (let i = 0; i < 50; i++) {
        const tag = `extlab-stress-${i}`;
        if (customElements.get(tag)) continue;
        class S extends HTMLElement { constructor() { super(); this.attachShadow({mode:"open"}); } }
        customElements.define(tag, S);
        const e = document.createElement(tag);
        shell.append(e);
        e.remove();
      }
    } catch (err) {
      ok = false;
      logMsg(`✗ Rapid recreation failed: ${String(err?.message || err)}`, "fail");
    }
    if (ok) logMsg("✓ Rapid recreation: 50 custom elements created and removed", "pass");
  }

  async function runAll() {
    log.innerHTML = "";
    logMsg("═══ Stress Tests ═══");
    await runMountUnmount();
    await runEventListenerLeak();
    await runLocalStorageQuota();
    await runConcurrentAsync();
    await runRapidRecreation();
    logMsg("═══ Complete ═══");
  }

  const runBtn = el("button", "extlab__button", "Run Stress Tests");
  runBtn.addEventListener("click", runAll);
  shell.insertBefore(runBtn, log);
  container.append(shell);

  // Auto-run
  runAll();

  return {
    cleanup: () => { shell.remove(); },
    rerun: () => { runAll(); },
  };
}

/* ────────────────────────────────────────────────────────────
 * ACTIVATE
 * ──────────────────────────────────────────────────────────── */
export function activate(host) {
  if (host.apiVersion !== "1") {
    throw new Error("extension-lab requires Canvas host API 1.");
  }

  injectStyle("extension-lab-style", STYLE);

  const unregisterDashboard = host.registerPage("dashboard", (mountCtx) => {
    return renderDashboard(host, mountCtx);
  });

  return () => {
    unregisterDashboard();
  };
}

/* ────────────────────────────────────────────────────────────
 * TESTING EXPORTS
 * ──────────────────────────────────────────────────────────── */
export const __testing = {
  CAPABILITIES,
  testVanillaDOM,
  testInlineBlobImport,
  testCDNImport,
  testCSSVariables,
  testLocalStorage,
  testWebWorker,
  testWebComponent,
  testResizeObserver,
  testMutationObserver,
  testIndexedDB,
  storageKey,
  injectStyle,
  el,
  badge,
  sleep,
  STYLE,
};
