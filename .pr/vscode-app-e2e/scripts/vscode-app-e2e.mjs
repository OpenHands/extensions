// Drives the real Agent Canvas Apps UI: install -> enable -> open page -> prepare/start -> OpenVSCode iframe.
import { chromium } from "/workspace/stack/oh/node_modules/playwright/index.mjs";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

const [source, label] = process.argv.slice(2);
const out = `/workspace/stack/e2e/out-${label}`;
const folder = "/workspace/stack/state/demo-folder";
mkdirSync(out, { recursive: true });
mkdirSync(folder, { recursive: true });
writeFileSync(`${folder}/HELLO_FROM_${label.toUpperCase()}.md`, `# ${label}\n`);

const log = [];
const note = (...args) => { const line = args.join(" "); log.push(line); console.log(line); };
const shot = async (page, name) => page.screenshot({ path: `${out}/${name}.png` });

const context = await chromium.launchPersistentContext(`${out}/profile`, {
  executablePath: "/usr/bin/chromium",
  args: ["--no-sandbox"],
  viewport: { width: 1440, height: 900 },
});
const page = context.pages()[0] ?? (await context.newPage());
page.on("pageerror", (e) => note("[pageerror]", e.message));
page.on("response", (r) => {
  const u = new URL(r.url());
  if (u.pathname.includes("canvas-extensions") || u.pathname.startsWith("/app-backends"))
    note("[http]", r.request().method(), `${u.origin}${u.pathname}`, r.status());
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
await page.getByTestId("canvas-extensions-screen").waitFor();
await shot(page, "01-apps-empty");

await page.getByRole("button", { name: "Add app" }).first().click();
const modal = page.getByTestId("add-canvas-extension-modal");
await modal.getByLabel("App source").fill(source);
await modal.getByRole("button", { name: "Install" }).click();
const card = page.getByTestId("canvas-extension-card-vscode");
await card.waitFor({ timeout: 60000 });
note("[card-after-install]", (await card.innerText()).replace(/\s+/g, " "));
await shot(page, "02-installed-disabled");

await card.getByRole("switch").or(card.getByLabel("Enable")).first().click();
await page.getByRole("button", { name: "Enable trusted app" }).click();
await card.getByText("Enabled").first().waitFor({ timeout: 30000 });
note("[card-after-enable]", (await card.innerText()).replace(/\s+/g, " "));
await shot(page, "03-enabled");

await page.goto("http://localhost:3001/extensions/vscode/editor", { waitUntil: "networkidle" });
await page.getByRole("heading", { name: "VS Code setup" }).waitFor({ timeout: 30000 });
note("[setup-panel]", (await page.locator("section[aria-live]").innerText()).replace(/\s+/g, " "));
await page.getByLabel("Workspace folder path").fill(folder);
await shot(page, "04-setup-panel");
await page.getByRole("button", { name: "Prepare and start" }).click();

const frame = page.locator("iframe").first();
await frame.waitFor({ timeout: 180000 });
const src = new URL(await frame.getAttribute("src"));
note("[iframe]", `${src.origin}${src.pathname}`, "folder=" + src.searchParams.get("folder"), "sandbox=" + (await frame.getAttribute("sandbox")));
const vscode = frame.contentFrame();
await vscode.locator(".monaco-workbench").waitFor({ timeout: 120000 });
await vscode.getByText(`HELLO_FROM_${label.toUpperCase()}.md`).first().waitFor({ timeout: 60000 });
note("[workbench]", "monaco-workbench rendered; explorer lists", `HELLO_FROM_${label.toUpperCase()}.md`);
const box = await frame.boundingBox();
note("[iframe-box]", JSON.stringify(box));
await page.waitForTimeout(3000);
await shot(page, "05-openvscode-ready");
const trust = vscode.getByRole("button", { name: "Yes, I trust the authors" });
if (await trust.isVisible().catch(() => false)) await trust.click();

await vscode.getByText(`HELLO_FROM_${label.toUpperCase()}.md`).first().click();
await vscode.locator(".monaco-editor .view-lines").first().waitFor({ timeout: 30000 });
note("[editor]", (await vscode.locator(".monaco-editor .view-lines").first().innerText()).trim());
await vscode.locator(".monaco-editor .view-lines").first().click();
await page.keyboard.press("Control+End");
await page.keyboard.type(`saved-from-canvas-${label}`);
await page.keyboard.press("Control+s");
await page.waitForTimeout(3000);
note("[disk-after-save]", JSON.stringify(readFileSync(`${folder}/HELLO_FROM_${label.toUpperCase()}.md`, "utf8")));
await shot(page, "06-file-edited-saved");

await page.goto("http://localhost:3001/apps", { waitUntil: "networkidle" });
await card.getByRole("switch").or(card.getByLabel("Disable")).first().click();
await card.getByText("Disabled").first().waitFor({ timeout: 30000 });
note("[card-after-disable]", (await card.innerText()).replace(/\s+/g, " "));
await page.goto("http://localhost:3001/extensions/vscode/editor", { waitUntil: "networkidle" });
await page.waitForTimeout(3000);
note("[route-after-disable]", "iframes=" + (await page.locator("iframe").count()), (await page.locator("main").first().innerText().catch(() => "")).replace(/\s+/g, " ").slice(0, 200));
await shot(page, "07-disabled-route");

writeFileSync(`${out}/log.txt`, log.join("\n") + "\n");
await context.close();
