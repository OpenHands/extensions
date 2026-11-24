/* Load the checked-in bundle the way Canvas does (Blob URL import) in headless
   Chrome, then: open a stored board, draw a rectangle, confirm the autosave
   upload, create a board from the picker with real keystrokes (which must not
   reach Excalidraw's shortcuts), dispose, and remount. Set CHROME_PATH if
   Chrome is elsewhere. */

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";

const here = dirname(fileURLToPath(import.meta.url));
const MANIFEST = JSON.parse(readFileSync(join(here, "..", "canvas-extension.json"), "utf8"));
const bundle = readFileSync(join(here, "..", MANIFEST.entrypoint), "utf8");
const chrome = process.env.CHROME_PATH
  ?? ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome"]
    .find((path) => existsSync(path));
if (!chrome) throw new Error("Chrome not found; set CHROME_PATH.");

const browser = await chromium.launch({ executablePath: chrome, headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on("pageerror", (err) => errors.push(err.message));
  page.on("request", (req) => {
    if (!req.url().startsWith("data:") && !req.url().startsWith("blob:") && req.url() !== "about:blank") {
      errors.push(`unexpected network request: ${req.url()}`);
    }
  });
  await page.setContent("<!doctype html><html><head></head><body style='margin:0'><div id='mount'></div></body></html>");

  await page.evaluate(async (source) => {
    const stored = {
      type: "excalidraw",
      version: 2,
      source: "smoke",
      elements: [],
      appState: { viewBackgroundColor: "#ffffff" },
      files: {},
    };
    window.smoke = { uploads: [], files: new Map(), navigations: [], registrations: new Map() };
    const host = {
      apiVersion: "1",
      extension: { name: "whiteboard", version: "0.0.0", resolvedRef: "smoke" },
      backend: { id: "smoke", kind: "local", orgId: null },
      registerPage(id, mount) {
        window.smoke.registrations.set(id, mount);
        return () => window.smoke.registrations.delete(id);
      },
      navigate() {},
      agentServer: {
        async request({ path, body }) {
          const target = new URL(path, "http://x").searchParams.get("path");
          if (path === "/api/file/home") return { home: "/home/smoke" };
          if (path.startsWith("/api/file/download")) {
            if (window.smoke.files.has(target)) return window.smoke.files.get(target);
            if (target.endsWith("/default/board.excalidraw")) return JSON.stringify(stored);
            throw Object.assign(new Error("Not Found"), { status: 404 });
          }
          if (path.startsWith("/api/file/search_subdirs")) {
            const names = new Set(["default"]);
            for (const file of window.smoke.files.keys()) names.add(file.slice(target.length + 1).split("/")[0]);
            return { items: [...names].map((name) => ({ name, path: `${target}/${name}` })), next_page_id: null };
          }
          if (path.startsWith("/api/file/upload")) {
            const text = await body.get("file").text();
            // Controlled transport faults force races while running the real
            // bundled editor, save callbacks, and mount lifecycle unchanged.
            const gate = window.smoke.gate;
            if (gate && target.endsWith(gate.suffix)) {
              window.smoke.gate = null;
              gate.entered = true;
              await gate.released;
              if (gate.fail) throw new Error("Controlled upload failure");
            }
            window.smoke.files.set(target, text);
            if (target.endsWith("/board.excalidraw")) window.smoke.uploads.push(text);
          }
          return {};
        },
      },
    };
    const url = URL.createObjectURL(new Blob([source], { type: "text/javascript" }));
    const module = await import(url);
    URL.revokeObjectURL(url);
    window.smoke.holdUpload = (suffix, fail = false) => {
      const gate = { suffix, fail, entered: false };
      gate.released = new Promise((resolve) => { gate.release = resolve; });
      window.smoke.gate = window.smoke.held = gate;
    };
    window.smoke.reset = () => {
      window.smoke.cleanup?.();
      window.smoke.deactivate?.();
      window.smoke.files.clear();
      window.smoke.uploads.length = 0;
      window.smoke.navigations.length = 0;
      window.smoke.gate = window.smoke.held = null;
      try { localStorage.clear(); } catch { /* about:blank has no storage origin. */ }
      window.smoke.deactivate = module.activate(host);
      window.smoke.cleanup = window.smoke.mount();
    };
    window.smoke.deactivate = module.activate(host);
    window.smoke.mount = () => window.smoke.registrations.get("board")({
      container: document.querySelector("#mount"),
      path: "",
      navigate: (to) => window.smoke.navigations.push(to),
    });
    window.smoke.cleanup = window.smoke.mount();
  }, bundle);

  await page.waitForSelector(".excalidraw canvas", { timeout: 15000 });
  await page.waitForSelector(".whiteboard-app__status[data-state='saved']");

  await page.click('label:has([data-testid="toolbar-rectangle"])');
  await page.mouse.move(500, 300);
  await page.mouse.down();
  await page.mouse.move(700, 450, { steps: 5 });
  await page.mouse.up();
  await page.waitForFunction(() => window.smoke.uploads.length > 0, null, { timeout: 5000 });
  const saved = JSON.parse(await page.evaluate(() => window.smoke.uploads.at(-1)));
  if (saved.type !== "excalidraw" || saved.elements.filter((e) => e.type === "rectangle").length !== 1) {
    throw new Error(`Autosave did not contain the drawn rectangle: ${JSON.stringify(saved.elements)}`);
  }

  // At desktop width the picker sits beside Excalidraw's main-menu button.
  const placement = await page.$eval(".whiteboard-picker", (node) => ({
    placement: node.dataset.placement,
    besideMenu: !!node.parentElement?.querySelector(".main-menu-trigger, .dropdown-menu-button"),
  }));
  if (placement.placement !== "menu" || !placement.besideMenu) {
    throw new Error(`Board picker is not next to the main menu: ${JSON.stringify(placement)}`);
  }
  await page.click(".whiteboard-picker__trigger");
  await page.waitForSelector(".whiteboard-picker__item[aria-current='page']");
  await page.click(".whiteboard-picker__input");
  await page.keyboard.type("Sprint plan");
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => window.smoke.navigations.length > 0, null, { timeout: 5000 });
  const created = await page.evaluate(() => ({
    navigations: window.smoke.navigations,
    meta: [...window.smoke.files].find(([file]) => file.endsWith("/meta.json") && !file.includes("/default/")),
    selectionTool: document.querySelector("[data-testid='toolbar-selection']")?.checked,
  }));
  if (!/^\/extensions\/whiteboard\/boards\/sprint-plan-[a-z0-9]{4}$/.test(created.navigations[0])) {
    throw new Error(`Picker did not open the new board: ${JSON.stringify(created.navigations)}`);
  }
  if (!created.meta || JSON.parse(created.meta[1]).title !== "Sprint plan") {
    throw new Error("Picker did not store the new board's title.");
  }
  // Typing "Sprint plan" into Excalidraw would have switched tools ("a" = arrow, "l" = line).
  if (!created.selectionTool) throw new Error("Picker keystrokes leaked into Excalidraw shortcuts.");

  const leftovers = await page.evaluate(() => {
    window.smoke.cleanup();
    return document.querySelector("#mount").childElementCount
      + document.querySelectorAll("style[data-whiteboard]").length;
  });
  if (leftovers !== 0) throw new Error("Mount cleanup left DOM or styles behind.");

  const remountMs = await page.evaluate(async () => {
    const start = performance.now();
    window.smoke.cleanup = window.smoke.mount();
    while (!document.querySelector(".excalidraw canvas")) await new Promise((r) => setTimeout(r, 5));
    const elapsed = performance.now() - start;
    window.smoke.cleanup();
    window.smoke.deactivate();
    return elapsed;
  });
  const ready = async () => {
    await page.waitForSelector(".excalidraw canvas");
    await page.waitForSelector(".whiteboard-app__status[data-state='saved']");
  };
  const draw = async (x, y) => {
    await page.click('label:has([data-testid="toolbar-rectangle"])');
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x + 100, y + 100, { steps: 5 });
    await page.mouse.up();
    await page.waitForSelector(".whiteboard-app__status[data-state='saving']");
  };
  const waitForUploads = async (count) => {
    await page.waitForFunction((n) => window.smoke.uploads.length >= n, count);
  };
  const savedElements = () => page.evaluate(() => JSON.parse(window.smoke.uploads.at(-1)).elements);
  const metaPath = "/home/smoke/.openhands/apps/whiteboard/boards/default/meta.json";
  const regressions = {
    async "a failed older save never retries over a newer successful save"() {
      await draw(400, 250);
      await waitForUploads(1);
      await page.evaluate(() => window.smoke.holdUpload("/board.excalidraw", true));
      await draw(700, 250);
      await page.waitForFunction(() => window.smoke.held.entered);
      await draw(400, 450);
      // Let the newer scene enter the 800 ms save queue while its predecessor is blocked.
      await page.waitForTimeout(1100);
      await page.evaluate(() => window.smoke.held.release());
      await waitForUploads(2);
      const newer = await savedElements();
      assert.equal(newer.length, 3);
      await page.evaluate(() => {
        window.smoke.cleanup();
        window.smoke.cleanup = window.smoke.mount();
      });
      await ready();
      assert.deepEqual(await savedElements(), newer);
    },
    async "remounts wait for the departing mount's save"() {
      await draw(400, 250);
      await waitForUploads(1);
      await page.evaluate(() => window.smoke.holdUpload("/board.excalidraw"));
      await draw(700, 250);
      await page.evaluate(() => window.smoke.cleanup());
      await page.waitForFunction(() => window.smoke.held.entered);
      await page.evaluate(() => { window.smoke.cleanup = window.smoke.mount(); });
      // Give an uncoordinated mount time to read the old scene before releasing the write.
      await page.waitForTimeout(200);
      await page.evaluate(() => window.smoke.held.release());
      await ready();
      await waitForUploads(2);
      const before = await savedElements();
      assert.equal(before.length, 2);
      await draw(400, 450);
      await waitForUploads(3);
      const after = await savedElements();
      assert.equal(after.length, 3);
      assert.ok(before.every((element) => after.some((next) => next.id === element.id)));
    },
    async "a failed departing save is retried on return"() {
      await draw(400, 250);
      await waitForUploads(1);
      await page.evaluate(() => window.smoke.holdUpload("/board.excalidraw", true));
      await draw(700, 250);
      await page.evaluate(() => window.smoke.cleanup());
      await page.waitForFunction(() => window.smoke.held.entered);
      await page.evaluate(() => {
        window.smoke.held.release();
        window.smoke.cleanup = window.smoke.mount();
      });
      // The failed in-flight save retains its scene for this mount. An edit
      // retries it without dropping the shapes that were never written.
      await page.waitForSelector(".excalidraw canvas");
      await page.waitForSelector(".whiteboard-app__status[data-state='error']");
      await draw(400, 450);
      await waitForUploads(2);
      assert.equal((await savedElements()).length, 3);
    },
    async "autosave preserves a concurrent rename"() {
      await page.evaluate(() => window.smoke.holdUpload("/meta.json"));
      await draw(400, 250);
      await page.waitForFunction(() => window.smoke.held.entered);
      await page.click(".whiteboard-picker__trigger");
      await page.getByRole("button", { name: "Rename board", exact: true }).click();
      await page.getByPlaceholder("Board name", { exact: true }).fill("New title");
      await page.getByRole("button", { name: "Save", exact: true }).click();
      await page.waitForTimeout(200);
      await page.evaluate(() => window.smoke.held.release());
      await page.waitForFunction((path) => JSON.parse(window.smoke.files.get(path) ?? "{}").title === "New title", metaPath);
      await ready();
      assert.equal(await page.evaluate((path) => JSON.parse(window.smoke.files.get(path)).title, metaPath), "New title");
    },
    async "autosave preserves a concurrent archive"() {
      await page.evaluate(() => window.smoke.holdUpload("/meta.json"));
      await draw(400, 250);
      await page.waitForFunction(() => window.smoke.held.entered);
      await page.click(".whiteboard-picker__trigger");
      await page.getByRole("button", { name: "Archive board", exact: true }).click();
      await page.getByRole("button", { name: "Archive", exact: true }).click();
      await page.waitForTimeout(200);
      await page.evaluate(() => window.smoke.held.release());
      await page.waitForFunction(() => window.smoke.navigations.length > 0);
      await ready();
      assert.equal(await page.evaluate((path) => JSON.parse(window.smoke.files.get(path)).archived, metaPath), true);
    },
  };
  for (const [name, regression] of Object.entries(regressions)) {
    await page.evaluate(() => window.smoke.reset());
    await ready();
    try {
      await regression();
      console.log(`Persistence regression OK: ${name}.`);
    } catch (error) {
      errors.push(`${name}: ${error.message}`);
    } finally {
      await page.evaluate(() => window.smoke.held?.release());
    }
  }
  if (errors.length) throw new Error(errors.join("\n"));
  console.log(`Blob smoke OK: render, draw, autosave, create board, dispose, remount (${Math.round(remountMs)} ms).`);
} finally {
  await browser.close();
}
