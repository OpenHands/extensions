import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "playwright";

const source = await readFile(resolve(import.meta.dirname, "../extension.js"), "utf8");
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROME_PATH || undefined,
});

try {
  const page = await browser.newPage();
  await page.route("http://canvas.test/", (route) => route.fulfill({
    contentType: "text/html",
    body: '<main id="app"></main>',
  }));
  await page.goto("http://canvas.test/");
  await page.evaluate(async (extensionSource) => {
    const blobUrl = URL.createObjectURL(new Blob([extensionSource], { type: "text/javascript" }));
    const module = await import(blobUrl);
    let mountPage;
    let unregistered = false;
    window.terminalRequests = [];
    window.fetch = () => { throw new Error("Terminal must not use fetch."); };
    window.WebSocket = class { constructor() { throw new Error("Terminal must not use WebSocket."); } };
    const disposeActivation = module.activate({
      apiVersion: "1",
      extension: { name: "terminal", version: "0.5.0", resolvedRef: "smoke" },
      backend: { id: "smoke-backend", kind: "local", orgId: null },
      agentServer: {
        async request(request) {
          window.terminalRequests.push(request);
          if (request.path === "/api/file/home") return { home: "/workspace" };
          return { exit_code: 0, stdout: "__BLOB_COMMAND_OK__\n", stderr: "" };
        },
      },
      registerPage(id, mount) {
        if (id !== "terminal") throw new Error(`Unexpected page ID: ${id}`);
        mountPage = mount;
        return () => { unregistered = true; };
      },
    });
    if (typeof mountPage !== "function") throw new Error("Terminal page was not registered.");
    const container = document.querySelector("#app");
    window.disposeTerminalMount = mountPage({ container, path: "" });
    window.disposeTerminalActivation = () => {
      window.disposeTerminalMount?.();
      disposeActivation();
      if (!unregistered) throw new Error("Activation cleanup did not unregister the page.");
      URL.revokeObjectURL(blobUrl);
    };
  }, source);

  const textarea = page.locator(".terminal-shell__mount .xterm-helper-textarea");
  await textarea.waitFor({ timeout: 5_000 });
  await textarea.focus();
  await page.keyboard.type("printf smoke");
  await page.keyboard.press("Enter");
  await page.locator(".terminal-shell__mount .xterm-rows").filter({ hasText: "__BLOB_COMMAND_OK__" }).waitFor({ timeout: 5_000 });
  const result = await page.evaluate(() => {
    const container = document.querySelector("#app");
    if (container.querySelector("iframe")) throw new Error("Terminal rendered an iframe.");
    const requests = window.terminalRequests;
    window.disposeTerminalActivation?.();
    if (container.childElementCount !== 0) throw new Error("Mount cleanup left DOM behind.");
    return requests;
  });
  if (result.length !== 2 || result[1].path !== "/api/bash/execute_bash_command") {
    throw new Error(`Unexpected Host API requests: ${JSON.stringify(result)}`);
  }
  console.log("Blob smoke passed with bundled xterm and authenticated Host API command execution.");
} finally {
  await browser.close();
}
