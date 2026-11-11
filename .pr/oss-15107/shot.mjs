// Screenshot the Slack install dialog of a mock Agent Canvas.
// Usage: node shot.mjs <canvas checkout> <base url> <output png> [connection option id]
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const [canvasDir, baseUrl, outPng, optionId] = process.argv.slice(2);
const require = createRequire(path.join(canvasDir, "package.json"));
const { chromium } = require("playwright");

function launchOptions() {
  // Fall back to a cached headless shell when the exact build is not cached.
  const cache = path.join(process.env.HOME, "Library/Caches/ms-playwright");
  const shells = fs
    .readdirSync(cache)
    .filter((name) => name.startsWith("chromium_headless_shell-"))
    .sort();
  for (const name of shells.reverse()) {
    const base = path.join(cache, name);
    for (const sub of fs.readdirSync(base)) {
      for (const bin of ["chrome-headless-shell", "headless_shell"]) {
        const candidate = path.join(base, sub, bin);
        if (fs.existsSync(candidate)) return { executablePath: candidate };
      }
    }
  }
  return {};
}

let browser;
try {
  browser = await chromium.launch();
} catch {
  browser = await chromium.launch(launchOptions());
}
const context = await browser.newContext({
  viewport: { width: 1280, height: 900 },
  deviceScaleFactor: 2,
});
const page = await context.newPage();
await page.addInitScript(() => {
  const backend = {
    id: "probe",
    name: "Local",
    host: window.location.origin,
    apiKey: "probe",
    kind: "local",
  };
  localStorage.setItem("openhands-onboarded", "1");
  localStorage.setItem("openhands-backends", JSON.stringify([backend]));
  const active = JSON.stringify({ backendId: "probe", orgId: null });
  localStorage.setItem("openhands-active-backend", active);
  sessionStorage.setItem("openhands-active-backend", active);
  localStorage.setItem(
    "openhands-sidebar-onboarding-checklist-dismissed",
    "true",
  );
});

await page.goto(`${baseUrl}/mcp`, { waitUntil: "domcontentloaded" });
const card = page.locator('[data-testid="mcp-marketplace-card-slack"]');
await card.waitFor({ state: "visible", timeout: 90_000 });

// The analytics consent dialog opens a few seconds after first render.
try {
  const confirm = page.getByText("Confirm preferences");
  await confirm.waitFor({ state: "visible", timeout: 8_000 });
  await confirm.click();
} catch {
  // not shown
}

await card.scrollIntoViewIfNeeded();
await card.click();
const modal = page.locator('[data-testid="mcp-install-modal"]');
await modal.waitFor({ state: "visible", timeout: 30_000 });
if (optionId) {
  await modal.locator(`[data-testid="mcp-install-option-${optionId}"]`).click();
}
await page.waitForTimeout(800);
await modal.screenshot({ path: outPng });

const text = (await modal.innerText()).replace(/\s+/g, " ").trim();
const fields = await modal
  .locator('[data-testid^="mcp-install-field-"]')
  .evaluateAll((nodes) => nodes.map((n) => n.getAttribute("data-testid")));
console.log(JSON.stringify({ outPng, fields, text }, null, 1));
await browser.close();
