import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import process from "node:process";
import { chromium } from "playwright-core";

const chrome = process.env.CHROME_PATH ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const bundle = await readFile(resolve(import.meta.dirname, "../extension.js"), "utf8");
const browser = await chromium.launch({ executablePath: chrome, headless: true });

try {
  const page = await browser.newPage();
  await page.setContent("<!doctype html><html><head></head><body><main id='mount'></main></body></html>");
  const result = await page.evaluate(async (source) => {
    const url = URL.createObjectURL(new Blob([source], { type: "text/javascript" }));
    const registrations = new Map();
    const navigation = [];
    const host = {
      apiVersion: "1",
      extension: { name: "vite-showcase", version: "0.1.0", resolvedRef: "blob-smoke" },
      backend: { id: "smoke-backend", kind: "local", orgId: null },
      registerPage(id, mount) { registrations.set(id, mount); return () => registrations.delete(id); },
      navigate(path) { navigation.push(path); },
    };
    try {
      const module = await import(url);
      const deactivate = module.activate(host);
      if (registrations.size !== 1 || !registrations.has("showcase")) throw new Error("Declared page was not registered.");
      const container = document.querySelector("#mount");
      const mount = registrations.get("showcase");
      const firstCleanup = mount({ container, path: "diagnostics", navigate: host.navigate });
      await new Promise((resolveWait) => setTimeout(resolveWait, 80));
      if (!container.textContent.includes("Runtime diagnostics")) throw new Error("Diagnostics route did not render.");
      if (!container.textContent.includes("fibonacci(32) = 2178309")) throw new Error("Inline Worker did not respond.");
      container.querySelector(".vs-brand").click();
      if (navigation.at(-1) !== "/extensions/vite-showcase/showcase") throw new Error("Root navigation failed.");
      firstCleanup();
      if (container.childElementCount !== 0) throw new Error("Mount cleanup left DOM behind.");
      const secondCleanup = mount({ container, path: "", navigate: host.navigate });
      await new Promise((resolveWait) => setTimeout(resolveWait, 20));
      if (!container.textContent.includes("Modern source")) throw new Error("Remount did not render overview.");
      secondCleanup();
      deactivate();
      if (registrations.size !== 0) throw new Error("Deactivation did not unregister the page.");
      return { navigation, bodyChildren: container.childElementCount };
    } finally {
      URL.revokeObjectURL(url);
    }
  }, bundle);
  if (result.bodyChildren !== 0) throw new Error("Smoke test finished with mounted DOM.");
  console.log(`Blob smoke OK: activate, diagnostics, Worker, navigate, dispose, and remount (${result.navigation.length} navigation).`);
} finally {
  await browser.close();
}
