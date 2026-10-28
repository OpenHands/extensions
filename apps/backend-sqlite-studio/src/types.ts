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

export interface ProbeStatus {
  pythonReady: boolean;
  pythonVersion: string | null;
  sqliteModuleVersion: string | null;
  sqliteCliVersion: string | null;
  initialized: boolean;
  wrapperPresent: boolean;
  databasePresent: boolean;
  runtimeVersion: string | null;
}
export interface SchemaColumn { name: string; type: string; nullable: boolean; primaryKey: boolean }
export interface SchemaTable { name: string; sql: string; columns: SchemaColumn[] }
export interface MigrationRecord { id: string; appliedAt: string }
export interface HistoryRecord { id: number; sql: string; status: "success" | "error"; executedAt: string; message: string }
export interface DatabaseSnapshot {
  initialized: boolean;
  databasePath: string;
  sizeBytes: number;
  journalMode: string;
  tables: SchemaTable[];
  migrations: MigrationRecord[];
  history: HistoryRecord[];
}
export type SqlValue = string | number | null | boolean | { blobBytes: number };
export interface QueryTable { columns: string[]; values: SqlValue[][]; truncated: boolean }
export interface QueryResponse extends DatabaseSnapshot { results: QueryTable[]; rowsAffected: number; durationMs: number }
export interface AuditEntry { id: string; action: string; detail: string; at: string; status: "success" | "error" }
