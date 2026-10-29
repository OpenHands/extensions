import { act } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import manifest from "../canvas-extension.json";
import { HANDOFF_ROUTE, STUDIO_ROUTE, normalizeRoute } from "./App";
import { DATA_SUBPATH, INSTALL_COMMAND, PROBE_COMMAND, RESET_COMMAND, agentHandoffText } from "./backend-service";
import { activate } from "./extension";
import type { AgentServerRequest, CanvasHost, DatabaseSnapshot, MountContext } from "./types";

const HOME = "/srv/tester";
const SNAPSHOT: DatabaseSnapshot = {
  initialized: true, databasePath: `${HOME}/${DATA_SUBPATH}/studio.sqlite3`, sizeBytes: 12288, journalMode: "wal",
  tables: [{ name: "notes", sql: "CREATE TABLE notes", columns: [{ name: "id", type: "INTEGER", nullable: false, primaryKey: true }, { name: "title", type: "TEXT", nullable: false, primaryKey: false }] }],
  migrations: [{ id: "001-create-notes", appliedAt: "2026-09-09T12:00:00Z" }],
  history: [{ id: 1, sql: "SELECT * FROM notes", status: "success", executedAt: "2026-09-09T12:01:00Z", message: "" }],
};
function b64(value: unknown) { return btoa(JSON.stringify(value)); }
function envelope(data: unknown) { return `BACKEND_SQLITE_STUDIO\t${b64({ ok: true, data })}\n`; }

interface Options { initialized?: boolean; installError?: string }
function makeHost(options: Options = {}) {
  const mounts = new Map<string, (context: MountContext) => void | (() => void)>(); const unregisters = [vi.fn(), vi.fn()]; const requests: AgentServerRequest[] = [];
  let initialized = options.initialized ?? true;
  const host: CanvasHost = {
    apiVersion: "1", extension: { name: "backend-sqlite-studio", version: "0.1.0" }, backend: { id: "local-test", kind: "local" },
    agentServer: { async request(request) {
      requests.push(request);
      if (request.path === "/api/file/home") return { home: HOME } as never;
      const command = (request.body as { command: string }).command;
      if (command === PROBE_COMMAND) return { exit_code: 0, stdout: `BACKEND_SQLITE_STUDIO_PROBE\t${b64({ pythonReady: 1, pythonVersion: "Python 3.13", sqliteModuleVersion: "3.50", sqliteCliVersion: "", initialized: initialized ? 1 : 0, wrapperPresent: initialized ? 1 : 0, databasePresent: initialized ? 1 : 0, runtimeVersion: initialized ? "1" : "" })}\n`, stderr: "" } as never;
      if (command === INSTALL_COMMAND) { if (options.installError) return { exit_code: 0, stdout: envelope({ ok: false, error: options.installError }), stderr: "" } as never; initialized = true; return { exit_code: 0, stdout: envelope(SNAPSHOT), stderr: "" } as never; }
      if (command === RESET_COMMAND) { initialized = false; return { exit_code: 0, stdout: "BACKEND_SQLITE_STUDIO_RESET\n", stderr: "" } as never; }
      const payload = JSON.parse(atob(command.match(/'([A-Za-z0-9+/=]+)'$/)![1]));
      if (payload.action === "status") return { exit_code: 0, stdout: envelope(SNAPSHOT), stderr: "" } as never;
      if (payload.action === "query") return { exit_code: 0, stdout: envelope({ ...SNAPSHOT, history: [{ id: 2, sql: payload.sql, status: "success", executedAt: "2026-09-09T12:02:00Z", message: "" }, ...SNAPSHOT.history], results: [{ columns: ["id", "title"], values: [[1, "Shared row"]], truncated: false }], rowsAffected: 0, durationMs: 1.5 }), stderr: "" } as never;
      if (payload.action === "export") return { exit_code: 0, stdout: envelope({ databaseBase64: btoa("SQLite format 3\0demo"), sizeBytes: 21 }), stderr: "" } as never;
      throw new Error(`Unexpected action ${payload.action}`);
    } },
    registerPage: vi.fn((id, mount) => { mounts.set(id, mount); return unregisters[mounts.size - 1]; }), navigate: vi.fn(),
  };
  return { host, mounts, unregisters, requests };
}
async function flush(rounds = 6) { for (let i = 0; i < rounds; i += 1) await act(async () => { await Promise.resolve(); await new Promise((resolve) => setTimeout(resolve, 0)); }); }
async function mountPage(pageId = "studio", path = "", options: Options = {}) {
  const fixture = makeHost(options); const deactivate = activate(fixture.host); const container = document.createElement("div"); const navigate = vi.fn(); let cleanup: void | (() => void);
  await act(async () => { cleanup = fixture.mounts.get(pageId)!({ container, path, navigate }); }); await flush();
  return { ...fixture, container, navigate, cleanup: cleanup!, deactivate };
}
function button(container: HTMLElement, label: string) { return [...container.querySelectorAll("button")].find((item) => item.textContent?.includes(label)) as HTMLButtonElement; }

beforeEach(() => { localStorage.clear(); vi.mocked(navigator.clipboard.writeText).mockClear(); });

describe("activation, routing, and cleanup", () => {
  it("registers exactly both declared pages and unregisters them", () => {
    const fixture = makeHost(); const deactivate = activate(fixture.host);
    expect(manifest.contributes.pages.map((page) => page.id)).toEqual(["studio", "handoff"]);
    expect(fixture.host.registerPage).toHaveBeenCalledTimes(2); deactivate(); expect(fixture.unregisters.every((fn) => fn.mock.calls.length === 1)).toBe(true);
  });
  it.each([["studio", "", "studio"], ["studio", "studio", "studio"], ["handoff", "", "handoff"], ["handoff", "handoff", "handoff"], ["studio", "other", "not-found"]])("normalizes %s / %s", (page, path, view) => expect(normalizeRoute(page, path)).toBe(view));
  it("uses mount navigation and removes all DOM on cleanup", async () => {
    const mounted = await mountPage("studio", "other"); button(mounted.container, "Open Studio").click(); expect(mounted.navigate).toHaveBeenCalledWith(STUDIO_ROUTE);
    await act(async () => mounted.cleanup()); expect(mounted.container.childElementCount).toBe(0); mounted.deactivate();
  });
});

describe("studio workflows", () => {
  it("renders database status, schema, migrations, history, and query results", async () => {
    const mounted = await mountPage(); expect(mounted.container.textContent).toContain("Agent Server persistence boundary"); expect(mounted.container.textContent).toContain("notes"); expect(mounted.container.textContent).toContain("001-create-notes"); expect(mounted.container.textContent).toContain("SELECT * FROM notes");
    await act(async () => button(mounted.container, "Run SQL").click()); await flush(); expect(mounted.container.textContent).toContain("Shared row"); expect(mounted.container.textContent).toContain("SQL completed on the Agent Server database");
    const queryCommand = (mounted.requests.at(-1)!.body as { command: string }).command; expect(queryCommand).not.toContain("SELECT id, title");
    await act(async () => mounted.cleanup()); mounted.deactivate();
  });

  it("shows an explicit non-mutating onboarding gate and installs only after confirmation", async () => {
    const mounted = await mountPage("studio", "", { initialized: false }); expect(mounted.container.textContent).toContain("The probe only inspected"); expect(mounted.container.textContent).toContain(`${HOME}/${DATA_SUBPATH}`);
    const install = button(mounted.container, "Install"); expect(install.disabled).toBe(true); const checkbox = mounted.container.querySelector('input[type="checkbox"]') as HTMLInputElement; await act(async () => checkbox.click()); expect(install.disabled).toBe(false);
    await act(async () => install.click()); await flush(); expect(mounted.requests.some((request) => (request.body as { command?: string } | undefined)?.command === INSTALL_COMMAND)).toBe(true); expect(mounted.container.textContent).toContain("SQL editor");
    await act(async () => mounted.cleanup()); mounted.deactivate();
  });

  it("requires immediate reset confirmation, shows the exact target, and records the deletion", async () => {
    const mounted = await mountPage(); expect(mounted.requests.some((request) => (request.body as { command?: string } | undefined)?.command === RESET_COMMAND)).toBe(false); await act(async () => button(mounted.container, "Reset data").click());
    expect(mounted.container.textContent).toContain(`${HOME}/${DATA_SUBPATH}`); expect(mounted.container.textContent).toContain("cannot be undone"); expect(mounted.requests.some((request) => (request.body as { command?: string } | undefined)?.command === RESET_COMMAND)).toBe(false);
    await act(async () => (mounted.container.querySelector('[data-testid="confirm-reset"]') as HTMLButtonElement).click()); await flush(); expect(mounted.requests.some((request) => (request.body as { command?: string } | undefined)?.command === RESET_COMMAND)).toBe(true); expect(localStorage.getItem("backend-sqlite-studio:audit:local-test")).toContain("Deleted only");
    await act(async () => mounted.cleanup()); mounted.deactivate();
  });

  it("gates repair behind a visible confirmation and preserves the focused workflow", async () => {
    const mounted = await mountPage();
    await act(async () => button(mounted.container, "Repair").click());
    expect(mounted.container.textContent).toContain(`${HOME}/${DATA_SUBPATH}/wrapper.py`);
    expect(mounted.container.textContent).toContain("Existing database rows are preserved");
    expect(mounted.requests.some((request) => (request.body as { command?: string } | undefined)?.command === INSTALL_COMMAND)).toBe(false);
    await act(async () => (mounted.container.querySelector('[data-testid="confirm-repair"]') as HTMLButtonElement).click()); await flush();
    expect(mounted.requests.some((request) => (request.body as { command?: string } | undefined)?.command === INSTALL_COMMAND)).toBe(true);
    expect(localStorage.getItem("backend-sqlite-studio:audit:local-test")).toContain("Repair completed");
    await act(async () => mounted.cleanup()); mounted.deactivate();
  });
});

describe("agent handoff", () => {
  it("shows and copies the exact backend database instructions", async () => {
    const mounted = await mountPage("handoff"); expect(mounted.container.textContent).toContain(`${HOME}/${DATA_SUBPATH}/studio.sqlite3`); await act(async () => button(mounted.container, "Copy agent handoff").click()); expect(navigator.clipboard.writeText).toHaveBeenCalledWith(agentHandoffText(HOME));
    button(mounted.container, "Studio").click(); expect(mounted.navigate).toHaveBeenCalledWith(STUDIO_ROUTE); expect(HANDOFF_ROUTE).toContain("/handoff"); await act(async () => mounted.cleanup()); mounted.deactivate();
  });
});
