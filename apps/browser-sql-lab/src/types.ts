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

export interface CanvasHost {
  apiVersion: string;
  extension: AppMetadata;
  backend: BackendMetadata;
  registerPage: (id: string, mount: (context: MountContext) => void | (() => void)) => () => void;
  navigate: (path: string) => void;
}

export interface MountContext {
  container: HTMLElement;
  path: string;
  navigate: (path: string) => void;
}

export type SqlValue = string | number | Uint8Array | null;

export interface QueryTable {
  columns: string[];
  values: SqlValue[][];
}

export interface SchemaTable {
  name: string;
  sql: string;
  columns: Array<{ name: string; type: string; nullable: boolean; primaryKey: boolean }>;
}

export interface MigrationRecord {
  id: string;
  appliedAt: string;
}

export interface HistoryRecord {
  id: number;
  sql: string;
  status: "success" | "error";
  executedAt: string;
}

export interface DatabaseSnapshot {
  namespace: string;
  tables: SchemaTable[];
  migrations: MigrationRecord[];
  history: HistoryRecord[];
}

export interface QueryResponse extends DatabaseSnapshot {
  results: QueryTable[];
  rowsAffected: number;
  durationMs: number;
}

export type WorkerRequest =
  | { id: number; type: "init"; namespace: string }
  | { id: number; type: "query"; sql: string }
  | { id: number; type: "seed" }
  | { id: number; type: "reset" }
  | { id: number; type: "export" }
  | { id: number; type: "cancel"; targetId: number };

export type WorkerResponse =
  | { id: number; ok: true; data: unknown }
  | { id: number; ok: false; error: string };
