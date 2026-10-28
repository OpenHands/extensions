import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import process from "node:process";
import { chromium } from "playwright-core";

const chrome = process.env.CHROME_PATH ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const bundle = await readFile(resolve(import.meta.dirname, "../extension.js"), "utf8");
const browser = await chromium.launch({ executablePath: chrome, headless: true });

try {
  const page = await browser.newPage();
  await page.route("http://git-cockpit.test/**", (route) => route.fulfill({
    status: 200,
    contentType: "text/html",
    body: "<!doctype html><html><head></head><body><main id='mount'></main></body></html>",
  }));
  await page.goto("http://git-cockpit.test/");

  const result = await page.evaluate(async (source) => {
    const workspace = "/workspace/demo";
    const token = btoa(workspace).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/g, "");
    const fileToken = btoa("src/app.ts").replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/g, "");
    const hash = "a".repeat(40);
    const parent = "b".repeat(40);
    const status = [
      `# branch.oid ${hash}`,
      "# branch.head main",
      "# branch.upstream origin/main",
      "# branch.ab +1 -0",
      `1 .M N... 100644 100644 100644 ${hash} ${hash} src/app.ts`,
      "? notes.txt",
      "",
    ].join("\0");
    const branches = ["R", "main", hash, "*", "2026-09-09T12:00:00-04:00", "\n"].join("\0");
    const log = ["C", hash, parent, "Ada Lovelace", "ada@example.com", "2026-09-09T12:00:00-04:00", "Build cockpit", "\n"].join("\0");
    const diff = ["GIT_COCKPIT_UNSTAGED", "4\t1\tsrc/app.ts", "GIT_COCKPIT_STAGED", ""].join("\0");
    const registrations = new Map();
    const requests = [];
    const bundleUrl = URL.createObjectURL(new Blob([source], { type: "text/javascript" }));
    const host = {
      apiVersion: "1",
      extension: { name: "git-cockpit", version: "0.1.0", resolvedRef: "blob-smoke" },
      backend: { id: "blob-local", kind: "local", orgId: null },
      agentServer: {
        async request(request) {
          requests.push(request);
          if (request.path === "/api/workspaces") return { workspaceParents: [{ path: "/workspace" }] };
          if (request.path.startsWith("/api/file/search_subdirs")) return { items: [{ path: workspace, name: "demo", is_dir: true }] };
          const command = request.body?.command ?? "";
          if (command.includes("GIT_COCKPIT_PROBE")) return { exit_code: 0, stdout: `GIT_COCKPIT_PROBE\t0\t1\tnone\t0\t${btoa("git version 2.51.0")}\n`, stderr: "" };
          if (command.includes("status --porcelain")) return { exit_code: 0, stdout: status, stderr: "" };
          if (command.includes("for-each-ref")) return { exit_code: 0, stdout: branches, stderr: "" };
          if (command.includes("log -n 30")) return { exit_code: 0, stdout: log, stderr: "" };
          if (command.includes("GIT_COCKPIT_UNSTAGED")) return { exit_code: 0, stdout: diff, stderr: "" };
          if (command.startsWith("encoded_path=")) return { exit_code: 0, stdout: "--- Unstaged changes ---\n@@ -1 +1 @@\n-old\n+new", stderr: "" };
          throw new Error(`Unexpected command: ${command}`);
        },
      },
      registerPage(id, mount) { registrations.set(id, mount); return () => registrations.delete(id); },
      navigate() {},
    };
    const container = document.querySelector("#mount");
    const waitFor = async (predicate, message) => {
      const deadline = performance.now() + 15000;
      while (!predicate()) {
        if (performance.now() > deadline) throw new Error(message);
        await new Promise((resolveWait) => setTimeout(resolveWait, 25));
      }
    };

    try {
      const module = await import(bundleUrl);
      const deactivate = module.activate(host);
      if (registrations.size !== 1 || !registrations.has("cockpit")) throw new Error("Declared page was not registered.");
      const mount = registrations.get("cockpit");

      const pickerCleanup = mount({ container, path: "", navigate() {} });
      await waitFor(() => container.querySelectorAll("select option").length === 2, "Workspace discovery did not render.");
      const planned = [...container.querySelectorAll('[data-testid="planned-write-operation"]')];
      if (planned.length !== 6 || planned.some((button) => !button.disabled)) throw new Error("Planned write controls were not all disabled.");
      const before = requests.length;
      planned.forEach((button) => { button.focus(); button.click(); });
      await new Promise((resolveWait) => setTimeout(resolveWait, 25));
      if (requests.length !== before) throw new Error("A planned write control initiated an Agent Server request.");
      pickerCleanup();
      if (container.childElementCount !== 0) throw new Error("Picker cleanup left DOM behind.");

      const dashboardCleanup = mount({ container, path: `workspace/${token}`, navigate() {} });
      await waitFor(() => container.textContent.includes("src/app.ts") && container.textContent.includes("Build cockpit") === false, "Repository dashboard did not render.");
      if (!container.textContent.includes("Changed files") || !container.textContent.includes("+4")) throw new Error("Parsed repository signals were not rendered.");
      const activeCommands = requests.filter((request) => request.path === "/api/bash/execute_bash_command");
      if (activeCommands.length !== 5) throw new Error(`Expected five probe/read commands, received ${activeCommands.length}.`);
      if (activeCommands.some((request) => request.body.cwd !== workspace || request.body.command.includes(workspace))) throw new Error("Workspace escaped the structured cwd boundary.");
      dashboardCleanup();

      const detailCleanup = mount({ container, path: `workspace/${token}/file/${fileToken}`, navigate() {} });
      await waitFor(() => container.querySelector('[data-testid="detail-output"]'), "Nested file diff did not render.");
      if (!container.textContent.includes("-old") || !container.textContent.includes("+new")) throw new Error("Individual file diff content was missing.");
      detailCleanup();

      const aboutCleanup = mount({ container, path: "about", navigate() {} });
      await waitFor(() => container.textContent.includes("A glass cockpit, not a terminal"), "Nested safety route did not render.");
      aboutCleanup();
      deactivate();
      if (registrations.size !== 0 || container.childElementCount !== 0) throw new Error("Final cleanup left registration or DOM behind.");
      return { planned: planned.length, commandCalls: requests.filter((request) => request.path === "/api/bash/execute_bash_command").length };
    } finally {
      URL.revokeObjectURL(bundleUrl);
    }
  }, bundle);

  console.log(`Blob smoke OK: ${result.commandCalls} controlled calls across dashboard/detail, ${result.planned} inert write placeholders, nested route and cleanup complete.`);
} finally {
  await browser.close();
}
