export interface AppMetadata {
  name: string;
  version: string;
  resolvedRef?: string | null;
}

export interface BackendMetadata {
  id?: string | null;
  kind?: string | null;
  orgId?: string | null;
}

export interface AgentServerRequest {
  path: string;
  method?: "GET" | "POST";
  body?: unknown;
}

export interface CanvasHost {
  apiVersion: string;
  extension: AppMetadata;
  backend: BackendMetadata;
  agentServer: {
    request<T = unknown>(request: AgentServerRequest): Promise<T>;
  };
  registerPage: (id: string, mount: (context: MountContext) => void | (() => void)) => () => void;
  navigate: (path: string) => void;
}

export interface MountContext {
  container: HTMLElement;
  path: string;
  navigate: (path: string) => void;
}

export interface WorkspaceCandidate {
  name: string;
  path: string;
  token: string;
}

export type InstallerKind = "brew" | "apt" | "dnf" | "apk";

export interface PrerequisiteStatus {
  git: boolean;
  gitVersion: string | null;
  worktree: boolean;
  installer: InstallerKind | null;
  installSupported: boolean;
}

export interface RepositoryStatus {
  branch: string | null;
  oid: string | null;
  upstream: string | null;
  ahead: number;
  behind: number;
  files: ChangedFile[];
}

export interface ChangedFile {
  path: string;
  originalPath?: string;
  index: string;
  worktree: string;
  kind: "tracked" | "renamed" | "untracked";
}

export interface BranchInfo {
  name: string;
  hash: string;
  current: boolean;
  committedAt: string;
}

export interface CommitInfo {
  hash: string;
  parents: string[];
  author: string;
  email: string;
  authoredAt: string;
  subject: string;
  body: string;
}

export interface DiffStat {
  path: string;
  previousPath?: string;
  additions: number | null;
  deletions: number | null;
  staged: boolean;
}

export interface RepositorySnapshot {
  status: RepositoryStatus;
  branches: BranchInfo[];
  commits: CommitInfo[];
  diffStats: DiffStat[];
}
