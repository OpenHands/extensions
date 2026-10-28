import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import process from "node:process";
import { chromium } from "playwright-core";

const chrome = process.env.CHROME_PATH ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const bundle = await readFile(resolve(import.meta.dirname, "../extension.js"), "utf8");
const browser = await chromium.launch({ executablePath: chrome, headless: true });

try {
  const page = await browser.newPage();
  await page.route("http://wasm-repo-lens.test/**", (route) => route.fulfill({
    status: 200,
    contentType: "text/html",
    body: "<!doctype html><html><head></head><body><main id='mount'></main></body></html>",
  }));
  await page.goto("http://wasm-repo-lens.test/");

  const result = await page.evaluate(async (source) => {
    const encode = (value) => btoa(unescape(encodeURIComponent(value)));
    const snapshot = [
      "V\t1",
      `B\t${encode("main")}`,
      `F\t${encode("src/App.tsx")}\t4096`,
      `F\t${encode("package.json")}\t256`,
      `C\t${encode("src/App.tsx")}\t${encode('import React from "react";\nexport function App() {}')}`,
      `C\t${encode("package.json")}\t${encode('{\n  "dependencies": {\n    "react": "^19.0.0"\n  }\n}')}`,
      `H\t${encode("src/App.tsx")}`,
      `H\t${encode("src/App.tsx")}`,
      "",
    ].join("\n");
    const bundleUrl = URL.createObjectURL(new Blob([source], { type: "text/javascript" }));
    const registrations = new Map();
    const requests = [];
    let activeWorkers = 0;
    const NativeWorker = Worker;
    class TrackedWorker extends NativeWorker {
      constructor(url, options) { super(url, options); activeWorkers += 1; }
      terminate() { activeWorkers -= 1; return super.terminate(); }
    }
    window.Worker = TrackedWorker;
    const host = {
      apiVersion: "1",
      extension: { name: "wasm-repo-lens", version: "0.1.0", resolvedRef: "blob-smoke" },
      backend: { id: "local-smoke", kind: "local", orgId: null },
      async request() { throw new Error("wrong request transport"); },
      agentServer: {
        async request(request) {
          requests.push(request);
          if (request.path === "/api/workspaces") return { workspaceParents: [{ path: "/workspace" }] };
          if (request.path.startsWith("/api/file/search_subdirs")) return { items: [{ path: "/workspace/demo", name: "demo", is_dir: true }] };
          if (request.body?.timeout === 10) return { exit_code: 0, stdout: "WASM_REPO_LENS_PROBE\t0\t0\n", stderr: "" };
          return { exit_code: 0, stdout: snapshot, stderr: "" };
        },
      },
      registerPage(id, mount) { registrations.set(id, mount); return () => registrations.delete(id); },
      navigate() {},
    };
    const container = document.querySelector("#mount");
    const waitFor = async (predicate, message) => {
      const deadline = performance.now() + 15000;
      while (!predicate()) {
        if (performance.now() > deadline) throw new Error(message);
        await new Promise((resolveWait) => setTimeout(resolveWait, 25));
      }
    };
    const token = btoa("/workspace/demo").replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/g, "");
    try {
      const module = await import(bundleUrl);
      const deactivate = module.activate(host);
      if (registrations.size !== 1 || !registrations.has("repo-lens")) throw new Error("Declared page was not registered.");
      const mount = registrations.get("repo-lens");

      const pickerCleanup = mount({ container, path: "", navigate() {} });
      await waitFor(() => container.querySelectorAll("select option").length === 2, "Workspace discovery did not render.");
      pickerCleanup();
      if (container.childElementCount !== 0 || activeWorkers !== 0) throw new Error("Picker cleanup left DOM or a Worker behind.");

      const analysisCleanup = mount({ container, path: `workspace/${token}`, navigate() {} });
      await waitFor(() => container.querySelector('[data-testid="analyze"]'), "Prerequisite probe did not enable analysis.");
      container.querySelector('[data-testid="analyze"]').click();
      await waitFor(() => container.querySelector('[data-testid="analysis-dashboard"]'), "Rust/WASM analysis did not render.");
      if (!container.textContent.includes("TypeScript") || !container.textContent.includes("react")) {
        throw new Error("Rust/WASM metrics were not rendered.");
      }
      const commandCalls = requests.filter((request) => request.path === "/api/bash/execute_bash_command");
      if (commandCalls.length !== 2) throw new Error("Expected exactly probe and snapshot commands.");
      if (commandCalls.some((request) => request.body.cwd !== "/workspace/demo" || request.body.command.includes("/workspace/demo"))) {
        throw new Error("Workspace path escaped the structured cwd boundary.");
      }
      analysisCleanup();

      const aboutCleanup = mount({ container, path: "about", navigate() {} });
      await waitFor(() => container.textContent.includes("Source crosses one boundary"), "Nested data-boundary route did not render.");
      aboutCleanup();
      deactivate();
      if (registrations.size !== 0 || activeWorkers !== 0 || container.childElementCount !== 0) {
        throw new Error("Final cleanup left registrations, Workers, or DOM behind.");
      }
      return { files: 2, commandCalls: commandCalls.length };
    } finally {
      window.Worker = NativeWorker;
      URL.revokeObjectURL(bundleUrl);
    }
  }, bundle);

  console.log(`Blob smoke OK: Rust/WASM analyzed ${result.files} files via ${result.commandCalls} fixed commands; nested route and cleanup complete.`);
} finally {
  await browser.close();
}
