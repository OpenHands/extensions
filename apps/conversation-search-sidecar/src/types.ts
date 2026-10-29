export interface AppMetadata { name: string; version: string; resolvedRef?: string | null }
export interface BackendMetadata { id?: string | null; kind?: string | null; orgId?: string | null }
export interface AgentServerRequest {
  path: string;
  method?: "GET" | "POST";
  body?: unknown;
  headers?: Record<string, string>;
}
export interface MountContext { container: HTMLElement; path: string; navigate: (path: string) => void }
export interface CanvasHost {
  apiVersion: string;
  extension: AppMetadata;
  backend: BackendMetadata;
  agentServer: { request<T = unknown>(request: AgentServerRequest): Promise<T> };
  registerPage: (id: string, mount: (context: MountContext) => void | (() => void)) => () => void;
  navigate: (path: string) => void;
}

export type LocationState = "ready" | "missing" | "empty" | "unreadable" | "unsupported";
export interface DataLocation {
  path: string;
  layout: string;
  state: LocationState;
  conversations: number;
  files: number;
  malformed: number;
  message?: string;
}
export interface ProbeStatus {
  os: string;
  arch: string;
  target: string;
  supported: boolean;
  goVersion: string | null;
  goReady: boolean;
  installed: boolean;
  runtimeVersion: string | null;
  binaryPresent: boolean;
  artifactPresent: boolean;
  artifactVerified: boolean;
  locations: DataLocation[];
}
export interface ServiceStatus {
  running: boolean;
  mode: "service" | "command";
  version: string;
  pid?: number;
  startedAt?: string;
  lastActivity?: string;
  idleSeconds?: number;
  idleShutdownSeconds: number;
}
export interface IndexStatus {
  ready: boolean;
  documents: number;
  sourceFiles: number;
  conversations: number;
  malformedFiles: number;
  indexBytes: number;
  lastIndexedAt?: string;
  locations: DataLocation[];
  service: ServiceStatus;
  added?: number;
  updated?: number;
  removed?: number;
  skipped?: number;
}
export interface SearchFilters { role?: string; kind?: string; tool?: string; after?: string; before?: string }
export interface SearchHit {
  id: string;
  score: number;
  conversationId: string;
  eventId: string;
  title: string;
  timestamp: string;
  role: string;
  kind: string;
  tool: string;
  sourcePath: string;
  excerpt: string;
  text?: string;
  summary?: string;
}
export interface SearchResponse { total: number; durationMs: number; hits: SearchHit[]; status: IndexStatus }
export interface NativeResponse { status?: IndexStatus; search?: SearchResponse; hit?: SearchHit; message?: string }
