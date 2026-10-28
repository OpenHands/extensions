import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import process from "node:process";
import { chromium } from "playwright-core";

const chrome = process.env.CHROME_PATH ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const bundle = await readFile(resolve(import.meta.dirname, "../extension.js"), "utf8");
const browser = await chromium.launch({ executablePath: chrome, headless: true });
try {
  const page = await browser.newPage();
  await page.route("http://backend-sqlite-studio.test/**", (route) => route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><html><body><main id='mount'></main></body></html>" }));
  await page.goto("http://backend-sqlite-studio.test/");
  const result = await page.evaluate(async (source) => {
    const home = "/srv/canvas";
    const encode = (value) => btoa(JSON.stringify(value));
    const envelope = (data) => `BACKEND_SQLITE_STUDIO\t${encode({ ok: true, data })}\n`;
    const snapshot = { initialized: true, databasePath: `${home}/.openhands/apps/backend-sqlite-studio/studio.sqlite3`, sizeBytes: 12288, journalMode: "wal", tables: [{ name: "notes", sql: "CREATE TABLE notes", columns: [{ name: "id", type: "INTEGER", nullable: false, primaryKey: true }, { name: "title", type: "TEXT", nullable: false, primaryKey: false }] }], migrations: [{ id: "001-create-notes", appliedAt: "2026-09-09T12:00:00Z" }], history: [] };
    const registrations = new Map(); const requests = [];
    const url = URL.createObjectURL(new Blob([source], { type: "text/javascript" }));
    const host = { apiVersion: "1", extension: { name: "backend-sqlite-studio", version: "0.1.0" }, backend: { id: "blob-local", kind: "local" }, agentServer: { async request(request) {
      requests.push(request);
      if (request.path === "/api/file/home") return { home };
      const command = request.body?.command ?? "";
      if (command.includes("BACKEND_SQLITE_STUDIO_PROBE")) return { exit_code: 0, stdout: `BACKEND_SQLITE_STUDIO_PROBE\t${encode({ pythonReady: 1, pythonVersion: "Python 3.13", sqliteModuleVersion: "3.50", sqliteCliVersion: "", initialized: 1, wrapperPresent: 1, databasePresent: 1, runtimeVersion: "1" })}\n`, stderr: "" };
      const match = command.match(/'([A-Za-z0-9+/=]+)'$/); const payload = match ? JSON.parse(atob(match[1])) : {};
      if (payload.action === "status") return { exit_code: 0, stdout: envelope(snapshot), stderr: "" };
      if (payload.action === "query") return { exit_code: 0, stdout: envelope({ ...snapshot, results: [{ columns: ["id", "title"], values: [[1, "Durable row"]], truncated: false }], rowsAffected: 0, durationMs: 1.2 }), stderr: "" };
      throw new Error(`Unexpected command: ${command.slice(0, 80)}`);
    } }, registerPage(id, mount) { registrations.set(id, mount); return () => registrations.delete(id); }, navigate() {} };
    const container = document.querySelector("#mount");
    const waitFor = async (predicate, label) => { const deadline = performance.now() + 15000; while (!predicate()) { if (performance.now() > deadline) throw new Error(label); await new Promise((resolveWait) => setTimeout(resolveWait, 25)); } };
    try {
      const module = await import(url); const deactivate = module.activate(host);
      if (registrations.size !== 2 || !registrations.has("studio") || !registrations.has("handoff")) throw new Error("Declared pages were not registered.");
      const cleanup = registrations.get("studio")({ container, path: "", navigate() {} });
      await waitFor(() => container.textContent.includes("SQL editor") && container.textContent.includes("notes"), "Studio did not render.");
      const editor = container.querySelector('textarea[aria-label="SQL editor"]'); editor.value = "SELECT 'not shell; $HOME' AS value;"; editor.dispatchEvent(new Event("input", { bubbles: true }));
      [...container.querySelectorAll("button")].find((button) => button.textContent.includes("Run SQL")).click();
      await waitFor(() => container.textContent.includes("Durable row"), "Query result did not render.");
      const queryCommand = requests.at(-1).body.command;
      if (queryCommand.includes("not shell") || queryCommand.includes("$HOME")) throw new Error("SQL escaped into shell source.");
      cleanup(); if (container.childElementCount !== 0) throw new Error("Studio cleanup left DOM behind.");
      const handoffCleanup = registrations.get("handoff")({ container, path: "", navigate() {} });
      await waitFor(() => container.textContent.includes(`${home}/.openhands/apps/backend-sqlite-studio/studio.sqlite3`), "Handoff path did not render.");
      handoffCleanup(); deactivate(); if (registrations.size !== 0 || container.childElementCount !== 0) throw new Error("Final cleanup failed.");
      return { pages: 2, requests: requests.length };
    } finally { URL.revokeObjectURL(url); }
  }, bundle);
  console.log(`Blob smoke OK: ${result.pages} pages, structured query, exact handoff path, ${result.requests} authenticated requests, and cleanup complete.`);
} finally { await browser.close(); }
