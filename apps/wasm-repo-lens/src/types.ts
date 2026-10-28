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

export interface PrerequisiteStatus {
  git: boolean;
  rg: boolean;
}

export interface RankedMetric {
  name: string;
  files: number;
  bytes: number;
  percent: number;
}

export interface FileMetric {
  path: string;
  bytes: number;
  changes?: number;
  language?: string;
}

export interface DependencyMetric {
  name: string;
  source: string;
  kind: "dependency" | "import";
  references: number;
}

export interface RepositoryAnalysis {
  branch: string | null;
  files: number;
  bytes: number;
  sourceSamples: number;
  historyEntries: number;
  truncated: boolean;
  languages: RankedMetric[];
  directories: RankedMetric[];
  largeFiles: FileMetric[];
  churnHotspots: FileMetric[];
  dependencies: DependencyMetric[];
  imports: DependencyMetric[];
}

export type WorkerRequest =
  | { id: number; type: "analyze"; snapshot: string }
  | { id: number; type: "cancel"; targetId: number };

export type WorkerResponse =
  | { id: number; ok: true; data: RepositoryAnalysis }
  | { id: number; ok: false; error: string };
