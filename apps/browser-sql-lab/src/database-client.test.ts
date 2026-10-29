import { describe, expect, it, vi } from "vitest";
import { DatabaseClient } from "./database-client";
import type { WorkerRequest, WorkerResponse } from "./types";

class ManualWorker {
  listeners = new Map<string, Set<(event: MessageEvent<WorkerResponse> | ErrorEvent) => void>>();
  messages: WorkerRequest[] = [];
  terminate = vi.fn();
  addEventListener(type: string, listener: (event: MessageEvent<WorkerResponse> | ErrorEvent) => void) {
    const listeners = this.listeners.get(type) ?? new Set();
    listeners.add(listener);
    this.listeners.set(type, listeners);
  }
  removeEventListener(type: string, listener: (event: MessageEvent<WorkerResponse> | ErrorEvent) => void) {
    this.listeners.get(type)?.delete(listener);
  }
  postMessage(message: WorkerRequest) { this.messages.push(message); }
  respond(response: WorkerResponse) {
    for (const listener of this.listeners.get("message") ?? []) {
      listener(new MessageEvent("message", { data: response }));
    }
  }
}

describe("DatabaseClient Worker RPC", () => {
  it("resolves successful responses and propagates Worker errors", async () => {
    const worker = new ManualWorker();
    const client = new DatabaseClient(worker as unknown as Worker);
    const success = client.initialize("browser-sql-lab::backend-a");
    worker.respond({ id: 1, ok: true, data: { namespace: "browser-sql-lab::backend-a", tables: [], migrations: [], history: [] } });
    await expect(success).resolves.toMatchObject({ namespace: "browser-sql-lab::backend-a" });

    const failure = client.query("bad sql");
    worker.respond({ id: 2, ok: false, error: "near bad: syntax error" });
    await expect(failure).rejects.toThrow("near bad: syntax error");
    client.terminate();
  });

  it("posts cancellation and ignores a late response", async () => {
    const worker = new ManualWorker();
    const client = new DatabaseClient(worker as unknown as Worker);
    const controller = new AbortController();
    const query = client.query("SELECT randomblob(1000000)", controller.signal);
    controller.abort();
    await expect(query).rejects.toMatchObject({ name: "AbortError" });
    expect(worker.messages).toContainEqual({ id: 2, type: "cancel", targetId: 1 });
    expect(() => worker.respond({ id: 1, ok: true, data: {} })).not.toThrow();
    client.terminate();
  });

  it("rejects pending requests and terminates the Worker during cleanup", async () => {
    const worker = new ManualWorker();
    const client = new DatabaseClient(worker as unknown as Worker);
    const pending = client.seed();
    client.terminate();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
    expect(worker.terminate).toHaveBeenCalledOnce();
  });
});
