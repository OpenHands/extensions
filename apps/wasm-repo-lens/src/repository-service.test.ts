import { describe, expect, it, vi } from "vitest";
import {
  gatherRepositorySnapshot,
  isValidWorkspacePath,
  listWorkspaces,
  PROBE_COMMAND,
  probePrerequisites,
  SNAPSHOT_COMMAND,
  workspaceToken,
} from "./repository-service";
import type { CanvasHost, WorkspaceCandidate } from "./types";

function hostWithRequest(request: (request: { path: string; method?: string; body?: unknown }) => Promise<unknown>): CanvasHost {
  return {
    apiVersion: "1",
    extension: { name: "wasm-repo-lens", version: "0.1.0" },
    backend: { id: "local", kind: "local" },
    agentServer: { request: request as CanvasHost["agentServer"]["request"] },
    registerPage: vi.fn(),
    navigate: vi.fn(),
  };
}

const workspace: WorkspaceCandidate = {
  name: "demo",
  path: "/workspace/demo",
  token: workspaceToken("/workspace/demo"),
};

describe("workspace discovery and validation", () => {
  it("lists validated direct and parent-directory workspaces", async () => {
    const calls: unknown[] = [];
    const host = hostWithRequest(async (request) => {
      calls.push(request);
      if (request.path === "/api/workspaces") {
        return {
          workspaceParents: [{ path: "/workspace" }, { path: "relative" }],
          workspaces: [{ path: "/direct/repo", name: "direct" }],
        } as never;
      }
      return { items: [
        { path: "/workspace/demo", name: "demo", is_dir: true },
        { path: "/workspace/../escape", name: "unsafe", is_dir: true },
        { path: "/workspace/file", name: "file", is_dir: false },
      ] } as never;
    });

    await expect(listWorkspaces(host)).resolves.toEqual([
      expect.objectContaining({ name: "demo", path: "/workspace/demo" }),
      expect.objectContaining({ name: "direct", path: "/direct/repo" }),
    ]);
    expect(calls).toContainEqual({ path: "/api/workspaces" });
    expect(calls).toContainEqual({ path: "/api/file/search_subdirs?path=%2Fworkspace" });
  });

  it.each(["", "/", "relative", "/a/../b", "/a//b", "/a\nb", "/a/./b"])("rejects unsafe workspace path %j", (path) => {
    expect(isValidWorkspacePath(path)).toBe(false);
  });

  it("surfaces workspace-list failures", async () => {
    const host = hostWithRequest(async () => { throw new Error("Agent Server unavailable"); });
    await expect(listWorkspaces(host)).rejects.toThrow("Agent Server unavailable");
  });
});

describe("controlled Agent Server commands", () => {
  it("uses the exact fixed probe request and parses missing prerequisites", async () => {
    const request = vi.fn(async () => ({
      exit_code: 0,
      stdout: "WASM_REPO_LENS_PROBE\t0\t1\n",
      stderr: "",
    }));
    await expect(probePrerequisites(hostWithRequest(request), workspace)).resolves.toEqual({ git: true, rg: false });
    expect(request).toHaveBeenCalledWith({
      path: "/api/bash/execute_bash_command",
      method: "POST",
      body: { command: PROBE_COMMAND, cwd: "/workspace/demo", timeout: 10 },
    });
  });

  it("uses the exact fixed snapshot request and does not put cwd in shell text", async () => {
    const request = vi.fn(async () => ({ exit_code: 0, stdout: "V\t1\n", stderr: "" }));
    await expect(gatherRepositorySnapshot(hostWithRequest(request), workspace)).resolves.toBe("V\t1\n");
    expect(SNAPSHOT_COMMAND).not.toContain(workspace.path);
    expect(SNAPSHOT_COMMAND).toContain("total+size > 300000");
    expect(SNAPSHOT_COMMAND).toContain("total+size > 150000");
    expect(SNAPSHOT_COMMAND).toContain("total+size > 350000");
    expect(SNAPSHOT_COMMAND).toContain("head -c 4096");
    expect(request).toHaveBeenCalledWith({
      path: "/api/bash/execute_bash_command",
      method: "POST",
      body: { command: SNAPSHOT_COMMAND, cwd: "/workspace/demo", timeout: 45 },
    });
  });

  it("rejects forged candidates, malformed probe output, command failures, and cancellation", async () => {
    const success = hostWithRequest(async () => ({ exit_code: 0, stdout: "unexpected", stderr: "" }) as never);
    await expect(probePrerequisites(success, { ...workspace, token: "forged" })).rejects.toThrow("path validation");
    await expect(probePrerequisites(success, workspace)).rejects.toThrow("unexpected response");

    const failed = hostWithRequest(async () => ({ exit_code: 7, stdout: "", stderr: "permission denied" }) as never);
    await expect(gatherRepositorySnapshot(failed, workspace)).rejects.toThrow("permission denied");

    const controller = new AbortController();
    controller.abort();
    await expect(probePrerequisites(success, workspace, controller.signal)).rejects.toMatchObject({ name: "AbortError" });
  });
});
