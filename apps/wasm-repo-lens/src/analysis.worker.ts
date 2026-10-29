/// <reference lib="webworker" />

import wasmUrl from "./repo_lens_engine.wasm?url";
import type { RepositoryAnalysis, WorkerRequest, WorkerResponse } from "./types";

interface EngineExports extends WebAssembly.Exports {
  memory: WebAssembly.Memory;
  alloc(size: number): number;
  dealloc(pointer: number, size: number): void;
  analyze(pointer: number, size: number): number;
  result_ptr(): number;
  result_len(): number;
}

const workerScope: DedicatedWorkerGlobalScope = self as unknown as DedicatedWorkerGlobalScope;
let enginePromise: Promise<EngineExports> | null = null;
const cancelled = new Set<number>();

async function loadEngine(): Promise<EngineExports> {
  enginePromise ??= (async () => {
    if (typeof WebAssembly === "undefined") throw new Error("This browser does not support WebAssembly.");
    const response = await fetch(wasmUrl);
    if (!response.ok) throw new Error(`Embedded WASM could not be loaded (${response.status}).`);
    const bytes = await response.arrayBuffer();
    const instance = await WebAssembly.instantiate(bytes, {});
    return instance.instance.exports as EngineExports;
  })().catch((error: unknown) => {
    enginePromise = null;
    throw new Error(`The Rust analysis engine could not start: ${error instanceof Error ? error.message : String(error)}`);
  });
  return enginePromise;
}

async function analyze(snapshot: string): Promise<RepositoryAnalysis> {
  const engine = await loadEngine();
  const input = new TextEncoder().encode(snapshot);
  const pointer = engine.alloc(input.byteLength);
  if (!pointer && input.byteLength > 0) throw new Error("The Rust analysis engine could not allocate input memory.");
  try {
    new Uint8Array(engine.memory.buffer, pointer, input.byteLength).set(input);
    const status = engine.analyze(pointer, input.byteLength);
    const resultPointer = engine.result_ptr();
    const resultLength = engine.result_len();
    const output = new TextDecoder().decode(new Uint8Array(engine.memory.buffer, resultPointer, resultLength));
    if (status !== 0) throw new Error(output || "The Rust analysis engine rejected the repository snapshot.");
    return JSON.parse(output) as RepositoryAnalysis;
  } finally {
    engine.dealloc(pointer, input.byteLength);
  }
}

workerScope.onmessage = async (event: MessageEvent<WorkerRequest>) => {
  const request = event.data;
  if (request.type === "cancel") {
    cancelled.add(request.targetId);
    return;
  }
  if (cancelled.delete(request.id)) return;
  try {
    const data = await analyze(request.snapshot);
    if (cancelled.delete(request.id)) return;
    workerScope.postMessage({ id: request.id, ok: true, data } satisfies WorkerResponse);
  } catch (error) {
    if (cancelled.delete(request.id)) return;
    workerScope.postMessage({
      id: request.id,
      ok: false,
      error: error instanceof Error ? error.message : String(error),
    } satisfies WorkerResponse);
  }
};
