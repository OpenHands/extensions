import { describe, expect, it, vi } from "vitest";
import {
  BRANCHES_COMMAND,
  commitDetailCommand,
  DIFF_SUMMARY_COMMAND,
  fileDiffCommand,
  INSTALL_COMMANDS,
  installGit,
  isValidRepoPath,
  isValidWorkspacePath,
  listWorkspaces,
  loadCommitDetail,
  loadFileDiff,
  loadRepository,
  LOG_COMMAND,
  parseBranches,
  parseDiffStats,
  parseLog,
  parseStatus,
  PROBE_COMMAND,
  probePrerequisites,
  STATUS_COMMAND,
  workspaceToken,
} from "./git-service";
import type { CanvasHost, WorkspaceCandidate } from "./types";

const HASH = "a".repeat(40);
const PARENT = "b".repeat(40);
const WORKSPACE = "/workspace/demo";
const workspace: WorkspaceCandidate = { name: "demo", path: WORKSPACE, token: workspaceToken(WORKSPACE) };

const STATUS_OUTPUT = [
  `# branch.oid ${HASH}`,
  "# branch.head main",
  "# branch.upstream origin/main",
  "# branch.ab +2 -1",
  `1 .M N... 100644 100644 100644 ${HASH} ${HASH} src/app.ts`,
  `2 R. N... 100644 100644 100644 ${HASH} ${HASH} R100 src/new.ts`,
  "src/old.ts",
  "? notes.txt",
  "",
].join("\0");

const BRANCH_OUTPUT = ["R", "main", HASH, "*", "2026-09-09T12:00:00-04:00", "\nR", "origin/main", HASH, " ", "2026-09-09T12:00:00-04:00", "\n"].join("\0");
const LOG_OUTPUT = ["C", HASH, PARENT, "Ada Lovelace", "ada@example.com", "2026-09-09T12:00:00-04:00", "Build cockpit", "\n"].join("\0");
const DIFF_OUTPUT = ["GIT_COCKPIT_UNSTAGED", "3\t1\tsrc/app.ts", "0\t0\t", "src/old.ts", "src/new.ts", "GIT_COCKPIT_STAGED", "5\t2\tsrc/new.ts", ""].join("\0");

function hostWithRequest(request: (request: { path: string; method?: string; body?: unknown }) => Promise<unknown>): CanvasHost {
  return {
    apiVersion: "1",
    extension: { name: "git-cockpit", version: "0.1.0" },
    backend: { id: "local", kind: "local" },
    agentServer: { request: request as CanvasHost["agentServer"]["request"] },
    registerPage: vi.fn(),
    navigate: vi.fn(),
  };
}

describe("workspace boundaries", () => {
  it("discovers only validated Agent Server workspaces", async () => {
    const calls: unknown[] = [];
    const host = hostWithRequest(async (request) => {
      calls.push(request);
      if (request.path === "/api/workspaces") return { workspaceParents: [{ path: "/workspace" }, { path: "relative" }], workspaces: [{ path: "/direct/repo", name: "direct" }] };
      return { items: [{ path: WORKSPACE, name: "demo", is_dir: true }, { path: "/workspace/../escape", is_dir: true }, { path: "/workspace/file", is_dir: false }] };
    });
    await expect(listWorkspaces(host)).resolves.toEqual([
      expect.objectContaining({ name: "demo", path: WORKSPACE }),
      expect.objectContaining({ name: "direct", path: "/direct/repo" }),
    ]);
    expect(calls).toContainEqual({ path: "/api/file/search_subdirs?path=%2Fworkspace" });
  });

  it.each(["", "/", "relative", "/a/../b", "/a//b", "/a\nb", "/a/./b"])("rejects unsafe workspace %j", (path) => expect(isValidWorkspacePath(path)).toBe(false));
  it.each(["", "/absolute", "../escape", "a/../b", "a//b", "a\nb"])("rejects unsafe repository path %j", (path) => expect(isValidRepoPath(path)).toBe(false));
});

describe("prerequisite onboarding", () => {
  it("uses the exact non-mutating probe and parses Git readiness", async () => {
    const request = vi.fn(async () => ({ exit_code: 0, stdout: `GIT_COCKPIT_PROBE\t0\t1\tnone\t0\t${btoa("git version 2.51.0")}\n`, stderr: "" }));
    await expect(probePrerequisites(hostWithRequest(request), workspace)).resolves.toEqual({ git: true, gitVersion: "git version 2.51.0", worktree: true, installer: null, installSupported: false });
    expect(request).toHaveBeenCalledWith({ path: "/api/bash/execute_bash_command", method: "POST", body: { command: PROBE_COMMAND, cwd: WORKSPACE, timeout: 10 } });
  });

  it("requires supported missing-Git state and sends only a fixed installer template", async () => {
    const request = vi.fn(async () => ({ exit_code: 0, stdout: "", stderr: "" }));
    const host = hostWithRequest(request);
    const missing = { git: false, gitVersion: null, worktree: false, installer: "brew" as const, installSupported: true };
    await installGit(host, workspace, missing);
    expect(request).toHaveBeenCalledWith({ path: "/api/bash/execute_bash_command", method: "POST", body: { command: INSTALL_COMMANDS.brew, cwd: WORKSPACE, timeout: 180 } });
    await expect(installGit(host, workspace, { ...missing, git: true })).rejects.toThrow("not available");
  });

  it("surfaces malformed probes and command failures", async () => {
    await expect(probePrerequisites(hostWithRequest(async () => ({ exit_code: 0, stdout: "unexpected" })), workspace)).rejects.toThrow("unexpected response");
    await expect(probePrerequisites(hostWithRequest(async () => ({ exit_code: 9, stderr: "backend denied" })), workspace)).rejects.toThrow("backend denied");
  });
});

describe("Git protocol parsers", () => {
  it("parses branch metadata and tracked, renamed, and untracked status", () => {
    expect(parseStatus(STATUS_OUTPUT)).toEqual({
      branch: "main", oid: HASH, upstream: "origin/main", ahead: 2, behind: 1,
      files: [
        { path: "src/app.ts", index: ".", worktree: "M", kind: "tracked" },
        { path: "src/new.ts", originalPath: "src/old.ts", index: "R", worktree: ".", kind: "renamed" },
        { path: "notes.txt", index: "?", worktree: "?", kind: "untracked" },
      ],
    });
  });

  it("parses branches and bounded log metadata", () => {
    expect(parseBranches(BRANCH_OUTPUT)).toEqual([
      { name: "main", hash: HASH, current: true, committedAt: "2026-09-09T12:00:00-04:00" },
      { name: "origin/main", hash: HASH, current: false, committedAt: "2026-09-09T12:00:00-04:00" },
    ]);
    expect(parseLog(LOG_OUTPUT)).toEqual([{ hash: HASH, parents: [PARENT], author: "Ada Lovelace", email: "ada@example.com", authoredAt: "2026-09-09T12:00:00-04:00", subject: "Build cockpit", body: "" }]);
  });

  it("parses staged, unstaged, and rename numstat records", () => {
    expect(parseDiffStats(DIFF_OUTPUT)).toEqual([
      { path: "src/app.ts", additions: 3, deletions: 1, staged: false },
      { path: "src/new.ts", previousPath: "src/old.ts", additions: 0, deletions: 0, staged: false },
      { path: "src/new.ts", additions: 5, deletions: 2, staged: true },
    ]);
  });
});

describe("controlled read-only Git requests", () => {
  it("loads repository signals with only the four exact fixed templates", async () => {
    const request = vi.fn(async ({ body }: { body?: unknown }) => {
      const command = (body as { command: string }).command;
      const stdout = command === STATUS_COMMAND ? STATUS_OUTPUT : command === BRANCHES_COMMAND ? BRANCH_OUTPUT : command === LOG_COMMAND ? LOG_OUTPUT : DIFF_OUTPUT;
      return { exit_code: 0, stdout, stderr: "" };
    });
    const snapshot = await loadRepository(hostWithRequest(request), workspace);
    expect(snapshot.status.files).toHaveLength(3);
    expect(snapshot.branches).toHaveLength(2);
    expect(snapshot.commits).toHaveLength(1);
    expect(snapshot.diffStats).toHaveLength(3);
    expect(request.mock.calls.map(([call]) => (call.body as { command: string }).command)).toEqual([STATUS_COMMAND, BRANCHES_COMMAND, LOG_COMMAND, DIFF_SUMMARY_COMMAND]);
    expect(request.mock.calls.every(([call]) => (call.body as { cwd: string }).cwd === WORKSPACE)).toBe(true);
    expect([STATUS_COMMAND, BRANCHES_COMMAND, LOG_COMMAND, DIFF_SUMMARY_COMMAND].some((command) => command.includes(WORKSPACE))).toBe(false);
  });

  it("base64-encodes validated paths and only accepts full hashes", async () => {
    const trickyPath = "src/it's-$file.ts";
    const diffCommand = fileDiffCommand(trickyPath);
    expect(diffCommand).not.toContain(trickyPath);
    expect(diffCommand).toContain(btoa(trickyPath));
    expect(diffCommand).toContain('git diff --no-ext-diff --no-color --unified=3 -- "$file_path"');
    expect(() => fileDiffCommand("../escape")).toThrow("path");
    expect(() => commitDetailCommand("main")).toThrow("commit ID");
    expect(commitDetailCommand(HASH)).toContain(HASH);

    const request = vi.fn(async () => ({ exit_code: 0, stdout: "detail", stderr: "" }));
    const host = hostWithRequest(request);
    await expect(loadFileDiff(host, workspace, trickyPath)).resolves.toBe("detail");
    await expect(loadCommitDetail(host, workspace, HASH)).resolves.toBe("detail");
    expect(request).toHaveBeenCalledTimes(2);
  });

  it("rejects forged workspace candidates and cancellation", async () => {
    const host = hostWithRequest(async () => ({ exit_code: 0, stdout: "" }));
    await expect(loadRepository(host, { ...workspace, token: "forged" })).rejects.toThrow("path validation");
    const controller = new AbortController(); controller.abort();
    await expect(loadRepository(host, workspace, controller.signal)).rejects.toMatchObject({ name: "AbortError" });
  });
});
