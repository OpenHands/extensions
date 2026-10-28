import { createRequire } from "node:module";
import initSqlJs from "sql.js";
import { beforeAll, describe, expect, it } from "vitest";
import { applyMigrations, executeQuery, getSnapshot, seedLibrary } from "./database-core";

let SQL: Awaited<ReturnType<typeof initSqlJs>>;

beforeAll(async () => {
  const require = createRequire(import.meta.url);
  const wasmPath = require.resolve("sql.js/dist/sql-wasm.wasm");
  SQL = await initSqlJs({ locateFile: () => wasmPath });
});

describe("database migrations and seed data", () => {
  it("applies the imported migration exactly once", () => {
    const database = new SQL.Database();
    expect(applyMigrations(database)).toEqual(["001-create-library"]);
    expect(applyMigrations(database)).toEqual([]);
    expect(getSnapshot(database, "test").tables.map((table) => table.name)).toEqual(["books"]);
    expect(getSnapshot(database, "test").migrations).toHaveLength(1);
    database.close();
  });

  it("loads embedded JSON and executes real SQLite queries", () => {
    const database = new SQL.Database();
    applyMigrations(database);
    seedLibrary(database);
    const response = executeQuery(database, "test", "SELECT COUNT(*) AS total, MAX(rating) AS top_rating FROM books;");
    expect(response.results[0]).toEqual({ columns: ["total", "top_rating"], values: [[5, 4.9]] });
    expect(response.history[0]?.status).toBe("success");
    database.close();
  });
});
