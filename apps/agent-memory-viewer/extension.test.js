// @vitest-environment jsdom
import { describe, expect, it, vi } from "vitest";
import { activate } from "./extension.js";

function setup({ enabled = true, user = "User memory", project = "Project memory", userDaily = null, projectDaily = null, extra = null, userError, projectError, dailyFiles } = {}) {
  const value = (entry) => typeof entry === "function" ? entry() : entry;
  let mount;
  const unregister = vi.fn();
  const request = vi.fn(async ({ path, body }) => {
    if (path === "/api/settings") return { agent_settings: { agent_context: { load_memory: enabled } } };
    if (path === "/api/file/home") return { home_directory: "/home/agent" };
    if (path === "/api/workspaces") return { workspaces: [{ id: "/workspace/project", name: "project", path: "/workspace/project" }] };
    if (path.startsWith("/api/conversations/search")) return { items: [{ workspace: { working_dir: "/workspace/project", kind: "LocalWorkspace" } }], next_page_id: null };
    if (path === "/api/bash/execute_bash_command") {
      if (body?.command?.includes("os.listdir")) {
        return { stdout: JSON.stringify(dailyFiles || {
          "/home/agent/.openhands/memory": userDaily === null ? [] : ["2026-10-06.md", "ignore.txt"],
          "/workspace/project/.openhands/memory": projectDaily === null ? [] : ["2026-10-06.md"],
        }) };
      }
      return { stdout: body?.command === "pwd" ? "/workspace/agent-server\n" : "{}" };
    }
    if (path.includes("%2Fhome%2Fagent%2F.openhands%2Fmemory%2FMEMORY.md")) {
      if (userError) throw new Error(userError);
      if (user === null) throw new Error("404 Not Found");
      return { content: value(user), modified_at: "2026-10-06T12:00:00Z" };
    }
    if (path.includes("%2Fhome%2Fagent%2F.openhands%2Fmemory%2F2026-10-06.md")) {
      if (userDaily === null) throw new Error("404 Not Found");
      return { content: userDaily, modified_at: "2026-10-06T13:00:00Z" };
    }

    if (path.includes("%2Fworkspace%2Fproject%2F.openhands%2Fmemory%2FMEMORY.md")) {
      if (projectError) throw new Error(projectError);
      if (project === null) throw new Error("404 Not Found");
      return { content: value(project), last_modified: "2026-10-05T12:00:00Z" };
    }
    if (path.includes("%2Fworkspace%2Fproject%2F.openhands%2Fmemory%2F2026-10-06.md")) {
      if (projectDaily === null) throw new Error("404 Not Found");
      return { content: projectDaily, last_modified: "2026-10-06T14:00:00Z" };
    }

    if (path.includes("/extra%2F.openhands%2Fmemory%2FMEMORY.md")) {
      return { content: extra };
    }
    throw new Error(`Unexpected path: ${path}`);
  });
  const host = { apiVersion: "1", agentServer: { request }, registerPage: vi.fn((id, page) => { mount = page; return unregister; }) };
  return { host, request, unregister, getMount: () => mount };
}

async function mount(options) {
  const context = setup(options);
  const deactivate = activate(context.host);
  const container = document.createElement("div");
  const cleanup = context.getMount()({ container, path: "", navigate: vi.fn() });
  await vi.waitFor(() => expect(container.textContent).not.toContain("Loading memory"));
  return { ...context, deactivate, container, cleanup };
}

describe("Agent Memory viewer", () => {
  it("registers its page and returns its unregister cleanup", () => {
    const { host, unregister } = setup();
    const deactivate = activate(host);
    expect(host.registerPage).toHaveBeenCalledWith("memory", expect.any(Function));
    expect(deactivate).toBe(unregister);
  });

  it("discovers registered workspaces and renders their memory", async () => {
    const { container, request, cleanup } = await mount({ user: "User entry", project: "Project entry" });
    expect(container.textContent).toContain("user");
    expect(container.textContent).toContain("project");
    expect(container.textContent).toContain("/home/agent/.openhands/memory/MEMORY.md");
    expect(container.textContent).toContain("/workspace/project/.openhands/memory/MEMORY.md");
    expect(container.textContent).toContain("Workspace: /workspace/project");
    expect(container.textContent).toContain("User entry");
    expect(container.textContent).toContain("Project entry");
    expect(request).toHaveBeenCalledWith({ path: "/api/settings" });
    expect(request).toHaveBeenCalledWith({ path: "/api/file/home" });
    expect(request).toHaveBeenCalledWith({ path: "/api/workspaces" });
    expect(container.textContent).toContain("injected");
    const timestampProbe = request.mock.calls.find(([call]) => call.body?.command?.includes("os.path.getmtime"));
    expect(timestampProbe?.[0]).toMatchObject({ method: "POST" });
    cleanup();
    expect(container.childElementCount).toBe(0);
  });

  it("discovers and renders dated daily memory notes", async () => {
    const { container, request, cleanup } = await mount({
      user: "User index",
      project: "Project index",
      userDaily: "User daily note",
      projectDaily: "Project daily note",
    });
    expect(container.textContent).toContain("/home/agent/.openhands/memory/2026-10-06.md");
    expect(container.textContent).toContain("/workspace/project/.openhands/memory/2026-10-06.md");
    expect(container.textContent).toContain("User daily note");
    expect(container.textContent).toContain("Project daily note");
    expect(container.textContent).toContain("daily note");
    expect(container.textContent).toContain("read on demand and not injected automatically");
    expect(container.querySelectorAll("details.agent-memory__entry")).toHaveLength(4);
    const listProbe = request.mock.calls.find(([call]) => call.body?.command?.includes("os.listdir"));
    expect(listProbe?.[0]).toMatchObject({ method: "POST" });
    cleanup();
  });

  it("keeps readable daily note results when another memory directory is inaccessible", async () => {
    const { container, request, cleanup } = await mount({
      userDaily: "Readable user daily note",
      dailyFiles: { "/home/agent/.openhands/memory": ["2026-10-06.md"], "/workspace/project/.openhands/memory": [] },
    });
    expect(container.textContent).toContain("Readable user daily note");
    const listProbe = request.mock.calls.map(([call]) => call).find((call) => call.body?.command?.includes("os.listdir"));
    expect(listProbe.body.command).toContain("except OSError");
    cleanup();
  });



  it("starts collapsed and expands each entry when its header is clicked", async () => {
    const { container, cleanup } = await mount({ user: "User entry", project: "Project entry" });
    const details = Array.from(container.querySelectorAll("details.agent-memory__entry"));
    expect(details).toHaveLength(2);
    expect(details.every((node) => !node.open)).toBe(true);
    details[1].querySelector("summary").click();
    expect(details[1].open).toBe(true);
    expect(details[0].open).toBe(false);
    cleanup();
  });

  it("renders an explicit disabled state without reading memory files", async () => {
    const { container, request, cleanup } = await mount({ enabled: false });
    expect(container.textContent).toContain("Memory is disabled");
    expect(request.mock.calls.some(([call]) => call.path.includes("/api/file/download"))).toBe(false);
    cleanup();
  });

  it("renders an explicit empty state for absent files", async () => {
    const { container, cleanup } = await mount({ user: null, project: null });
    expect(container.textContent).toContain("No memory entries yet");
    cleanup();
  });

  it("refreshes with a cache-busted file request", async () => {
    let user = "Original memory";
    const { container, request, cleanup } = await mount({ user: () => user });
    user = "Updated memory";
    container.querySelector("button").click();
    await vi.waitFor(() => expect(container.textContent).toContain("Updated memory"));
    const downloads = request.mock.calls.map(([call]) => call).filter((call) => call.path.startsWith("/api/file/download"));
    expect(downloads).toHaveLength(4);
    expect(downloads[0].path).toMatch(/&_=/);
    expect(downloads[0].headers).toEqual({ "Cache-Control": "no-cache" });
    cleanup();
  });

  it("keeps readable entries and renders a failed source safely", async () => {
    const { container, cleanup } = await mount({ user: "User entry", projectError: "Access denied" });
    expect(container.textContent).toContain("User entry");
    expect(container.textContent).toContain("Could not read /workspace/project/.openhands/memory/MEMORY.md");
    expect(container.textContent).toContain("Access denied");
    cleanup();
  });

  it("renders errors safely and rejects incompatible hosts", async () => {
    expect(() => activate({ apiVersion: "2" })).toThrow(/host API 1/);
    const { container, cleanup } = await mount({ userError: "Access denied", projectError: "Access denied" });
    expect(container.textContent).toContain("Could not read /home/agent/.openhands/memory/MEMORY.md");
    expect(container.textContent).toContain("Access denied");
    cleanup();
  });
});