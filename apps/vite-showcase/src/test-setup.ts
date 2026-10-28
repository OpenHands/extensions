import { vi } from "vitest";

export const fakeWorkers: FakeWorker[] = [];

export class FakeWorker {
  private listeners = new Set<(event: MessageEvent) => void>();
  constructor() { fakeWorkers.push(this); }
  terminate = vi.fn();
  addEventListener = vi.fn((_type: string, listener: (event: MessageEvent) => void) => this.listeners.add(listener));
  removeEventListener = vi.fn((_type: string, listener: (event: MessageEvent) => void) => this.listeners.delete(listener));
  postMessage = vi.fn(() => {
    queueMicrotask(() => {
      for (const listener of this.listeners) {
        listener(new MessageEvent("message", { data: { input: 32, value: 2178309, durationMs: 0.2 } }));
      }
    });
  });
}

vi.mock("./diagnostics.worker?worker&inline", () => ({ default: FakeWorker }));
