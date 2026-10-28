import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import process from "node:process";
import { chromium } from "playwright-core";

const chrome = process.env.CHROME_PATH ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const bundle = await readFile(resolve(import.meta.dirname, "../extension.js"), "utf8");
const browser = await chromium.launch({ executablePath: chrome, headless: true });
try {
  const page = await browser.newPage();
  await page.route("http://conversation-search.test/**", (route) => route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><html><body><main id='mount'></main></body></html>" }));
  await page.goto("http://conversation-search.test/");
  const result = await page.evaluate(async (source) => {
    const home = "/srv/canvas";
    const encode = (value) => btoa(JSON.stringify(value));
    const native = (data) => `CONVERSATION_SEARCH\t${encode({ ok: true, data })}\n`;
    const locations = [{ path: `${home}/.openhands/dev_conversations`, layout: "sdk-dev", state: "ready", conversations: 12, files: 100, malformed: 1 }, { path: `${home}/.openhands/conversations`, layout: "sdk-standard", state: "missing", conversations: 0, files: 0, malformed: 0 }];
    const service = { running: false, mode: "command", version: "0.1.0", idleShutdownSeconds: 600 };
    const status = { ready: true, documents: 98, sourceFiles: 100, conversations: 12, malformedFiles: 1, indexBytes: 65536, lastIndexedAt: "2026-09-09T12:00:00Z", locations, service };
    const registrations = new Map(); const requests = []; const navigations = [];
    const url = URL.createObjectURL(new Blob([source], { type: "text/javascript" }));
    const host = { apiVersion: "1", extension: { name: "conversation-search-sidecar", version: "0.1.0" }, backend: { id: "blob-local", kind: "local" }, agentServer: { async request(request) {
      requests.push(request);
      if (request.path === "/api/file/home") return { home };
      const command = request.body?.command ?? "";
      if (command.includes("CONVERSATION_SEARCH_PROBE")) return { exit_code: 0, stdout: `CONVERSATION_SEARCH_PROBE\t${encode({ os: "Linux", arch: "x86_64", target: "linux-amd64", supported: true, goVersion: "go version go1.25 linux/amd64", goReady: true, installed: true, runtimeVersion: "1", binaryPresent: true, artifactPresent: true, artifactVerified: true, locations })}\n`, stderr: "" };
      const match = command.match(/'([A-Za-z0-9+/=]+)'$/); const payload = match ? JSON.parse(atob(match[1])) : {};
      if (payload.action === "status") return { exit_code: 0, stdout: native({ status }), stderr: "" };
      if (payload.action === "search") return { exit_code: 0, stdout: native({ search: { total: 1, durationMs: 2.4, status, hits: [{ id: "doc-1", score: 1.2, conversationId: "conv", eventId: "evt", title: "Canvas sidecar", timestamp: "2026-09-09T11:00:00Z", role: "user", kind: "MessageEvent", tool: "", sourcePath: `${home}/.openhands/dev_conversations/conv/events/event.json`, excerpt: "native search result" }] } }), stderr: "" };
      if (payload.action === "inspect") return { exit_code: 0, stdout: native({ hit: { id: "doc-1", score: 1.2, conversationId: "conv", eventId: "evt", title: "Canvas sidecar", timestamp: "2026-09-09T11:00:00Z", role: "user", kind: "MessageEvent", tool: "", sourcePath: `${home}/.openhands/dev_conversations/conv/events/event.json`, excerpt: "native search result", text: "native search result" } }), stderr: "" };
      throw new Error(`Unexpected command: ${command.slice(0, 80)}`);
    } }, registerPage(id, mount) { registrations.set(id, mount); return () => registrations.delete(id); }, navigate() { throw new Error("The host navigator must not be used for mounted App links."); } };
    const container = document.querySelector("#mount");
    const waitFor = async (predicate, label) => { const deadline = performance.now() + 15000; while (!predicate()) { if (performance.now() > deadline) throw new Error(label); await new Promise((resolveWait) => setTimeout(resolveWait, 25)); } };
    try {
      const module = await import(url); const deactivate = module.activate(host);
      if (registrations.size !== 1 || !registrations.has("search")) throw new Error("The single declared page was not registered.");
      const navigate = (path) => navigations.push(path);
      const cleanup = registrations.get("search")({ container, path: "", navigate });
      await waitFor(() => container.textContent.includes("Find the moment") && container.textContent.includes("98"), "Search page did not render.");
      const input = container.querySelector('input[aria-label="Search conversation index"]'); input.value = "native"; input.dispatchEvent(new Event("input", { bubbles: true }));
      container.querySelector('form button[type="submit"]').click();
      await waitFor(() => container.textContent.includes("native search result"), "Search result did not render.");
      const conversationLink = container.querySelector('a[href="/conversations/conv?backend=blob-local"]');
      if (!conversationLink || !conversationLink.textContent.includes("Canvas sidecar")) throw new Error("Search result did not link to its conversation.");
      conversationLink.click();
      if (navigations.at(-1) !== "/conversations/conv?backend=blob-local") throw new Error("Conversation link did not use Canvas navigation.");
      const searchCommand = requests.at(-1).body.command;
      if (searchCommand.includes("native search result") || searchCommand.includes("query\":\"native")) throw new Error("Search text escaped into shell source.");
      cleanup(); if (container.childElementCount !== 0) throw new Error("Search cleanup left DOM behind.");
      const operationsCleanup = registrations.get("search")({ container, path: "operations", navigate });
      await waitFor(() => container.textContent.includes("Own the index lifecycle") && container.textContent.includes("sdk-dev"), "Operations page did not render.");
      operationsCleanup(); deactivate(); if (registrations.size !== 0 || container.childElementCount !== 0) throw new Error("Final cleanup failed.");
      return { pages: 1, routes: 2, requests: requests.length };
    } finally { URL.revokeObjectURL(url); }
  }, bundle);
  console.log(`Blob smoke OK: ${result.pages} registered page with ${result.routes} routes, clickable conversation navigation, base64 CLI search, diagnostics, operations, ${result.requests} authenticated requests, and cleanup complete.`);
} finally { await browser.close(); }
