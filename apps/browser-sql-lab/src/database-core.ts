import type { Database, QueryExecResult } from "sql.js";
import migration001 from "./migrations/001-create-library.sql?raw";
import seedData from "./seed-data.json";
import type {
  DatabaseSnapshot,
  HistoryRecord,
  MigrationRecord,
  QueryResponse,
  QueryTable,
  SchemaTable,
  SqlValue,
} from "./types";

export const MIGRATIONS = [
  { id: "001-create-library", sql: migration001 },
] as const;

const INTERNAL_SCHEMA_SQL = `
  CREATE TABLE IF NOT EXISTS _browser_sql_lab_migrations (
    id TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
  );
  CREATE TABLE IF NOT EXISTS _browser_sql_lab_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sql TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success', 'error')),
    executed_at TEXT NOT NULL
  );
`;

function rows(result: QueryExecResult | undefined): SqlValue[][] {
  return (result?.values ?? []) as SqlValue[][];
}

function text(value: SqlValue | undefined): string {
  return value == null ? "" : String(value);
}

export function applyMigrations(database: Database): string[] {
  database.run(INTERNAL_SCHEMA_SQL);
  const applied = new Set(
    rows(database.exec("SELECT id FROM _browser_sql_lab_migrations")[0]).map((row) => text(row[0])),
  );
  const newlyApplied: string[] = [];

  for (const migration of MIGRATIONS) {
    if (applied.has(migration.id)) continue;
    database.run("BEGIN");
    try {
      database.run(migration.sql);
      database.run(
        "INSERT INTO _browser_sql_lab_migrations (id, applied_at) VALUES (?, ?)",
        [migration.id, new Date().toISOString()],
      );
      database.run("COMMIT");
      newlyApplied.push(migration.id);
    } catch (error) {
      database.run("ROLLBACK");
      throw error;
    }
  }
  return newlyApplied;
}

function readSchema(database: Database): SchemaTable[] {
  const tableRows = rows(database.exec(`
    SELECT name, COALESCE(sql, '')
    FROM sqlite_master
    WHERE type = 'table'
      AND name NOT LIKE 'sqlite_%'
      AND name NOT LIKE '_browser_sql_lab_%'
    ORDER BY name
  `)[0]);

  return tableRows.map((row) => {
    const name = text(row[0]);
    const escapedName = name.replaceAll('"', '""');
    const columnRows = rows(database.exec(`PRAGMA table_info("${escapedName}")`)[0]);
    return {
      name,
      sql: text(row[1]),
      columns: columnRows.map((column) => ({
        name: text(column[1]),
        type: text(column[2]) || "ANY",
        nullable: Number(column[3]) === 0 && Number(column[5]) === 0,
        primaryKey: Number(column[5]) > 0,
      })),
    };
  });
}

function readMigrations(database: Database): MigrationRecord[] {
  database.run(INTERNAL_SCHEMA_SQL);
  return rows(database.exec(`
    SELECT id, applied_at
    FROM _browser_sql_lab_migrations
    ORDER BY id
  `)[0]).map((row) => ({ id: text(row[0]), appliedAt: text(row[1]) }));
}

function readHistory(database: Database): HistoryRecord[] {
  database.run(INTERNAL_SCHEMA_SQL);
  return rows(database.exec(`
    SELECT id, sql, status, executed_at
    FROM _browser_sql_lab_history
    ORDER BY id DESC
    LIMIT 30
  `)[0]).map((row) => ({
    id: Number(row[0]),
    sql: text(row[1]),
    status: text(row[2]) as HistoryRecord["status"],
    executedAt: text(row[3]),
  }));
}

export function getSnapshot(database: Database, namespace: string): DatabaseSnapshot {
  return {
    namespace,
    tables: readSchema(database),
    migrations: readMigrations(database),
    history: readHistory(database),
  };
}

function recordHistory(database: Database, sql: string, status: HistoryRecord["status"]): void {
  database.run(INTERNAL_SCHEMA_SQL);
  database.run(
    "INSERT INTO _browser_sql_lab_history (sql, status, executed_at) VALUES (?, ?, ?)",
    [sql, status, new Date().toISOString()],
  );
}

export function executeQuery(database: Database, namespace: string, sql: string): QueryResponse {
  const trimmed = sql.trim();
  if (!trimmed) throw new Error("Enter a SQL statement before running the query.");
  const started = performance.now();
  try {
    const rawResults = database.exec(trimmed);
    const rowsAffected = database.getRowsModified();
    recordHistory(database, trimmed, "success");
    const results: QueryTable[] = rawResults.map((result) => ({
      columns: result.columns,
      values: result.values as SqlValue[][],
    }));
    return {
      ...getSnapshot(database, namespace),
      results,
      rowsAffected,
      durationMs: Math.max(0, performance.now() - started),
    };
  } catch (error) {
    try {
      recordHistory(database, trimmed, "error");
    } catch {
      // Preserve the original SQLite error if user SQL damaged the history table.
    }
    throw error;
  }
}

export function seedLibrary(database: Database): void {
  database.run("BEGIN");
  try {
    const statement = database.prepare(`
      INSERT INTO books (id, title, author, published_year, rating)
      VALUES (?, ?, ?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET
        title = excluded.title,
        author = excluded.author,
        published_year = excluded.published_year,
        rating = excluded.rating
    `);
    try {
      for (const book of seedData) {
        statement.run([book.id, book.title, book.author, book.publishedYear, book.rating]);
      }
    } finally {
      statement.free();
    }
    database.run("COMMIT");
  } catch (error) {
    database.run("ROLLBACK");
    throw error;
  }
}
