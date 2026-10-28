import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import manifest from "../canvas-extension.json";
import { normalizeRoute, ROOT_ROUTE } from "./App";
import { activate } from "./extension";
import {
  BRANCHES_COMMAND,
  DIFF_SUMMARY_COMMAND,
  INSTALL_COMMANDS,
  LOG_COMMAND,
  pathToken,
  PROBE_COMMAND,
  SETUP_PROMPT,
  STATUS_COMMAND,
  workspaceToken,
} from "./git-service";
import { preferenceKey } from "./preferences";
import type { AgentServerRequest, CanvasHost, MountContext } from "./types";

const WORKSPACE = "/workspace/demo";
const HASH = "a".repeat(40);
const PARENT = "b".repeat(40);
const TOKEN = workspaceToken(WORKSPACE);
const FILE_TOKEN = pathToken("src/app.ts");
const UNTRACKED_TOKEN = pathToken("notes.txt");
const STATUS_OUTPUT = [
  `# branch.oid ${HASH}`,
  "# branch.head main",
  "# branch.upstream origin/main",
  "# branch.ab +2 -1",
  `1 .M N... 100644 100644 100644 ${HASH} ${HASH} src/app.ts`,
  "? notes.txt",
  "",
].join("\0");
const BRANCH_OUTPUT = ["R", "main", HASH, "*", "2026-09-09T12:00:00-04:00", "\n"].join("\0");
const LOG_OUTPUT = ["C", HASH, PARENT, "Ada Lovelace", "ada@example.com", "2026-09-09T12:00:00-04:00", "Build cockpit", "\n"].join("\0");
const DIFF_OUTPUT = ["GIT_COCKPIT_UNSTAGED", "3\t1\tsrc/app.ts", "GIT_COCKPIT_STAGED", "",].join("\0");

interface HostOptions {
  probe?: string;
  failWorkspaces?: boolean;
  commandFailure?: string;
}

function makeHost(options: HostOptions = {}) {
  let mount: ((context: MountContext) => void | (() => void)) | undefined;
  const unregister = vi.fn();
  const requests: AgentServerRequest[] = [];
  const host: CanvasHost = {
    apiVersion: "1",
    extension: { name: "git-cockpit", version: "0.1.0", resolvedRef: "test" },
    backend: { id: "local-test", kind: "local", orgId: null },
    agentServer: {
      async request(request) {
        requests.push(request);
        if (request.path === "/api/workspaces") {
          if (options.failWorkspaces) throw new Error("Agent Server unavailable");
          return { workspaceParents: [{ path: "/workspace" }] } as never;
        }
        if (request.path.startsWith("/api/file/search_subdirs")) return { items: [{ path: WORKSPACE, name: "demo", is_dir: true }] } as never;
        const command = (request.body as { command: string }).command;
        if (command === PROBE_COMMAND) return { exit_code: 0, stdout: options.probe ?? `GIT_COCKPIT_PROBE\t0\t1\tnone\t0\t${btoa("git version 2.51.0")}\n`, stderr: "" } as never;
        if (command === INSTALL_COMMANDS.brew) return { exit_code: 0, stdout: "installed", stderr: "" } as never;
        if (options.commandFailure && command === STATUS_COMMAND) return { exit_code: 7, stdout: "", stderr: options.commandFailure } as never;
        if (command === STATUS_COMMAND) return { exit_code: 0, stdout: STATUS_OUTPUT, stderr: "" } as never;
        if (command === BRANCHES_COMMAND) return { exit_code: 0, stdout: BRANCH_OUTPUT, stderr: "" } as never;
        if (command === LOG_COMMAND) return { exit_code: 0, stdout: LOG_OUTPUT, stderr: "" } as never;
        if (command === DIFF_SUMMARY_COMMAND) return { exit_code: 0, stdout: DIFF_OUTPUT, stderr: "" } as never;
        if (command.startsWith("encoded_path=")) return { exit_code: 0, stdout: "--- Unstaged changes ---\n@@ -1 +1 @@\n-old\n+new", stderr: "" } as never;
        if (command.startsWith("git show")) return { exit_code: 0, stdout: `commit ${HASH}\nAuthor: Ada Lovelace\n\n Build cockpit`, stderr: "" } as never;
        throw new Error(`Unexpected command: ${command}`);
      },
    },
    registerPage: vi.fn((_id, callback) => { mount = callback; return unregister; }),
    navigate: vi.fn(),
  };
  return { host, unregister, requests, getMount: () => mount };
}

async function flush(rounds = 5) {
  for (let index = 0; index < rounds; index += 1) {
    await act(async () => { await Promise.resolve(); await new Promise((resolve) => setTimeout(resolve, 0)); });
  }
}

async function mountAt(path: string, options: HostOptions = {}) {
  const fixture = makeHost(options);
  const deactivate = activate(fixture.host);
  const container = document.createElement("div");
  const navigate = vi.fn();
  let cleanup: void | (() => void);
  await act(async () => { cleanup = fixture.getMount()!({ container, path, navigate }); });
  await flush();
  return { ...fixture, container, navigate, cleanup: cleanup!, deactivate };
}

beforeEach(() => {
  localStorage.clear();
  vi.mocked(navigator.clipboard.writeText).mockClear();
});

afterEach(() => vi.restoreAllMocks());

describe("Git Cockpit activation and routing", () => {
  it("registers exactly the declared page and unregisters on deactivation", () => {
    const { host, unregister } = makeHost();
    const deactivate = activate(host);
    expect(manifest.contributes.pages.map((page) => page.id)).toEqual(["cockpit"]);
    expect(host.registerPage).toHaveBeenCalledWith("cockpit", expect.any(Function));
    deactivate();
    expect(unregister).toHaveBeenCalledOnce();
  });

  it("rejects unsupported Canvas API versions", () => {
    const { host } = makeHost();
    host.apiVersion = "2";
    expect(() => activate(host)).toThrow("requires Canvas host API 1");
    expect(host.registerPage).not.toHaveBeenCalled();
  });

  it.each([
    ["", { view: "picker" }],
    ["cockpit", { view: "picker" }],
    [`workspace/${TOKEN}`, { view: "workspace", token: TOKEN, detail: null }],
    [`workspace/${TOKEN}/file/${FILE_TOKEN}`, { view: "workspace", token: TOKEN, detail: { kind: "file", value: FILE_TOKEN } }],
    [`workspace/${TOKEN}/commit/${HASH}`, { view: "workspace", token: TOKEN, detail: { kind: "commit", value: HASH } }],
    ["about", { view: "about" }],
    ["workspace/bad/token", { view: "not-found" }],
  ])("normalizes nested route %s", (path, expected) => expect(normalizeRoute(path)).toEqual(expected));

  it("uses the mount-context navigator for nested routes", async () => {
    const mounted = await mountAt("about");
    const button = [...mounted.container.querySelectorAll("button")].find((entry) => entry.textContent === "Choose a workspace")!;
    await act(async () => button.click());
    expect(mounted.navigate).toHaveBeenCalledWith(ROOT_ROUTE);
    await act(async () => mounted.cleanup()); mounted.deactivate();
  });
});

describe("read-only repository experience", () => {
  it("persists and navigates the selected Agent Server workspace", async () => {
    const mounted = await mountAt("");
    const select = mounted.container.querySelector("select") as HTMLSelectElement;
    select.value = TOKEN;
    await act(async () => select.dispatchEvent(new Event("change", { bubbles: true })));
    expect(mounted.navigate).toHaveBeenCalledWith(`${ROOT_ROUTE}/workspace/${TOKEN}`);
    expect(JSON.parse(localStorage.getItem(preferenceKey(mounted.host.backend))!)).toMatchObject({ workspaceToken: TOKEN });
    await act(async () => mounted.cleanup()); mounted.deactivate();
  });

  it("renders the dashboard from fixed status, branch, log, and diff commands", async () => {
    const mounted = await mountAt(`workspace/${TOKEN}`);
    expect(mounted.container.textContent).toContain("Changed files");
    expect(mounted.container.textContent).toContain("src/app.ts");
    expect(mounted.container.textContent).toContain("+3");
    expect(mounted.container.textContent).toContain("origin/main");
    const commandCalls = mounted.requests.filter((request) => request.path === "/api/bash/execute_bash_command");
    expect(commandCalls.map((request) => (request.body as { command: string }).command)).toEqual([PROBE_COMMAND, STATUS_COMMAND, BRANCHES_COMMAND, LOG_COMMAND, DIFF_SUMMARY_COMMAND]);
    expect(commandCalls.every((request) => (request.body as { cwd: string }).cwd === WORKSPACE)).toBe(true);

    const file = [...mounted.container.querySelectorAll("button")].find((entry) => entry.textContent?.includes("src/app.ts"))!;
    await act(async () => file.click());
    expect(mounted.navigate).toHaveBeenCalledWith(`${ROOT_ROUTE}/workspace/${TOKEN}/file/${FILE_TOKEN}`);

    const history = [...mounted.container.querySelectorAll("button")].find((entry) => entry.textContent === "history")!;
    await act(async () => history.click());
    expect(mounted.container.textContent).toContain("Build cockpit");
    expect(JSON.parse(localStorage.getItem(preferenceKey(mounted.host.backend))!)).toMatchObject({ tab: "history" });
    const commit = [...mounted.container.querySelectorAll("button")].find((entry) => entry.textContent?.includes("Build cockpit"))!;
    await act(async () => commit.click());
    expect(mounted.navigate).toHaveBeenCalledWith(`${ROOT_ROUTE}/workspace/${TOKEN}/commit/${HASH}`);
    await act(async () => mounted.cleanup()); mounted.deactivate();
  });

  it("loads validated individual file diffs and recent commit detail", async () => {
    const file = await mountAt(`workspace/${TOKEN}/file/${FILE_TOKEN}`);
    expect(file.container.querySelector('[data-testid="detail-output"]')?.textContent).toContain("-old");
    const fileCommands = file.requests.filter((request) => request.path === "/api/bash/execute_bash_command");
    expect(fileCommands).toHaveLength(6);
    expect((fileCommands.at(-1)?.body as { command: string }).command).not.toContain("src/app.ts");
    await act(async () => file.cleanup()); file.deactivate();

    const commit = await mountAt(`workspace/${TOKEN}/commit/${HASH}`);
    expect(commit.container.querySelector('[data-testid="detail-output"]')?.textContent).toContain(`commit ${HASH}`);
    expect(commit.requests.filter((request) => request.path === "/api/bash/execute_bash_command")).toHaveLength(6);
    await act(async () => commit.cleanup()); commit.deactivate();
  });

  it("explains untracked files without issuing a detail command", async () => {
    const mounted = await mountAt(`workspace/${TOKEN}/file/${UNTRACKED_TOKEN}`);
    expect(mounted.container.textContent).toContain("Untracked files have no Git diff until they are staged");
    expect(mounted.requests.filter((request) => request.path === "/api/bash/execute_bash_command")).toHaveLength(5);
    await act(async () => mounted.cleanup()); mounted.deactivate();
  });

  it("renders non-zero command failures as a helpful state", async () => {
    const mounted = await mountAt(`workspace/${TOKEN}`, { commandFailure: "permission denied by backend" });
    expect(mounted.container.textContent).toContain("Repository signals failed");
    expect(mounted.container.textContent).toContain("permission denied by backend");
    await act(async () => mounted.cleanup()); mounted.deactivate();
  });
});

describe("safe onboarding and planned controls", () => {
  it("shows missing Git, copies the fixed prompt, and gates the fixed installer", async () => {
    const mounted = await mountAt(`workspace/${TOKEN}`, { probe: "GIT_COCKPIT_PROBE\t1\t0\tbrew\t1\t\n" });
    expect(mounted.container.textContent).toContain("Install Git deliberately");
    expect(mounted.container.textContent).toContain("Homebrew will download Git");
    const install = [...mounted.container.querySelectorAll("button")].find((entry) => entry.textContent === "Install Git with brew") as HTMLButtonElement;
    expect(install.disabled).toBe(true);
    const checkbox = mounted.container.querySelector('input[type="checkbox"]') as HTMLInputElement;
    await act(async () => { checkbox.click(); });
    expect(install.disabled).toBe(false);

    const copy = [...mounted.container.querySelectorAll("button")].find((entry) => entry.textContent === "Copy agent setup prompt")!;
    await act(async () => copy.click());
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(SETUP_PROMPT);
    expect(mounted.container.textContent).toContain("Setup prompt copied.");

    await act(async () => install.click());
    await flush();
    const commands = mounted.requests.filter((request) => request.path === "/api/bash/execute_bash_command").map((request) => (request.body as { command: string }).command);
    expect(commands).toContain(INSTALL_COMMANDS.brew);
    await act(async () => mounted.cleanup()); mounted.deactivate();
  });

  it("renders every write placeholder disabled and cannot initiate a request on click or focus", async () => {
    const mounted = await mountAt("");
    const placeholders = [...mounted.container.querySelectorAll('[data-testid="planned-write-operation"]')] as HTMLButtonElement[];
    expect(placeholders).toHaveLength(6);
    expect(placeholders.every((button) => button.disabled)).toBe(true);
    expect(mounted.container.textContent).toContain("Not available yet.");
    expect(mounted.container.textContent).toContain("explicit confirmation and carefully scoped safety checks");
    const before = mounted.requests.length;
    for (const button of placeholders) { button.focus(); button.click(); }
    await flush();
    expect(mounted.requests).toHaveLength(before);
    await act(async () => mounted.cleanup()); mounted.deactivate();
  });

  it("renders workspace failures and removes mounted DOM on cleanup", async () => {
    const mounted = await mountAt("", { failWorkspaces: true });
    expect(mounted.container.textContent).toContain("Workspace discovery failed");
    await act(async () => mounted.cleanup());
    expect(mounted.container.childElementCount).toBe(0);
    mounted.deactivate();
    expect(mounted.unregister).toHaveBeenCalledOnce();
  });
});
