import DatabaseWorker from "./database.worker?worker&inline";
import type { DatabaseSnapshot, QueryResponse, WorkerRequest, WorkerResponse } from "./types";

type PendingRequest = {
  resolve: (value: unknown) => void;
  reject: (reason: unknown) => void;
  removeAbort?: () => void;
};

type RequestPayload =
  | { type: "init"; namespace: string }
  | { type: "query"; sql: string }
  | { type: "seed" }
  | { type: "reset" }
  | { type: "export" };

export class DatabaseClient {
  private readonly worker: Worker;
  private readonly pending = new Map<number, PendingRequest>();
  private nextId = 1;
  private disposed = false;

  constructor(worker: Worker = new DatabaseWorker()) {
    this.worker = worker;
    this.worker.addEventListener("message", this.onMessage);
    this.worker.addEventListener("error", this.onWorkerError);
  }

  private readonly onMessage = (event: MessageEvent<WorkerResponse>) => {
    const response = event.data;
    const pending = this.pending.get(response.id);
    if (!pending) return;
    this.pending.delete(response.id);
    pending.removeAbort?.();
    if (response.ok) pending.resolve(response.data);
    else pending.reject(new Error(response.error));
  };

  private readonly onWorkerError = (event: ErrorEvent) => {
    const error = new Error(event.message || "The database Worker stopped unexpectedly.");
    for (const pending of this.pending.values()) {
      pending.removeAbort?.();
      pending.reject(error);
    }
    this.pending.clear();
  };

  private request<T>(payload: RequestPayload, signal?: AbortSignal): Promise<T> {
    if (this.disposed) return Promise.reject(new Error("The database client has been disposed."));
    if (signal?.aborted) return Promise.reject(new DOMException("The request was cancelled.", "AbortError"));
    const id = this.nextId++;
    return new Promise<T>((resolve, reject) => {
      const pending: PendingRequest = { resolve: resolve as (value: unknown) => void, reject };
      if (signal) {
        const onAbort = () => {
          this.pending.delete(id);
          try {
            this.worker.postMessage({ id: this.nextId++, type: "cancel", targetId: id } satisfies WorkerRequest);
          } catch {
            // The Worker may already be gone during App cleanup.
          }
          reject(new DOMException("The request was cancelled.", "AbortError"));
        };
        signal.addEventListener("abort", onAbort, { once: true });
        pending.removeAbort = () => signal.removeEventListener("abort", onAbort);
      }
      this.pending.set(id, pending);
      try {
        this.worker.postMessage({ id, ...payload } as WorkerRequest);
      } catch (error) {
        this.pending.delete(id);
        pending.removeAbort?.();
        reject(error);
      }
    });
  }

  initialize(namespace: string, signal?: AbortSignal): Promise<DatabaseSnapshot> {
    return this.request({ type: "init", namespace }, signal);
  }

  query(sql: string, signal?: AbortSignal): Promise<QueryResponse> {
    return this.request({ type: "query", sql }, signal);
  }

  seed(signal?: AbortSignal): Promise<DatabaseSnapshot> {
    return this.request({ type: "seed" }, signal);
  }

  reset(signal?: AbortSignal): Promise<DatabaseSnapshot> {
    return this.request({ type: "reset" }, signal);
  }

  export(signal?: AbortSignal): Promise<Uint8Array> {
    return this.request({ type: "export" }, signal);
  }

  terminate(): void {
    if (this.disposed) return;
    this.disposed = true;
    const error = new DOMException("The database client was terminated.", "AbortError");
    for (const pending of this.pending.values()) {
      pending.removeAbort?.();
      pending.reject(error);
    }
    this.pending.clear();
    this.worker.removeEventListener("message", this.onMessage);
    this.worker.removeEventListener("error", this.onWorkerError);
    this.worker.terminate();
  }
}
