// Parse and render every catalog diagram with Canvas's Mermaid settings, report
// natural sizes, and save a contact sheet screenshot of all of them.
import { readdirSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(
  "/Users/VascoSchiavo/git/OpenHands/.claude/worktrees/canvas-mermaid/package.json",
);
const { chromium } = require("playwright");
const [catalogDir, outPath] = process.argv.slice(2);
const apiKey = readFileSync("/Users/VascoSchiavo/.openhands/agent-canvas/api-key.txt", "utf8").trim();
const origin = "http://localhost:8000";

const entries = readdirSync(catalogDir)
  .map((id) => {
    try {
      return JSON.parse(readFileSync(`${catalogDir}/${id}/manifest.json`, "utf8"));
    } catch {
      return null;
    }
  })
  .filter(Boolean)
  .map((e) => ({ id: e.id, diagram: e.diagram }));

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
await context.addInitScript(({ apiKey, origin }) => {
  const active = JSON.stringify({ backendId: "local", orgId: null });
  localStorage.setItem("openhands-onboarded", "1");
  localStorage.setItem("openhands-backends", JSON.stringify([{ id: "local", name: "Local", host: origin, apiKey, kind: "local" }]));
  localStorage.setItem("openhands-active-backend", active);
  sessionStorage.setItem("openhands-active-backend", active);
  localStorage.setItem("openhands-color-theme", "light-plus");
}, { apiKey, origin });
const page = await context.newPage();
const urls = [];
page.on("request", (r) => urls.push(r.url()));
await page.goto(`${origin}/automations/new/github-pr-reviewer`);
await page.getByTestId("mermaid-diagram").waitFor({ timeout: 60000 });
const entry = urls.find((u) => /\.vite\/deps\/mermaid\.js/.test(u));

const results = await page.evaluate(
  async ({ entry, entries }) => {
    const mermaid = (await import(entry)).default;
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme: "base",
      themeVariables: { fontSize: "13px", fontFamily: getComputedStyle(document.body).fontFamily },
      themeCSS: ".node rect { rx: 8px; ry: 8px; }",
      flowchart: { curve: "basis", padding: 10, nodeSpacing: 32, rankSpacing: 28, wrappingWidth: 260 },
    });
    document.body.innerHTML = "";
    const sheet = document.createElement("div");
    sheet.id = "sheet";
    sheet.style.cssText = "display:grid;grid-template-columns:repeat(5,300px);gap:12px;padding:12px;background:#fff;font:12px sans-serif";
    document.body.appendChild(sheet);
    const out = [];
    let n = 0;
    for (const { id, diagram } of entries) {
      n += 1;
      const ok = await mermaid.parse(diagram ?? "", { suppressErrors: true });
      if (!ok) {
        out.push({ id, ok: false });
        continue;
      }
      const { svg } = await mermaid.render(`v${n}`, diagram);
      const cell = document.createElement("div");
      cell.style.cssText = "border:1px solid #ddd;padding:6px";
      cell.innerHTML = `<div style="font-weight:600;margin-bottom:4px">${id}</div>${svg}`;
      const svgEl = cell.querySelector("svg");
      svgEl.style.maxHeight = "320px";
      sheet.appendChild(cell);
      const vb = svgEl.getAttribute("viewBox").split(" ").map(Number);
      out.push({ id, ok: true, width: Math.round(vb[2]), height: Math.round(vb[3]) });
    }
    return out;
  },
  { entry, entries },
);
for (const r of results) {
  const flag = !r.ok ? "PARSE ERROR" : r.width > 462 ? "TOO WIDE for dialog" : r.height > 520 ? "tall" : "ok";
  console.log(r.id.padEnd(52), r.ok ? `${r.width}x${r.height}` : "", flag);
}
await page.locator("#sheet").screenshot({ path: outPath });
await browser.close();
