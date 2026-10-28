import { describe, expect, it, vi } from "vitest";
import {
  DATA_SUBPATH,
  INSTALL_COMMAND,
  PROBE_COMMAND,
  RESET_COMMAND,
  agentHandoffText,
  agentSetupText,
  commandForPayload,
  dataDirectory,
  discoverHome,
  installOrRepair,
  isValidHomePath,
  parseSqlStatements,
  probePrerequisites,
  resetData,
  runQuery,
} from "./backend-service";
import type { AgentServerRequest, CanvasHost, DatabaseSnapshot } from "./types";

const HOME = "/Users/tester";
const SNAPSHOT: DatabaseSnapshot = {
  initialized: true, databasePath: `${HOME}/${DATA_SUBPATH}/studio.sqlite3`, sizeBytes: 8192,
  journalMode: "delete", tables: [{ name: "notes", sql: "CREATE TABLE notes", columns: [{ name: "id", type: "INTEGER", nullable: false, primaryKey: true }] }],
  migrations: [{ id: "001-create-notes", appliedAt: "2026-09-09T12:00:00Z" }], history: [],
};

function encoded(value: unknown): string {
  const json = JSON.stringify(value); const bytes = new TextEncoder().encode(json); let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}
function envelope(data?: unknown, error?: string): string {
  return `BACKEND_SQLITE_STUDIO\t${encoded(error ? { ok: false, error } : { ok: true, data })}\n`;
}
function hostWith(request: (request: AgentServerRequest) => Promise<unknown>): CanvasHost {
  return { apiVersion: "1", extension: { name: "backend-sqlite-studio", version: "0.1.0" }, backend: { id: "local" }, agentServer: { request: request as CanvasHost["agentServer"]["request"] }, registerPage: vi.fn(), navigate: vi.fn() };
}

describe("Agent Server home and data-directory isolation", () => {
  it("discovers the home through the existing endpoint and derives only the App directory", async () => {
    const request = vi.fn(async () => ({ home: HOME }));
    await expect(discoverHome(hostWith(request))).resolves.toBe(HOME);
    expect(request).toHaveBeenCalledWith({ path: "/api/file/home" });
    expect(dataDirectory(HOME)).toBe(`${HOME}/.openhands/apps/backend-sqlite-studio`);
  });

  it.each(["", "relative", "/tmp/../escape", "/tmp//double", "/tmp\nunsafe"])("rejects unsafe home %j", (path) => expect(isValidHomePath(path)).toBe(false));

  it("rejects missing and malformed home responses", async () => {
    await expect(discoverHome(hostWith(async () => ({ nope: true })))).rejects.toThrow("safe absolute home");
    await expect(discoverHome(hostWith(async () => "not-json"))).rejects.toThrow("valid JSON");
  });
});

describe("non-mutating prerequisites and setup", () => {
  it("uses the exact read-only probe and parses both SQLite runtimes", async () => {
    const result = { pythonReady: 1, pythonVersion: "Python 3.13.7", sqliteModuleVersion: "3.50.4", sqliteCliVersion: "3.50.4", initialized: 0, wrapperPresent: 0, databasePresent: 0, runtimeVersion: "" };
    const request = vi.fn(async () => ({ exit_code: 0, stdout: `BACKEND_SQLITE_STUDIO_PROBE\t${encoded(result)}\n`, stderr: "" }));
    await expect(probePrerequisites(hostWith(request), HOME)).resolves.toEqual({ pythonReady: true, pythonVersion: "Python 3.13.7", sqliteModuleVersion: "3.50.4", sqliteCliVersion: "3.50.4", initialized: false, wrapperPresent: false, databasePresent: false, runtimeVersion: null });
    expect(request).toHaveBeenCalledWith({ path: "/api/bash/execute_bash_command", method: "POST", body: { command: PROBE_COMMAND, cwd: HOME, timeout: 15 } });
    expect(PROBE_COMMAND).not.toMatch(/mkdir|touch|rm\s|install\s|create_directory/);
  });

  it("uses one fixed App-scoped template for migration success", async () => {
    const request = vi.fn(async () => ({ exit_code: 0, stdout: envelope(SNAPSHOT), stderr: "" }));
    await expect(installOrRepair(hostWith(request), HOME)).resolves.toEqual(SNAPSHOT);
    expect(request).toHaveBeenCalledWith({ path: "/api/bash/execute_bash_command", method: "POST", body: { command: INSTALL_COMMAND, cwd: HOME, timeout: 30 } });
    expect(INSTALL_COMMAND).toContain("app_dir='.openhands/apps/backend-sqlite-studio'");
    expect(INSTALL_COMMAND).not.toContain(HOME);
  });

  it("surfaces migration failure from the structured wrapper", async () => {
    const host = hostWith(async () => ({ exit_code: 0, stdout: envelope(undefined, "migration 001 failed"), stderr: "" }));
    await expect(installOrRepair(host, HOME)).rejects.toThrow("migration 001 failed");
  });
});

describe("structured query protocol", () => {
  it("parses semicolons only outside strings and comments", () => {
    expect(parseSqlStatements("INSERT INTO notes(title) VALUES ('a;b'); -- keep ; here\nSELECT * FROM notes;")).toEqual([
      "INSERT INTO notes(title) VALUES ('a;b')", "-- keep ; here\nSELECT * FROM notes",
    ]);
    expect(() => parseSqlStatements("SELECT 'unfinished")).toThrow("unterminated");
  });

  it("base64-encodes user SQL so it never becomes shell source", async () => {
    const sql = "SELECT '$HOME'; touch /tmp/never; -- it's SQL";
    const command = commandForPayload({ action: "query", sql, statements: [sql] });
    expect(command).not.toContain(sql);
    expect(command).toMatch(/^python3 '\.openhands\/apps\/backend-sqlite-studio\/wrapper\.py' '[A-Za-z0-9+/=]+'$/);
    const response = { ...SNAPSHOT, results: [{ columns: ["value"], values: [["ok"]], truncated: false }], rowsAffected: 0, durationMs: 2.5 };
    const request = vi.fn(async (_call: AgentServerRequest) => ({ exit_code: 0, stdout: envelope(response), stderr: "" }));
    await expect(runQuery(hostWith(request), HOME, sql)).resolves.toEqual(response);
    const sent = (request.mock.calls[0][0].body as { command: string }).command;
    expect(sent).not.toContain("touch /tmp/never");
  });

  it("surfaces wrapper query failures without losing the message", async () => {
    const host = hostWith(async () => ({ exit_code: 0, stdout: envelope(undefined, "no such table: missing"), stderr: "" }));
    await expect(runQuery(host, HOME, "SELECT * FROM missing")).rejects.toThrow("no such table");
  });
});

describe("destructive reset and agent handoff", () => {
  it("uses one exact reset target relative to validated home", async () => {
    const request = vi.fn(async () => ({ exit_code: 0, stdout: "BACKEND_SQLITE_STUDIO_RESET\n", stderr: "" }));
    await resetData(hostWith(request), HOME);
    expect(request).toHaveBeenCalledWith({ path: "/api/bash/execute_bash_command", method: "POST", body: { command: RESET_COMMAND, cwd: HOME, timeout: 20 } });
    expect(RESET_COMMAND.match(/\.openhands\/apps\/backend-sqlite-studio/g)).toHaveLength(2);
  });

  it("names the exact database and safe constraints in agent-facing instructions", () => {
    const prompt = agentHandoffText(HOME);
    expect(prompt).toContain(`${HOME}/${DATA_SUBPATH}/studio.sqlite3`);
    expect(prompt).toContain("parameterized SQL");
    expect(prompt).toContain("Do not move, replace, reset, or delete");
  });

  it("provides a non-mutating, approval-gated setup prompt", () => {
    const prompt = agentSetupText(HOME);
    expect(prompt).toContain(`${HOME}/${DATA_SUBPATH}`);
    expect(prompt).toContain("obtain my approval before installing");
    expect(prompt).toContain("use Recheck");
  });
});
