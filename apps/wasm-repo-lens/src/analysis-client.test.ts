import { describe, expect, it, vi } from "vitest";
import { AnalysisClient } from "./analysis-client";
import type { RepositoryAnalysis, WorkerRequest, WorkerResponse } from "./types";

const analysis: RepositoryAnalysis = {
  branch: "main",
  files: 1,
  bytes: 42,
  sourceSamples: 1,
  historyEntries: 1,
  truncated: false,
  languages: [],
  directories: [],
  largeFiles: [],
  churnHotspots: [],
  dependencies: [],
  imports: [],
};

class FakeWorker {
  requests: WorkerRequest[] = [];
  message: ((event: MessageEvent<WorkerResponse>) => void) | null = null;
  error: ((event: ErrorEvent) => void) | null = null;
  terminate = vi.fn();
  addEventListener(type: string, listener: EventListener) {
    if (type === "message") this.message = listener as typeof this.message;
    if (type === "error") this.error = listener as typeof this.error;
  }
  removeEventListener(type: string, listener: EventListener) {
    if (type === "message" && this.message === listener) this.message = null;
    if (type === "error" && this.error === listener) this.error = null;
  }
  postMessage(request: WorkerRequest) { this.requests.push(request); }
  respond(response: WorkerResponse) { this.message?.({ data: response } as MessageEvent<WorkerResponse>); }
}

describe("AnalysisClient", () => {
  it("resolves Worker analysis RPC and terminates cleanly", async () => {
    const worker = new FakeWorker();
    const client = new AnalysisClient(() => worker as unknown as Worker);
    const promise = client.analyze("V\t1\n");
    expect(worker.requests[0]).toEqual({ id: 1, type: "analyze", snapshot: "V\t1\n" });
    worker.respond({ id: 1, ok: true, data: analysis });
    await expect(promise).resolves.toEqual(analysis);
    client.terminate();
    expect(worker.terminate).toHaveBeenCalledOnce();
  });

  it("cancels in-flight WASM work by terminating and replacing the Worker", async () => {
    const workers: FakeWorker[] = [];
    const client = new AnalysisClient(() => {
      const worker = new FakeWorker();
      workers.push(worker);
      return worker as unknown as Worker;
    });
    const controller = new AbortController();
    const promise = client.analyze("large snapshot", controller.signal);
    controller.abort();
    await expect(promise).rejects.toMatchObject({ name: "AbortError" });
    expect(workers).toHaveLength(2);
    expect(workers[0].requests.at(-1)).toMatchObject({ type: "cancel", targetId: 1 });
    expect(workers[0].terminate).toHaveBeenCalledOnce();
    client.terminate();
  });

  it("propagates Worker errors", async () => {
    const worker = new FakeWorker();
    const client = new AnalysisClient(() => worker as unknown as Worker);
    const promise = client.analyze("bad snapshot");
    worker.respond({ id: 1, ok: false, error: "invalid protocol" });
    await expect(promise).rejects.toThrow("invalid protocol");
    client.terminate();
  });
});
