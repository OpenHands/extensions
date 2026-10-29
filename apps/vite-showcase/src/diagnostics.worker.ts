/// <reference lib="webworker" />

function fibonacci(input: number): number {
  let previous = 0;
  let current = 1;
  for (let index = 0; index < input; index += 1) {
    [previous, current] = [current, previous + current];
  }
  return previous;
}

self.addEventListener("message", (event: MessageEvent<{ input: number }>) => {
  const started = performance.now();
  const input = event.data.input;
  self.postMessage({
    input,
    value: fibonacci(input),
    durationMs: Number((performance.now() - started).toFixed(2)),
  });
});

export {};
