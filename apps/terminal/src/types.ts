export type PageContext = {
  container: HTMLElement;
  path: string;
};

export type AgentServerRequest = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  body?: unknown;
  headers?: Record<string, string>;
};

export type CanvasHost = {
  apiVersion: string;
  extension: Readonly<{ name: string; version: string; resolvedRef: string | null }>;
  backend: Readonly<{ id: string; kind: "local" | "cloud"; orgId: string | null }>;
  registerPage(id: string, mount: (context: PageContext) => void | (() => void)): () => void;
  agentServer: {
    request<T = unknown>(request: AgentServerRequest): Promise<T>;
  };
};
