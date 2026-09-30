// Is third-party iframe localStorage blocked by this Chromium build independent of Canvas/Agent Server?
import { chromium } from "/workspace/stack/oh/node_modules/playwright/index.mjs";
import http from "node:http";

const server = http.createServer((_q, r) => { r.setHeader("content-type", "text/html"); r.end("<p>x</p>"); }).listen(18999, "127.0.0.1");
const args = ["--no-sandbox", ...(process.argv[2] ? [process.argv[2]] : [])];
const browser = await chromium.launch({ executablePath: "/usr/bin/chromium", args });
console.log("chromium", browser.version(), "args", args.join(" "));
const page = await browser.newPage();
await page.goto("http://localhost:3001/robots.txt");
await page.evaluate(() => new Promise((ok) => {
  const f = document.createElement("iframe");
  f.sandbox = "allow-forms allow-modals allow-popups allow-same-origin allow-scripts";
  f.src = "http://127.0.0.1:18999/";
  f.onload = ok;
  document.body.append(f);
}));
const frame = page.frames().find((f) => f.url().includes("18999"));
console.log("3p iframe localStorage:", await frame.evaluate(() => { try { localStorage.setItem("k", "v"); return "ok"; } catch (e) { return "ERR " + e.message; } }));
await browser.close();
server.close();
