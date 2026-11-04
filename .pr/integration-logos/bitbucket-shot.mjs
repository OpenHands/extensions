// Templates page filtered to Bitbucket, for the integration-logo evidence.
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(
  "/Users/VascoSchiavo/git/OpenHands/.claude/worktrees/collapse-script-files/package.json",
);
const { chromium } = require("playwright");
const [origin, out] = process.argv.slice(2);
const apiKey = readFileSync("/Users/VascoSchiavo/.openhands/agent-canvas/api-key.txt", "utf8").trim();

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 760 } });
await context.addInitScript(({ apiKey, origin }) => {
  const active = JSON.stringify({ backendId: "local", orgId: null });
  localStorage.setItem("openhands-onboarded", "1");
  localStorage.setItem("openhands-backends", JSON.stringify([{ id: "local", name: "Local", host: origin, apiKey, kind: "local" }]));
  localStorage.setItem("openhands-active-backend", active);
  sessionStorage.setItem("openhands-active-backend", active);
  localStorage.setItem("openhands-sidebar-onboarding-checklist-dismissed", "true");
}, { apiKey, origin });
const page = await context.newPage();
await page.goto(`${origin}/automations/templates`);
await page.getByRole("button", { name: "Confirm preferences" }).click({ timeout: 5000 }).catch(() => {});
await page.getByRole("button", { name: "Bitbucket" }).first().click({ timeout: 60000 });
await page.waitForTimeout(2000);
const imgs = await page.$$eval('[data-testid^="recommended-automation-icon-"] img', (els) =>
  els.map((e) => `${e.alt}:${e.naturalWidth > 0 ? "loaded" : "broken"}`),
);
console.log(origin, JSON.stringify(imgs));
await page.screenshot({ path: out, clip: { x: 620, y: 0, width: 660, height: 760 } });
await browser.close();
