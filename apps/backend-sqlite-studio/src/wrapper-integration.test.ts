// @vitest-environment node
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { DATA_SUBPATH, INSTALL_COMMAND, RESET_COMMAND, commandForPayload } from "./backend-service";

function run(cwd: string, command: string): { ok: boolean; data?: Record<string, unknown>; error?: string } {
  const output = execFileSync("/bin/sh", ["-c", command], { cwd, encoding: "utf8" });
  const encoded = output.match(/^BACKEND_SQLITE_STUDIO\t([A-Za-z0-9+/=]+)$/m)?.[1];
  if (!encoded) throw new Error(`Missing wrapper envelope: ${output}`);
  return JSON.parse(Buffer.from(encoded, "base64").toString("utf8"));
}

describe("real Python SQLite wrapper", () => {
  it("installs, migrates, safely executes tricky SQL, persists history, and resets only its directory", () => {
    const home = mkdtempSync(join(tmpdir(), "backend-sqlite-studio-"));
    try {
      const installed = run(home, INSTALL_COMMAND);
      expect(installed.ok).toBe(true);
      expect(installed.data?.migrations).toEqual([expect.objectContaining({ id: "001-create-notes" })]);
      const sql = "INSERT INTO notes(title, body) VALUES ('beginner; guide', '$HOME is data'); SELECT title, body FROM notes;";
      const queried = run(home, commandForPayload({ action: "query", sql, statements: ["INSERT INTO notes(title, body) VALUES ('beginner; guide', '$HOME is data')", "SELECT title, body FROM notes"] }));
      expect(queried.ok).toBe(true);
      expect(queried.data?.results).toEqual([expect.objectContaining({ values: [["beginner; guide", "$HOME is data"]] })]);
      const status = run(home, commandForPayload({ action: "status" }));
      expect(status.data?.history).toEqual([expect.objectContaining({ sql, status: "success" })]);
      expect(existsSync(join(home, DATA_SUBPATH, "studio.sqlite3"))).toBe(true);
      execFileSync("/bin/sh", ["-c", RESET_COMMAND], { cwd: home });
      expect(existsSync(join(home, DATA_SUBPATH))).toBe(false);
      expect(existsSync(home)).toBe(true);
    } finally { rmSync(home, { recursive: true, force: true }); }
  });

  it("returns a structured migration failure without writing outside the App directory", () => {
    const home = mkdtempSync(join(tmpdir(), "backend-sqlite-studio-bad-migration-"));
    try {
      const app = join(home, DATA_SUBPATH);
      execFileSync("python3", ["-c", "import pathlib, sqlite3, sys; p=pathlib.Path(sys.argv[1]); p.mkdir(parents=True); c=sqlite3.connect(p/'studio.sqlite3'); c.execute('CREATE TABLE _backend_sqlite_studio_migrations (wrong TEXT)'); c.commit()", app]);
      const result = run(home, INSTALL_COMMAND);
      expect(result.ok).toBe(false);
      expect(result.error).toMatch(/no such column: id/);
      expect(readFileSync(join(app, ".runtime-version"), "utf8")).toBe("1");
      expect(existsSync(join(home, "studio.sqlite3"))).toBe(false);
    } finally { rmSync(home, { recursive: true, force: true }); }
  });
});
