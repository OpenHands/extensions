import "fake-indexeddb/auto";
import { vi } from "vitest";
import type { DatabaseSnapshot, WorkerRequest, WorkerResponse } from "./types";

export const fakeWorkers: FakeDatabaseWorker[] = [];
let nextInitializationError = "";

export function failNextInitialization(message: string): void {
  nextInitializationError = message;
}

function snapshot(namespace: string, history: DatabaseSnapshot["history"] = []): DatabaseSnapshot {
  return {
    namespace,
    tables: [{
      name: "books",
      sql: "CREATE TABLE books (...)" ,
      columns: [
        { name: "id", type: "INTEGER", nullable: true, primaryKey: true },
        { name: "title", type: "TEXT", nullable: false, primaryKey: false },
        { name: "author", type: "TEXT", nullable: false, primaryKey: false },
      ],
    }],
    migrations: [{ id: "001-create-library", appliedAt: "2026-09-08T12:00:00.000Z" }],
    history,
  };
}

export class FakeDatabaseWorker {
  private messageListeners = new Set<(event: MessageEvent<WorkerResponse>) => void>();
  private errorListeners = new Set<(event: ErrorEvent) => void>();
  namespace = "";
  requests: WorkerRequest[] = [];
  terminate = vi.fn();
  removeEventListener = vi.fn((type: string, listener: EventListenerOrEventListenerObject) => {
    if (type === "message") this.messageListeners.delete(listener as (event: MessageEvent<WorkerResponse>) => void);
    if (type === "error") this.errorListeners.delete(listener as (event: ErrorEvent) => void);
  });
  addEventListener = vi.fn((type: string, listener: EventListenerOrEventListenerObject) => {
    if (type === "message") this.messageListeners.add(listener as (event: MessageEvent<WorkerResponse>) => void);
    if (type === "error") this.errorListeners.add(listener as (event: ErrorEvent) => void);
  });

  constructor() { fakeWorkers.push(this); }

  postMessage = vi.fn((request: WorkerRequest) => {
    this.requests.push(request);
    if (request.type === "cancel") return;
    queueMicrotask(() => {
      let response: WorkerResponse;
      if (request.type === "init") {
        this.namespace = request.namespace;
        if (nextInitializationError) {
          response = { id: request.id, ok: false, error: nextInitializationError };
          nextInitializationError = "";
        } else {
          response = { id: request.id, ok: true, data: snapshot(this.namespace) };
        }
      } else if (request.type === "query" && request.sql.includes("missing_table")) {
        response = { id: request.id, ok: false, error: "no such table: missing_table" };
      } else if (request.type === "query") {
        response = {
          id: request.id,
          ok: true,
          data: {
            ...snapshot(this.namespace, [{ id: 1, sql: request.sql, status: "success", executedAt: "2026-09-08T12:01:00.000Z" }]),
            results: [{ columns: ["author", "books"], values: [["Ursula K. Le Guin", 2]] }],
            rowsAffected: 0,
            durationMs: 1.25,
          },
        };
      } else if (request.type === "export") {
        response = { id: request.id, ok: true, data: new Uint8Array([83, 81, 76]) };
      } else {
        response = { id: request.id, ok: true, data: snapshot(this.namespace) };
      }
      for (const listener of this.messageListeners) {
        listener(new MessageEvent("message", { data: response }));
      }
    });
  });
}

vi.mock("./database.worker?worker&inline", () => ({ default: FakeDatabaseWorker }));
