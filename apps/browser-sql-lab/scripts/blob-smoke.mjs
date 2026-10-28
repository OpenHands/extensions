import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import process from "node:process";
import { chromium } from "playwright-core";

const chrome = process.env.CHROME_PATH ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const bundle = await readFile(resolve(import.meta.dirname, "../extension.js"), "utf8");
const browser = await chromium.launch({ executablePath: chrome, headless: true });

try {
  const page = await browser.newPage();
  await page.route("http://browser-sql-lab.test/**", (route) => route.fulfill({
    status: 200,
    contentType: "text/html",
    body: "<!doctype html><html><head></head><body><main id='mount'></main></body></html>",
  }));
  await page.goto("http://browser-sql-lab.test/");

  const result = await page.evaluate(async (source) => {
    const bundleUrl = URL.createObjectURL(new Blob([source], { type: "text/javascript" }));
    const registrations = new Map();
    const navigation = [];
    const suffix = `${Date.now()}-${Math.random()}`;
    let activeWorkers = 0;
    const NativeWorker = Worker;
    class TrackedWorker extends NativeWorker {
      constructor(url, options) {
        super(url, options);
        activeWorkers += 1;
      }
      terminate() {
        activeWorkers -= 1;
        return super.terminate();
      }
    }
    window.Worker = TrackedWorker;

    const host = {
      apiVersion: "1",
      extension: { name: "browser-sql-lab", version: "0.1.0", resolvedRef: "blob-smoke" },
      backend: { id: `smoke-a-${suffix}`, kind: "local", orgId: null },
      registerPage(id, mount) { registrations.set(id, mount); return () => registrations.delete(id); },
      navigate(path) { navigation.push(path); },
    };
    const container = document.querySelector("#mount");
    const waitFor = async (predicate, message) => {
      const deadline = performance.now() + 10000;
      while (!predicate()) {
        if (performance.now() > deadline) throw new Error(message);
        await new Promise((resolveWait) => setTimeout(resolveWait, 25));
      }
    };
    const setQuery = (sql) => {
      const editor = container.querySelector("textarea");
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
      setter.call(editor, sql);
      editor.dispatchEvent(new Event("input", { bubbles: true }));
    };
    const clickButton = (label) => {
      const button = [...container.querySelectorAll("button")].find((candidate) => candidate.textContent.includes(label));
      if (!button) throw new Error(`Could not find ${label} button.`);
      button.click();
    };

    try {
      const module = await import(bundleUrl);
      const deactivate = module.activate(host);
      if (registrations.size !== 1 || !registrations.has("sql-lab")) throw new Error("Declared page was not registered.");
      const mount = registrations.get("sql-lab");

      const firstCleanup = mount({ container, path: "", navigate: host.navigate });
      await waitFor(() => container.textContent.includes("SQL editor"), "SQLite WASM did not initialize.");
      if (!container.textContent.includes(`browser-sql-lab::smoke-a-${suffix}`)) throw new Error("Backend namespace was not rendered.");
      clickButton("Seed data");
      await waitFor(() => container.textContent.includes("Five embedded library records"), "Seed data was not saved.");
      clickButton("Run query");
      await waitFor(() => container.textContent.includes("Ursula K. Le Guin"), "Seeded query did not render results.");
      firstCleanup();
      if (container.childElementCount !== 0 || activeWorkers !== 0) throw new Error("First cleanup left DOM or a Worker behind.");

      const persistedCleanup = mount({ container, path: "", navigate: host.navigate });
      await waitFor(() => container.textContent.includes("SQL editor"), "Persisted database did not reopen.");
      setQuery("SELECT COUNT(*) AS total FROM books;");
      clickButton("Run query");
      await waitFor(() => container.querySelector("tbody")?.textContent.trim() === "5", "Rows did not survive remount.");
      persistedCleanup();

      host.backend.id = `smoke-b-${suffix}`;
      const isolatedCleanup = mount({ container, path: "about", navigate: host.navigate });
      await waitFor(() => container.textContent.includes("A real database, folded into one file."), "Nested About route did not render.");
      isolatedCleanup();
      const isolatedLabCleanup = mount({ container, path: "", navigate: host.navigate });
      await waitFor(() => container.textContent.includes("SQL editor"), "Second backend database did not initialize.");
      setQuery("SELECT COUNT(*) AS total FROM books;");
      clickButton("Run query");
      await waitFor(() => container.querySelector("tbody")?.textContent.trim() === "0", "Data crossed backend namespaces.");
      isolatedLabCleanup();

      deactivate();
      if (registrations.size !== 0 || activeWorkers !== 0 || container.childElementCount !== 0) {
        throw new Error("Final deactivation left registrations, Workers, or DOM behind.");
      }
      return { navigation, persistedRows: 5, isolatedRows: 0 };
    } finally {
      window.Worker = NativeWorker;
      URL.revokeObjectURL(bundleUrl);
    }
  }, bundle);

  console.log(`Blob smoke OK: WASM/Worker query, persisted ${result.persistedRows} rows, isolated backend had ${result.isolatedRows}, cleanup complete.`);
} finally {
  await browser.close();
}
