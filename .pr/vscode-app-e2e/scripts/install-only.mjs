// Install a source through the real Customize -> Apps modal and report the outcome.
import { chromium } from "/workspace/stack/oh/node_modules/playwright/index.mjs";
import { mkdirSync, writeFileSync } from "node:fs";

const [label, source, ref = "", repoPath = ""] = process.argv.slice(2);
const out = `/workspace/stack/e2e/out-${label}`;
mkdirSync(out, { recursive: true });
const log = [];
const note = (...a) => { const l = a.join(" "); log.push(l); console.log(l); };

const context = await chromium.launchPersistentContext(`${out}/profile`, {
  executablePath: "/usr/bin/chromium", args: ["--no-sandbox"], viewport: { width: 1440, height: 900 },
});
const page = context.pages()[0] ?? (await context.newPage());
page.on("response", async (r) => {
  if (r.url().includes("/api/canvas-extensions/install"))
    note("[http]", r.request().method(), new URL(r.url()).pathname, r.status(), (await r.text().catch(() => "")).slice(0, 300));
});
await page.goto("http://localhost:3001/apps", { waitUntil: "networkidle" });
const telemetry = page.getByRole("checkbox", { name: "Send anonymous usage data" });
if (await telemetry.isVisible().catch(() => false)) {
  await telemetry.uncheck();
  await page.getByRole("button", { name: "Confirm preferences" }).click();
}
const skip = page.getByText("Skip for now");
if (await skip.isVisible({ timeout: 5000 }).catch(() => false)) await skip.click();
await page.goto("http://localhost:3001/apps", { waitUntil: "networkidle" });
await page.getByRole("button", { name: "Add app" }).first().click();
const modal = page.getByTestId("add-canvas-extension-modal");
await modal.getByLabel("App source").fill(source);
if (ref) await modal.getByLabel(/Ref/i).fill(ref);
if (repoPath) await modal.getByLabel(/Path/i).fill(repoPath);
await modal.getByRole("button", { name: "Install" }).click();
await page.waitForTimeout(20000);
const card = page.getByTestId("canvas-extension-card-vscode");
note("[card]", (await card.count()) ? (await card.innerText()).replace(/\s+/g, " ") : "none");
await page.screenshot({ path: `${out}/install.png` });
writeFileSync(`${out}/log.txt`, log.join("\n") + "\n");
await context.close();
