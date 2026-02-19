/*
OpenHands Cloud API (V1) minimal client.

Audience: AI agents.

App server (Cloud):
- Base: https://app.all-hands.dev
- Prefix: /api/v1
- Auth: Authorization: Bearer <OPENHANDS_API_KEY>

Agent server (sandbox runtime):
- Base: {agent_server_url}/api
- Auth: X-Session-API-Key: <session_api_key>

This is intentionally small and keeps responses mostly untyped (unknown/record)
so it is easy to adapt.
*/

export type OpenHandsV1Options = {
  apiKey: string;
  baseUrl?: string;
};

export type JSONValue = null | boolean | number | string | JSONValue[] | { [k: string]: JSONValue };

export class OpenHandsV1API {
  private readonly apiKey: string;
  private readonly baseUrl: string;

  constructor(opts: OpenHandsV1Options) {
    if (!opts.apiKey) throw new Error("Missing apiKey");
    this.apiKey = opts.apiKey;
    this.baseUrl = (opts.baseUrl ?? "https://app.all-hands.dev").replace(/\/$/, "");
  }

  private get apiV1Url(): string {
    return `${this.baseUrl}/api/v1`;
  }

  private async baseRequest<T>(
    url: string,
    init: RequestInit | undefined,
    headers: Record<string, string>,
    parseAs: "json" | "blob" = "json",
  ): Promise<T> {
    const res = await fetch(url, {
      ...init,
      headers: {
        ...headers,
        ...(init?.headers ?? {}),
      },
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`OpenHands API error ${res.status} ${res.statusText}: ${text}`);
    }

    if (parseAs === "blob") return (await res.blob()) as unknown as T;
    return (await res.json()) as T;
  }

  private async request<T>(
    url: string,
    init?: RequestInit,
    parseAs: "json" | "blob" = "json",
  ): Promise<T> {
    return await this.baseRequest(
      url,
      init,
      { Authorization: `Bearer ${this.apiKey}`, "Content-Type": "application/json" },
      parseAs,
    );
  }

  // -----------------------------
  // App server endpoints
  // -----------------------------

  async usersMe(): Promise<Record<string, unknown>> {
    return await this.request(`${this.apiV1Url}/users/me`, { method: "GET" });
  }

  async appConversationsSearch(limit = 20): Promise<Record<string, unknown>> {
    const params = new URLSearchParams({ limit: String(Math.max(1, limit)) });
    return await this.request(`${this.apiV1Url}/app-conversations/search?${params.toString()}`, {
      method: "GET",
    });
  }

  async appConversationsGetBatch(ids: string[]): Promise<Array<Record<string, unknown>>> {
    if (ids.length === 0) return [];
    const params = new URLSearchParams();
    for (const id of ids) params.append("ids", id);
    return await this.request(`${this.apiV1Url}/app-conversations?${params.toString()}`, {
      method: "GET",
    });
  }

  async conversationEventsCount(conversationId: string): Promise<number> {
    const res = await this.request<number>(
      `${this.apiV1Url}/conversation/${encodeURIComponent(conversationId)}/events/count`,
      { method: "GET" },
    );
    return Number(res);
  }

  async appConversationDownloadZip(conversationId: string): Promise<Blob> {
    const url = `${this.apiV1Url}/app-conversations/${encodeURIComponent(conversationId)}/download`;
    return await this.request<Blob>(url, { method: "GET" }, "blob");
  }

  async appConversationStart(req: {
    initialMessage: string;
    selectedRepository?: string;
    selectedBranch?: string;
    title?: string;
    run?: boolean;
  }): Promise<Record<string, unknown>> {
    const payload: Record<string, unknown> = {
      initial_message: {
        role: "user",
        content: [{ type: "text", text: req.initialMessage }],
        run: req.run ?? true,
      },
    };
    if (req.selectedRepository) payload.selected_repository = req.selectedRepository;
    if (req.selectedBranch) payload.selected_branch = req.selectedBranch;
    if (req.title) payload.title = req.title;

    return await this.request(`${this.apiV1Url}/app-conversations`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async appConversationsStartTasksGetBatch(ids: string[]): Promise<Array<Record<string, unknown>>> {
    if (ids.length === 0) return [];
    const params = new URLSearchParams();
    for (const id of ids) params.append("ids", id);
    return await this.request(`${this.apiV1Url}/app-conversations/start-tasks?${params.toString()}`, {
      method: "GET",
    });
  }

  // -----------------------------
  // Agent server endpoints
  // -----------------------------

  private async agentRequest<T>(
    agentServerUrl: string,
    sessionApiKey: string,
    path: string,
    init?: RequestInit,
  ): Promise<T> {
    const base = agentServerUrl.replace(/\/$/, "");
    const url = `${base}${path}`;
    return await this.baseRequest(
      url,
      init,
      { "X-Session-API-Key": sessionApiKey, "Content-Type": "application/json" },
      "json",
    );
  }

  async agentEventsCount(agentServerUrl: string, sessionApiKey: string, conversationId: string, opts?: {
    timestampGte?: string;
    timestampLt?: string;
    kind?: string;
    source?: string;
    body?: string;
  }): Promise<number> {
    const params = new URLSearchParams();
    if (opts?.timestampGte) params.set("timestamp__gte", opts.timestampGte);
    if (opts?.timestampLt) params.set("timestamp__lt", opts.timestampLt);
    if (opts?.kind) params.set("kind", opts.kind);
    if (opts?.source) params.set("source", opts.source);
    if (opts?.body) params.set("body", opts.body);

    const qs = params.toString();
    const suffix = qs ? `?${qs}` : "";
    const n = await this.agentRequest<number>(
      agentServerUrl,
      sessionApiKey,
      `/api/conversations/${encodeURIComponent(conversationId)}/events/count${suffix}`,
      { method: "GET" },
    );
    return Number(n);
  }

  async agentEventsSearch(agentServerUrl: string, sessionApiKey: string, conversationId: string, opts?: {
    limit?: number;
    sortOrder?: "TIMESTAMP" | "TIMESTAMP_DESC";
    timestampGte?: string;
    timestampLt?: string;
    kind?: string;
    source?: string;
    body?: string;
  }): Promise<Record<string, unknown>> {
    const params = new URLSearchParams();
    params.set("limit", String(Math.max(1, Math.min(100, opts?.limit ?? 50))));
    if (opts?.sortOrder) params.set("sort_order", opts.sortOrder);
    if (opts?.timestampGte) params.set("timestamp__gte", opts.timestampGte);
    if (opts?.timestampLt) params.set("timestamp__lt", opts.timestampLt);
    if (opts?.kind) params.set("kind", opts.kind);
    if (opts?.source) params.set("source", opts.source);
    if (opts?.body) params.set("body", opts.body);

    return await this.agentRequest<Record<string, unknown>>(
      agentServerUrl,
      sessionApiKey,
      `/api/conversations/${encodeURIComponent(conversationId)}/events/search?${params.toString()}`,
      { method: "GET" },
    );
  }

  async agentExecuteBash(agentServerUrl: string, sessionApiKey: string, command: string, cwd?: string): Promise<Record<string, unknown>> {
    const payload: Record<string, unknown> = { command, timeout: 30 };
    if (cwd) payload.cwd = cwd;

    return await this.agentRequest<Record<string, unknown>>(
      agentServerUrl,
      sessionApiKey,
      `/api/bash/execute_bash_command`,
      { method: "POST", body: JSON.stringify(payload) },
    );
  }
}
