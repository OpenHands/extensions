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
  agentServer?: {
    request: (request: { method?: string; path: string; signal?: AbortSignal }) => Promise<unknown>;
  };
}

export interface MountContext {
  container: HTMLElement;
  path: string;
  navigate: (path: string) => void;
}

export interface WorkerResult {
  input: number;
  value: number;
  durationMs: number;
}
