export async function loadBuildInsight(signal: AbortSignal): Promise<string> {
  await new Promise<void>((resolve, reject) => {
    const timer = window.setTimeout(resolve, 40);
    signal.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timer);
        reject(new DOMException("The insight was cancelled.", "AbortError"));
      },
      { once: true },
    );
  });

  return "The lazy module resolved inside the same artifact—no network chunk was requested.";
}
