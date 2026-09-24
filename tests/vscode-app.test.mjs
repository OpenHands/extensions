import assert from "node:assert/strict";
import { activate } from "../apps/vscode/extension.js";

class Element {
  constructor(tag) { this.tagName = tag; this.children = []; this.listeners = {}; this.style = {}; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute() {}
  addEventListener(name, fn) { this.listeners[name] = fn; }
  async click() { await this.listeners.click(); }
}
class Document { createElement(tag) { return new Element(tag); } createTextNode(text) { return { textContent: text }; } }
const document = new Document();
globalThis.document = document;
globalThis.localStorage = { values: new Map(), getItem(k) { return this.values.get(k) ?? null; }, setItem(k, v) { this.values.set(k, v); }, removeItem(k) { this.values.delete(k); } };

const requests = [];
let status = { name: "vscode", state: "stopped", revision: "artifact-revision" };
const host = {
  backend: { id: "backend-a", orgId: "org-a" }, extension: { name: "vscode" },
  agentServer: { request: async ({ method, path, body }) => {
    requests.push({ method, path, body });
    if (method === "GET") return status;
    if (path.endsWith("/prepare")) return status;
    if (path.endsWith("/start")) { status = { ...status, state: "ready" }; return status; }
    return status;
  } },
  appBackendView: { mount: ({ container, query }) => { container.mountedQuery = query; return () => { container.disposed = true; }; } },
  registerPage: (_id, mount) => { host.mount = mount; return () => {}; },
};
await activate(host);
const container = new Element("main");
const dispose = await host.mount({ container });
assert.equal(container.children[0].children[0].children[0].textContent, "VS Code setup");
await container.children[0].children[0].children[3].children[0].click();
assert.deepEqual(requests.slice(0, 3).map(({ method, path, body }) => [method, path, body]), [
  ["GET", "/api/canvas-extensions/installed/vscode/backend", undefined],
  ["POST", "/api/canvas-extensions/installed/vscode/backend/prepare", { revision: "artifact-revision" }],
  ["POST", "/api/canvas-extensions/installed/vscode/backend/start", { revision: "artifact-revision" }],
]);
assert.equal(container.children[0].children[0].mountedQuery, undefined);
dispose();
console.log("VS Code App lifecycle behavior passed");
