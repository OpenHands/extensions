/// <reference lib="webworker" />

import initSqlJs, { type Database, type SqlJsStatic } from "sql.js";
import wasmUrl from "sql.js/dist/sql-wasm.wasm?url";
import { applyMigrations, executeQuery, getSnapshot, seedLibrary } from "./database-core";
import { openDatabaseStorage, type DatabaseStorage } from "./storage";
import type { WorkerRequest, WorkerResponse } from "./types";

const workerScope: DedicatedWorkerGlobalScope = self as unknown as DedicatedWorkerGlobalScope;
const cancelled = new Set<number>();
let sqlRuntime: Promise<SqlJsStatic> | null = null;
let database: Database | null = null;
let storage: DatabaseStorage | null = null;
let namespace = "";
let queue = Promise.resolve();

function loadSqlRuntime(): Promise<SqlJsStatic> {
  sqlRuntime ??= initSqlJs({ locateFile: () => wasmUrl }).catch((error: unknown) => {
    throw new Error(
      `SQLite WASM could not start: ${error instanceof Error ? error.message : String(error)}. ` +
        "Reload Canvas in a browser that supports WebAssembly.",
    );
  });
  return sqlRuntime;
}

function requireDatabase(): Database {
  if (!database || !storage || !namespace) {
    throw new Error("The database is not ready yet. Wait for initialization, then try again.");
  }
  return database;
}

async function persist(): Promise<void> {
  if (!storage || !database) throw new Error("Database persistence is not initialized.");
  await storage.save(database.export());
}

async function initialize(nextNamespace: string) {
  database?.close();
  storage?.close();
  namespace = nextNamespace;
  storage = await openDatabaseStorage(namespace);
  const [SQL, saved] = await Promise.all([loadSqlRuntime(), storage.load()]);
  database = saved ? new SQL.Database(saved) : new SQL.Database();
  const applied = applyMigrations(database);
  if (!saved || applied.length > 0) await persist();
  return getSnapshot(database, namespace);
}

async function handleRequest(request: Exclude<WorkerRequest, { type: "cancel" }>): Promise<unknown> {
  if (request.type === "init") return initialize(request.namespace);
  const activeDatabase = requireDatabase();
  if (request.type === "query") {
    try {
      const result = executeQuery(activeDatabase, namespace, request.sql);
      await persist();
      return result;
    } catch (error) {
      await persist();
      throw error;
    }
  }
  if (request.type === "seed") {
    seedLibrary(activeDatabase);
    await persist();
    return getSnapshot(activeDatabase, namespace);
  }
  if (request.type === "reset") {
    await storage!.clear();
    activeDatabase.close();
    const SQL = await loadSqlRuntime();
    database = new SQL.Database();
    applyMigrations(database);
    await persist();
    return getSnapshot(database, namespace);
  }
  return activeDatabase.export();
}

function post(response: WorkerResponse, transfer: Transferable[] = []): void {
  workerScope.postMessage(response, transfer);
}

workerScope.onmessage = (event: MessageEvent<WorkerRequest>) => {
  const request = event.data;
  if (request.type === "cancel") {
    cancelled.add(request.targetId);
    return;
  }

  queue = queue.then(async () => {
    if (cancelled.delete(request.id)) return;
    try {
      const data = await handleRequest(request);
      if (cancelled.delete(request.id)) return;
      if (data instanceof Uint8Array) {
        post({ id: request.id, ok: true, data }, [data.buffer]);
      } else {
        post({ id: request.id, ok: true, data });
      }
    } catch (error) {
      if (cancelled.delete(request.id)) return;
      post({
        id: request.id,
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  });
};
