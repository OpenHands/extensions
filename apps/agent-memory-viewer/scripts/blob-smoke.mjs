import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import process from "node:process";
import { chromium } from "playwright-core";

const chrome = process.env.CHROME_PATH ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const source = await readFile(resolve(import.meta.dirname, "../extension.js"), "utf8");
const browser = await chromium.launch({ executablePath: chrome, headless: true });
try {
  const page = await browser.newPage();
  await page.setContent("<!doctype html><main id='mount'></main>");
  const result = await page.evaluate(async (bundle) => {
    const registrations = new Map();
    const url = URL.createObjectURL(new Blob([bundle], { type: "text/javascript" }));
    const request = async ({ path, body }) => {
      if (path === "/api/settings") return { agent_settings: { agent_context: { load_memory: true } } };
      if (path === "/api/file/home") return { home: "/home/agent" };
      if (path === "/api/workspaces") return { workspaces: [] };
      if (path.startsWith("/api/conversations/search")) return { items: [] };
      if (path.startsWith("/api/file/download")) return { content: "User memory" };
      if (path === "/api/bash/execute_bash_command") return { stdout: body.command.includes("os.listdir") ? "{\"/home/agent/.openhands/memory\":[]}" : "{}" };
      throw new Error(`Unexpected request: ${path}`);
    };
    const host = { apiVersion: "1", agentServer: { request }, registerPage(id, mount) { registrations.set(id, mount); return () => registrations.delete(id); } };
    const container = document.querySelector("#mount");
    try {
      const module = await import(url);
      const deactivate = module.activate(host);
      if (!registrations.has("memory")) throw new Error("Memory page was not registered.");
      const cleanup = registrations.get("memory")({ container, path: "", navigate() {} });
      await new Promise((resolveWait) => setTimeout(resolveWait, 50));
      if (!container.textContent.includes("User memory")) throw new Error("Memory page did not render.");
      cleanup();
      deactivate();
      if (container.childElementCount || registrations.size) throw new Error("Cleanup left mounted state.");
      return { pages: 1 };
    } finally {
      URL.revokeObjectURL(url);
    }
  }, source);
  console.log(`Blob smoke OK: ${result.pages} page registered, rendered, and cleaned up.`);
} finally {
  await browser.close();
}
