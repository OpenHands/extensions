import type {
  BranchInfo,
  CanvasHost,
  ChangedFile,
  CommitInfo,
  DiffStat,
  InstallerKind,
  PrerequisiteStatus,
  RepositorySnapshot,
  RepositoryStatus,
  WorkspaceCandidate,
} from "./types";

const MAX_WORKSPACE_PARENTS = 24;
const MAX_WORKSPACES = 240;

export const PROBE_COMMAND = String.raw`git_status=1
worktree_status=0
git_version=''
installer='none'
install_supported=0
if command -v git >/dev/null 2>&1; then
  git_status=0
  git_version=$(git --version 2>/dev/null || true)
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 && worktree_status=1
else
  if command -v brew >/dev/null 2>&1; then installer='brew'; install_supported=1
  elif command -v apt-get >/dev/null 2>&1; then installer='apt'
    if [ "$(id -u)" -eq 0 ] || (command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1); then install_supported=1; fi
  elif command -v dnf >/dev/null 2>&1; then installer='dnf'
    if [ "$(id -u)" -eq 0 ] || (command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1); then install_supported=1; fi
  elif command -v apk >/dev/null 2>&1; then installer='apk'
    if [ "$(id -u)" -eq 0 ] || (command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1); then install_supported=1; fi
  fi
fi
version64=$(printf '%s' "$git_version" | base64 | tr -d '\n')
printf 'GIT_COCKPIT_PROBE\t%s\t%s\t%s\t%s\t%s\n' "$git_status" "$worktree_status" "$installer" "$install_supported" "$version64"`;

export const STATUS_COMMAND = "GIT_OPTIONAL_LOCKS=0 git status --porcelain=v2 --branch -z --untracked-files=all";
export const BRANCHES_COMMAND = "git for-each-ref --sort=-committerdate --count=100 --format='R%00%(refname:short)%00%(objectname)%00%(HEAD)%00%(committerdate:iso-strict)%00' refs/heads refs/remotes";
export const LOG_COMMAND = "git log -n 30 --format='C%x00%H%x00%P%x00%an%x00%ae%x00%aI%x00%s%x00'";
export const DIFF_SUMMARY_COMMAND = String.raw`printf 'GIT_COCKPIT_UNSTAGED\0'
git diff --no-ext-diff --no-color --numstat -z -- .
printf 'GIT_COCKPIT_STAGED\0'
git diff --cached --no-ext-diff --no-color --numstat -z -- .`;

export const INSTALL_COMMANDS: Record<InstallerKind, string> = {
  brew: "brew install git",
  apt: String.raw`if [ "$(id -u)" -eq 0 ]; then apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y git; else sudo -n apt-get update && sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y git; fi`,
  dnf: String.raw`if [ "$(id -u)" -eq 0 ]; then dnf install -y git; else sudo -n dnf install -y git; fi`,
  apk: String.raw`if [ "$(id -u)" -eq 0 ]; then apk add git; else sudo -n apk add git; fi`,
};

export const SETUP_PROMPT = `Set up Git for Git Cockpit on this Agent Server. First inspect the operating system and available package manager. If Git is missing, explain the exact package-manager command and files it may change, obtain any needed approval, then install Git. Do not modify any repository files, Git refs, the index, remotes, credentials, or configuration. Verify with "git --version" and "git rev-parse --is-inside-work-tree" in the selected workspace, then report what changed.`;

interface WorkspaceResponse {
  workspaceParents?: Array<{ path?: unknown }>;
  workspaces?: Array<{ path?: unknown; name?: unknown }>;
}

interface SearchResponse {
  items?: Array<{ path?: unknown; name?: unknown; is_dir?: unknown }>;
}

interface CommandResponse {
  exit_code?: unknown;
  stdout?: unknown;
  stderr?: unknown;
}

function abortError(): DOMException {
  return new DOMException("The Agent Server request was cancelled.", "AbortError");
}

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) throw abortError();
}

function decodeBase64(value: string): string {
  try {
    const binary = atob(value);
    const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
    return new TextDecoder().decode(bytes);
  } catch {
    return "";
  }
}

function encodeBase64(value: string): string {
  const bytes = new TextEncoder().encode(value);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

export function isValidWorkspacePath(path: unknown): path is string {
  if (typeof path !== "string" || path.length < 2 || path.length > 4096 || !path.startsWith("/")) return false;
  if (/[\0-\x1f\x7f]/.test(path) || path.includes("//")) return false;
  const segments = path.split("/").filter(Boolean);
  return segments.length > 0 && segments.every((segment) => segment !== "." && segment !== "..");
}

export function isValidRepoPath(path: unknown): path is string {
  if (typeof path !== "string" || path.length === 0 || path.length > 4096 || path.startsWith("/")) return false;
  if (/[\0-\x1f\x7f]/.test(path) || path.includes("//")) return false;
  return path.split("/").every((segment) => segment.length > 0 && segment !== "." && segment !== "..");
}

export function workspaceToken(path: string): string {
  return encodeBase64(path).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/g, "");
}

export function pathToken(path: string): string {
  return workspaceToken(path);
}

function candidate(path: string, name?: unknown): WorkspaceCandidate {
  const fallback = path.split("/").filter(Boolean).at(-1) ?? path;
  return {
    path,
    name: typeof name === "string" && name.trim() ? name.trim() : fallback,
    token: workspaceToken(path),
  };
}

export async function listWorkspaces(host: CanvasHost, signal?: AbortSignal): Promise<WorkspaceCandidate[]> {
  throwIfAborted(signal);
  const response = await host.agentServer.request<WorkspaceResponse>({ path: "/api/workspaces" });
  throwIfAborted(signal);
  const found = new Map<string, WorkspaceCandidate>();

  for (const entry of response?.workspaces ?? []) {
    if (isValidWorkspacePath(entry.path)) found.set(entry.path, candidate(entry.path, entry.name));
  }

  const parents = (response?.workspaceParents ?? [])
    .map((entry) => entry.path)
    .filter(isValidWorkspacePath)
    .slice(0, MAX_WORKSPACE_PARENTS);

  const listings = await Promise.all(parents.map(async (parent) => {
    try {
      return await host.agentServer.request<SearchResponse>({
        path: `/api/file/search_subdirs?path=${encodeURIComponent(parent)}`,
      });
    } catch {
      return { items: [] } satisfies SearchResponse;
    }
  }));
  throwIfAborted(signal);

  for (const listing of listings) {
    for (const entry of listing.items ?? []) {
      if (isValidWorkspacePath(entry.path) && entry.is_dir !== false) {
        found.set(entry.path, candidate(entry.path, entry.name));
      }
    }
  }

  return [...found.values()]
    .sort((a, b) => a.name.localeCompare(b.name) || a.path.localeCompare(b.path))
    .slice(0, MAX_WORKSPACES);
}

async function executeControlled(
  host: CanvasHost,
  workspace: WorkspaceCandidate,
  command: string,
  timeout: number,
  signal?: AbortSignal,
): Promise<string> {
  if (!isValidWorkspacePath(workspace.path) || workspace.token !== workspaceToken(workspace.path)) {
    throw new Error("The selected workspace did not pass path validation. Refresh the workspace list and try again.");
  }
  throwIfAborted(signal);
  const response = await host.agentServer.request<CommandResponse>({
    path: "/api/bash/execute_bash_command",
    method: "POST",
    body: { command, cwd: workspace.path, timeout },
  });
  throwIfAborted(signal);
  const exitCode = typeof response?.exit_code === "number" ? response.exit_code : -1;
  const stdout = typeof response?.stdout === "string" ? response.stdout : "";
  const stderr = typeof response?.stderr === "string" ? response.stderr.trim() : "";
  if (exitCode !== 0) throw new Error(stderr || `The controlled Agent Server command failed with exit code ${exitCode}.`);
  return stdout;
}

export async function probePrerequisites(
  host: CanvasHost,
  workspace: WorkspaceCandidate,
  signal?: AbortSignal,
): Promise<PrerequisiteStatus> {
  const output = await executeControlled(host, workspace, PROBE_COMMAND, 10, signal);
  const match = output.match(/^GIT_COCKPIT_PROBE\t([01])\t([01])\t(brew|apt|dnf|apk|none)\t([01])\t([A-Za-z0-9+/=]*)$/m);
  if (!match) throw new Error("The Git prerequisite probe returned an unexpected response.");
  return {
    git: match[1] === "0",
    worktree: match[2] === "1",
    installer: match[3] === "none" ? null : match[3] as InstallerKind,
    installSupported: match[4] === "1",
    gitVersion: match[1] === "0" ? decodeBase64(match[5]) || "Git available" : null,
  };
}

export async function installGit(
  host: CanvasHost,
  workspace: WorkspaceCandidate,
  status: PrerequisiteStatus,
  signal?: AbortSignal,
): Promise<void> {
  if (status.git || !status.installer || !status.installSupported) {
    throw new Error("A supported Git install is not available for this Agent Server.");
  }
  await executeControlled(host, workspace, INSTALL_COMMANDS[status.installer], 180, signal);
}

export function parseStatus(output: string): RepositoryStatus {
  const status: RepositoryStatus = { branch: null, oid: null, upstream: null, ahead: 0, behind: 0, files: [] };
  const records = output.split("\0");
  for (let index = 0; index < records.length; index += 1) {
    const record = records[index];
    if (!record) continue;
    if (record.startsWith("# branch.oid ")) status.oid = record.slice(13) === "(initial)" ? null : record.slice(13);
    else if (record.startsWith("# branch.head ")) status.branch = record.slice(14) === "(detached)" ? null : record.slice(14);
    else if (record.startsWith("# branch.upstream ")) status.upstream = record.slice(18);
    else if (record.startsWith("# branch.ab ")) {
      const match = record.match(/\+(\d+) -(\d+)/);
      if (match) { status.ahead = Number(match[1]); status.behind = Number(match[2]); }
    } else if (record.startsWith("1 ")) {
      const parts = record.split(" ");
      const path = parts.slice(8).join(" ");
      if (isValidRepoPath(path)) status.files.push(changedFile(path, parts[1], "tracked"));
    } else if (record.startsWith("2 ")) {
      const parts = record.split(" ");
      const path = parts.slice(9).join(" ");
      const originalPath = records[index + 1];
      index += 1;
      if (isValidRepoPath(path) && isValidRepoPath(originalPath)) {
        status.files.push({ ...changedFile(path, parts[1], "renamed"), originalPath });
      }
    } else if (record.startsWith("? ")) {
      const path = record.slice(2);
      if (isValidRepoPath(path)) status.files.push(changedFile(path, "??", "untracked"));
    }
  }
  return status;
}

function changedFile(path: string, xy: string, kind: ChangedFile["kind"]): ChangedFile {
  return { path, index: xy[0] ?? ".", worktree: xy[1] ?? ".", kind };
}

function normalizedMarker(value: string): string {
  return value.replace(/^\n+/, "");
}

export function parseBranches(output: string): BranchInfo[] {
  const parts = output.split("\0");
  const branches: BranchInfo[] = [];
  for (let index = 0; index < parts.length; index += 1) {
    if (normalizedMarker(parts[index]) !== "R") continue;
    const [name, hash, head, committedAt] = parts.slice(index + 1, index + 5);
    if (name && /^[0-9a-f]{40}$/.test(hash ?? "")) {
      branches.push({ name, hash, current: head === "*", committedAt: committedAt ?? "" });
    }
    index += 4;
  }
  return branches;
}

export function parseLog(output: string): CommitInfo[] {
  const parts = output.split("\0");
  const commits: CommitInfo[] = [];
  for (let index = 0; index < parts.length; index += 1) {
    if (normalizedMarker(parts[index]) !== "C") continue;
    const [hash, parents, author, email, authoredAt, subject] = parts.slice(index + 1, index + 7);
    if (/^[0-9a-f]{40}$/.test(hash ?? "")) {
      commits.push({
        hash,
        parents: (parents ?? "").split(" ").filter((parent) => /^[0-9a-f]{40}$/.test(parent)),
        author: author ?? "",
        email: email ?? "",
        authoredAt: authoredAt ?? "",
        subject: subject ?? "",
        body: "",
      });
    }
    index += 6;
  }
  return commits;
}

export function parseDiffStats(output: string): DiffStat[] {
  const parts = output.split("\0");
  const stats: DiffStat[] = [];
  let staged = false;
  for (let index = 0; index < parts.length; index += 1) {
    const part = parts[index];
    if (part === "GIT_COCKPIT_UNSTAGED") { staged = false; continue; }
    if (part === "GIT_COCKPIT_STAGED") { staged = true; continue; }
    const match = part.match(/^([^\t]+)\t([^\t]+)\t(.*)$/s);
    if (!match) continue;
    let path = match[3];
    let previousPath: string | undefined;
    if (!path) {
      previousPath = parts[index + 1];
      path = parts[index + 2];
      index += 2;
    }
    if (!isValidRepoPath(path) || (previousPath && !isValidRepoPath(previousPath))) continue;
    stats.push({
      path,
      previousPath,
      additions: match[1] === "-" ? null : Number(match[1]),
      deletions: match[2] === "-" ? null : Number(match[2]),
      staged,
    });
  }
  return stats;
}

export async function loadRepository(
  host: CanvasHost,
  workspace: WorkspaceCandidate,
  signal?: AbortSignal,
): Promise<RepositorySnapshot> {
  const [status, branches, commits, diffStats] = await Promise.all([
    executeControlled(host, workspace, STATUS_COMMAND, 15, signal),
    executeControlled(host, workspace, BRANCHES_COMMAND, 15, signal),
    executeControlled(host, workspace, LOG_COMMAND, 20, signal),
    executeControlled(host, workspace, DIFF_SUMMARY_COMMAND, 20, signal),
  ]);
  return {
    status: parseStatus(status),
    branches: parseBranches(branches),
    commits: parseLog(commits),
    diffStats: parseDiffStats(diffStats),
  };
}

export function fileDiffCommand(path: string): string {
  if (!isValidRepoPath(path)) throw new Error("The requested file path did not pass validation.");
  const encoded = encodeBase64(path);
  if (!/^[A-Za-z0-9+/=]+$/.test(encoded)) throw new Error("The requested file path could not be safely encoded.");
  return String.raw`encoded_path='${encoded}'
if printf '%s' "$encoded_path" | base64 --decode >/dev/null 2>&1; then
  file_path=$(printf '%s' "$encoded_path" | base64 --decode)
else
  file_path=$(printf '%s' "$encoded_path" | base64 -D)
fi
{
  printf '%s\n' '--- Unstaged changes ---'
  git diff --no-ext-diff --no-color --unified=3 -- "$file_path"
  printf '%s\n' '--- Staged changes ---'
  git diff --cached --no-ext-diff --no-color --unified=3 -- "$file_path"
} | head -c 180000`;
}

export async function loadFileDiff(
  host: CanvasHost,
  workspace: WorkspaceCandidate,
  path: string,
  signal?: AbortSignal,
): Promise<string> {
  return executeControlled(host, workspace, fileDiffCommand(path), 20, signal);
}

export function commitDetailCommand(hash: string): string {
  if (!/^[0-9a-f]{40}$/.test(hash)) throw new Error("The requested commit ID did not pass validation.");
  return `git show --no-ext-diff --no-color --format=fuller --stat --summary --no-renames --max-count=1 ${hash} -- | head -c 180000`;
}

export async function loadCommitDetail(
  host: CanvasHost,
  workspace: WorkspaceCandidate,
  hash: string,
  signal?: AbortSignal,
): Promise<string> {
  return executeControlled(host, workspace, commitDetailCommand(hash), 20, signal);
}

export function installerExplanation(installer: InstallerKind): string {
  if (installer === "brew") return "Homebrew will download Git and its required formula dependencies into the Homebrew prefix.";
  if (installer === "apt") return "APT will refresh package indexes, download the Git package and dependencies, and update the system package database.";
  if (installer === "dnf") return "DNF will download the Git package and dependencies and update the system package database.";
  return "APK will download the Git package and dependencies and update the system package database.";
}
