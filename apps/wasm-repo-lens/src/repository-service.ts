import type { CanvasHost, PrerequisiteStatus, WorkspaceCandidate } from "./types";

const MAX_WORKSPACE_PARENTS = 24;
const MAX_WORKSPACES = 240;

export const PROBE_COMMAND = String.raw`git_status=1
rg_status=1
command -v git >/dev/null 2>&1 && git_status=0
command -v rg >/dev/null 2>&1 && rg_status=0
printf 'WASM_REPO_LENS_PROBE\t%s\t%s\n' "$git_status" "$rg_status"`;

export const SNAPSHOT_COMMAND = String.raw`printf 'V\t1\n'
branch=$(git branch --show-current 2>/dev/null || true)
printf 'B\t%s\n' "$(printf '%s' "$branch" | base64 | tr -d '\n')"
file_count=0
rg --files --hidden -0 -g '!.git/**' -g '!node_modules/**' -g '!target/**' -g '!dist/**' -g '!build/**' -g '!.next/**' -g '!.venv/**' -g '!venv/**' | while IFS= read -r -d '' file; do
  file_count=$((file_count + 1))
  [ "$file_count" -gt 5000 ] && printf 'T\tfiles\n' && break
  path64=$(printf '%s' "$file" | base64 | tr -d '\n')
  size=$(wc -c < "$file" 2>/dev/null | tr -d '[:space:]')
  [ -z "$size" ] && size=0
  printf 'F\t%s\t%s\n' "$path64" "$size"
done | awk 'BEGIN { total=0 } { size=length($0)+1; if (total+size > 300000) { print "T\tinventory-bytes"; exit } print; total+=size }'
git log -z --format= --name-only -n 200 -- . 2>/dev/null | while IFS= read -r -d '' file; do
  [ -z "$file" ] && continue
  printf 'H\t%s\n' "$(printf '%s' "$file" | base64 | tr -d '\n')"
done | awk 'BEGIN { total=0 } { size=length($0)+1; if (total+size > 150000) { print "T\thistory-bytes"; exit } print; total+=size }'
content_count=0
rg --files --hidden -0 -g '!.git/**' -g '!node_modules/**' -g '!target/**' -g '!dist/**' -g '!build/**' -g '!.next/**' -g '!.venv/**' -g '!venv/**' | while IFS= read -r -d '' file; do
  [ "$content_count" -ge 250 ] && break
  case "$file" in
    package.json|*/package.json|Cargo.toml|*/Cargo.toml|go.mod|*/go.mod|pyproject.toml|*/pyproject.toml|requirements.txt|*/requirements.txt|*.js|*.jsx|*.mjs|*.cjs|*.ts|*.tsx|*.py|*.rs|*.go|*.java|*.kt|*.kts|*.c|*.h|*.cc|*.cpp|*.cs|*.rb|*.php|*.swift|*.vue|*.svelte)
      path64=$(printf '%s' "$file" | base64 | tr -d '\n')
      content64=$(head -c 4096 "$file" 2>/dev/null | base64 | tr -d '\n')
      printf 'C\t%s\t%s\n' "$path64" "$content64"
      content_count=$((content_count + 1))
      ;;
  esac
done | awk 'BEGIN { total=0 } { size=length($0)+1; if (total+size > 350000) { print "T\tcontent-bytes"; exit } print; total+=size }'`;

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
  return new DOMException("The repository request was cancelled.", "AbortError");
}

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) throw abortError();
}

export function isValidWorkspacePath(path: unknown): path is string {
  if (typeof path !== "string" || path.length < 2 || path.length > 4096 || !path.startsWith("/")) return false;
  if (/[\0-\x1f\x7f]/.test(path) || path.includes("//")) return false;
  const segments = path.split("/").filter(Boolean);
  return segments.length > 0 && segments.every((segment) => segment !== "." && segment !== "..");
}

export function workspaceToken(path: string): string {
  const bytes = new TextEncoder().encode(path);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/g, "");
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

async function executeReadOnly(
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
  if (exitCode !== 0) throw new Error(stderr || `The Agent Server command failed with exit code ${exitCode}.`);
  return stdout;
}

export async function probePrerequisites(
  host: CanvasHost,
  workspace: WorkspaceCandidate,
  signal?: AbortSignal,
): Promise<PrerequisiteStatus> {
  const output = await executeReadOnly(host, workspace, PROBE_COMMAND, 10, signal);
  const match = output.match(/^WASM_REPO_LENS_PROBE\t([01])\t([01])$/m);
  if (!match) throw new Error("The prerequisite probe returned an unexpected response.");
  return { git: match[1] === "0", rg: match[2] === "0" };
}

export function gatherRepositorySnapshot(
  host: CanvasHost,
  workspace: WorkspaceCandidate,
  signal?: AbortSignal,
): Promise<string> {
  return executeReadOnly(host, workspace, SNAPSHOT_COMMAND, 45, signal);
}

export const SETUP_PROMPT = `Set up the prerequisites for WASM Repo Lens on this Agent Server. Check the operating system and package manager, then install git and ripgrep (the rg command) if either is missing. Do not modify any repository files. Verify with "git --version" and "rg --version", then report what changed.`;
