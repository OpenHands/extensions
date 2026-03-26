/*
OpenHands Cloud API (V1) minimal client.

Audience: AI agents.

App server (Cloud):
- Base: https://app.all-hands.dev
- Prefix: /api/v1
- Auth: Authorization: Bearer <OPENHANDS_CLOUD_API_KEY>

Agent server (sandbox runtime):
- Base: {agent_server_url}/api
- Auth: X-Session-API-Key: <session_api_key>

This is intentionally small and keeps responses mostly untyped (unknown/record)
so it is easy to adapt.
*/

export type OpenHandsOptions = {
  apiKey: string;
  baseUrl?: string;
};

const AGENT_EVENTS_SEARCH_MAX_LIMIT = 100;


export class OpenHandsAPI {
  private readonly apiKey: string;
  private readonly baseUrl: string;

  constructor(opts: OpenHandsOptions) {
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
    const safeLimit = Number.isFinite(limit) ? Math.trunc(limit) : 1;
    const params = new URLSearchParams({ limit: String(Math.max(1, safeLimit)) });
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

  async conversationEventsCount(appConversationId: string): Promise<number> {
    const res = await this.request<number>(
      `${this.apiV1Url}/conversation/${encodeURIComponent(appConversationId)}/events/count`,
      { method: "GET" },
    );
    return Number(res);
  }

  async appConversationDownloadZip(appConversationId: string): Promise<Blob> {
    const url = `${this.apiV1Url}/app-conversations/${encodeURIComponent(appConversationId)}/download`;
    return await this.request<Blob>(url, { method: "GET" }, "blob");
  }

  async appConversationStart(req: {
    initialMessage: string;
    selectedRepository?: string;
    selectedBranch?: string;
    title?: string;
    run?: boolean;
  }): Promise<Record<string, unknown>> {
    // NOTE: In many deployments this returns a *start-task* object.
    // `id` is usually the start_task_id; use `app_conversation_id` (if present)
    // for `/download` and `/conversation/.../events/...` endpoints.
    // If `app_conversation_id` is missing, fetch it via:
    // GET /api/v1/app-conversations/start-tasks?ids=<start_task_id>

    const payload: Record<string, unknown> = {
      initial_message: {
        role: "user",
        // V1 expects `content` as an array of parts, even for a single text message.
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

  private buildAgentEventFilterParams(opts?: {
    timestampGte?: string;
    timestampLt?: string;
    kind?: string;
    source?: string;
    body?: string;
  }): URLSearchParams {
    const params = new URLSearchParams();
    if (opts?.timestampGte) params.set("timestamp__gte", opts.timestampGte);
    if (opts?.timestampLt) params.set("timestamp__lt", opts.timestampLt);
    if (opts?.kind) params.set("kind", opts.kind);
    if (opts?.source) params.set("source", opts.source);
    if (opts?.body) params.set("body", opts.body);
    return params;
  }

  async agentEventsCount(agentServerUrl: string, sessionApiKey: string, conversationId: string, opts?: {
    timestampGte?: string;
    timestampLt?: string;
    kind?: string;
    source?: string;
    body?: string;
  }): Promise<number> {
    const qs = this.buildAgentEventFilterParams(opts).toString();
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
    const params = this.buildAgentEventFilterParams(opts);

    // Cap limit to keep responses small and consistent across clients.
    const rawLimit = opts?.limit ?? 50;
    const safeLimit = Number.isFinite(rawLimit) ? Math.trunc(rawLimit) : 1;
    const limit = Math.max(1, Math.min(AGENT_EVENTS_SEARCH_MAX_LIMIT, safeLimit));
    params.set("limit", String(limit));

    if (opts?.sortOrder) params.set("sort_order", opts.sortOrder);

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


export type OpenHandsV1Options = OpenHandsOptions;
export { OpenHandsAPI as OpenHandsV1API };
