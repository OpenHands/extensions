import AnalysisWorker from "./analysis.worker?worker&inline";
import type { RepositoryAnalysis, WorkerRequest, WorkerResponse } from "./types";

type PendingRequest = {
  resolve: (value: RepositoryAnalysis) => void;
  reject: (reason: unknown) => void;
  removeAbort?: () => void;
};

type WorkerFactory = () => Worker;

export class AnalysisClient {
  private worker: Worker;
  private readonly workerFactory: WorkerFactory;
  private readonly pending = new Map<number, PendingRequest>();
  private nextId = 1;
  private disposed = false;

  constructor(workerFactory: WorkerFactory = () => new AnalysisWorker()) {
    this.workerFactory = workerFactory;
    this.worker = workerFactory();
    this.attach();
  }

  private attach(): void {
    this.worker.addEventListener("message", this.onMessage);
    this.worker.addEventListener("error", this.onWorkerError);
  }

  private detach(): void {
    this.worker.removeEventListener("message", this.onMessage);
    this.worker.removeEventListener("error", this.onWorkerError);
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
    this.rejectAll(new Error(event.message || "The repository analysis Worker stopped unexpectedly."));
  };

  private rejectAll(error: unknown): void {
    for (const pending of this.pending.values()) {
      pending.removeAbort?.();
      pending.reject(error);
    }
    this.pending.clear();
  }

  private restartAfterCancellation(targetId: number): void {
    try {
      this.worker.postMessage({ id: this.nextId++, type: "cancel", targetId } satisfies WorkerRequest);
    } catch {
      // Termination below is the authoritative cancellation path.
    }
    this.detach();
    this.worker.terminate();
    this.rejectAll(new DOMException("Repository analysis was cancelled.", "AbortError"));
    if (!this.disposed) {
      this.worker = this.workerFactory();
      this.attach();
    }
  }

  analyze(snapshot: string, signal?: AbortSignal): Promise<RepositoryAnalysis> {
    if (this.disposed) return Promise.reject(new Error("The analysis client has been disposed."));
    if (signal?.aborted) return Promise.reject(new DOMException("Repository analysis was cancelled.", "AbortError"));
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const pending: PendingRequest = { resolve, reject };
      if (signal) {
        const onAbort = () => this.restartAfterCancellation(id);
        signal.addEventListener("abort", onAbort, { once: true });
        pending.removeAbort = () => signal.removeEventListener("abort", onAbort);
      }
      this.pending.set(id, pending);
      try {
        this.worker.postMessage({ id, type: "analyze", snapshot } satisfies WorkerRequest);
      } catch (error) {
        this.pending.delete(id);
        pending.removeAbort?.();
        reject(error);
      }
    });
  }

  terminate(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.detach();
    this.worker.terminate();
    this.rejectAll(new DOMException("The analysis client was terminated.", "AbortError"));
  }
}
