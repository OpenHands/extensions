/*
OpenHands API (legacy V0) minimal client.

This file mirrors the Python client in scripts/openhands_api.py.

Audience: AI agents.

Recommended workflow:
1) POST /api/conversations (create)
2) GET /api/conversations/:id (status)
3) GET /api/conversations/:id/events (incremental events)
4) GET /api/conversations/:id/trajectory (full history)

Docs: https://docs.openhands.dev/api-reference/new-conversation
Server routes: https://github.com/OpenHands/OpenHands/tree/main/openhands/server/routes
*/

export type OpenHandsAPIOptions = {
  apiKey: string;
  baseUrl?: string;
};

export type CreateConversationRequest = {
  initialUserMsg: string;
  repository?: string;
  selectedBranch?: string;
  gitProvider?: string;
  conversationInstructions?: string;
};

export type CreateConversationResponse = {
  status: string;
  conversation_id: string;
  message?: string;
  url?: string;
  [k: string]: unknown;
};

export type GetConversationResponse = {
  conversation_id: string;
  status: string;
  url?: string;
  [k: string]: unknown;
};

export type GetEventsResponse = {
  events: unknown[];
  has_more?: boolean;
  [k: string]: unknown;
};

export type ListConversationsResponse = {
  results: unknown[];
  next_page_id?: string | null;
  [k: string]: unknown;
};

export class OpenHandsAPI {
  private readonly apiKey: string;
  private readonly baseUrl: string;

  constructor(opts: OpenHandsAPIOptions) {
    if (!opts.apiKey) throw new Error("Missing apiKey");
    this.apiKey = opts.apiKey;
    this.baseUrl = (opts.baseUrl ?? "https://app.all-hands.dev").replace(/\/$/, "");
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const res = await fetch(url, {
      ...init,
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`OpenHands API error ${res.status} ${res.statusText}: ${text}`);
    }

    return (await res.json()) as T;
  }

  async createConversation(req: CreateConversationRequest): Promise<CreateConversationResponse> {
    return await this.request<CreateConversationResponse>("/api/conversations", {
      method: "POST",
      body: JSON.stringify({
        initial_user_msg: req.initialUserMsg,
        repository: req.repository,
        selected_branch: req.selectedBranch,
        git_provider: req.gitProvider,
        conversation_instructions: req.conversationInstructions,
      }),
    });
  }

  async getConversation(conversationId: string): Promise<GetConversationResponse> {
    return await this.request<GetConversationResponse>(
      `/api/conversations/${encodeURIComponent(conversationId)}`,
      { method: "GET" },
    );
  }

  async getEvents(
    conversationId: string,
    opts?: { startId?: number; endId?: number; reverse?: boolean; limit?: number },
  ): Promise<GetEventsResponse> {
    const limit = Math.max(1, Math.min(100, opts?.limit ?? 20));
    const params = new URLSearchParams({
      start_id: String(opts?.startId ?? 0),
      reverse: String(Boolean(opts?.reverse)),
      limit: String(limit),
    });
    if (opts?.endId !== undefined) params.set("end_id", String(opts.endId));

    return await this.request<GetEventsResponse>(
      `/api/conversations/${encodeURIComponent(conversationId)}/events?${params.toString()}`,
      { method: "GET" },
    );
  }

  async getTrajectory(conversationId: string): Promise<Record<string, unknown>> {
    return await this.request<Record<string, unknown>>(
      `/api/conversations/${encodeURIComponent(conversationId)}/trajectory`,
      { method: "GET" },
    );
  }

  async listConversations(opts?: {
    limit?: number;
    pageId?: string;
    selectedRepository?: string;
    includeSubConversations?: boolean;
  }): Promise<ListConversationsResponse> {
    const params = new URLSearchParams({
      limit: String(Math.max(1, opts?.limit ?? 20)),
    });
    if (opts?.pageId) params.set("page_id", opts.pageId);
    if (opts?.selectedRepository) params.set("selected_repository", opts.selectedRepository);
    if (opts?.includeSubConversations !== undefined) {
      params.set("include_sub_conversations", String(Boolean(opts.includeSubConversations)));
    }

    return await this.request<ListConversationsResponse>(`/api/conversations?${params.toString()}`, {
      method: "GET",
    });
  }

  async updateConversationTitle(conversationId: string, title: string): Promise<Record<string, unknown>> {
    return await this.request<Record<string, unknown>>(
      `/api/conversations/${encodeURIComponent(conversationId)}`,
      { method: "PATCH", body: JSON.stringify({ title }) },
    );
  }

  async deleteConversation(conversationId: string): Promise<Record<string, unknown>> {
    return await this.request<Record<string, unknown>>(
      `/api/conversations/${encodeURIComponent(conversationId)}`,
      { method: "DELETE" },
    );
  }

  async addMessage(conversationId: string, message: string): Promise<Record<string, unknown>> {
    return await this.request<Record<string, unknown>>(
      `/api/conversations/${encodeURIComponent(conversationId)}/message`,
      { method: "POST", body: JSON.stringify({ message }) },
    );
  }

  async listWorkspaceFiles(conversationId: string, path?: string): Promise<unknown> {
    const params = new URLSearchParams();
    if (path !== undefined) params.set("path", path);
    const qs = params.toString();
    return await this.request<unknown>(
      `/api/conversations/${encodeURIComponent(conversationId)}/list-files${qs ? `?${qs}` : ""}`,
      { method: "GET" },
    );
  }

  async getFileContent(conversationId: string, filePath: string): Promise<Record<string, unknown>> {
    const params = new URLSearchParams({ file: filePath });
    return await this.request<Record<string, unknown>>(
      `/api/conversations/${encodeURIComponent(conversationId)}/select-file?${params.toString()}`,
      { method: "GET" },
    );
  }

  async pollUntilTerminal(
    conversationId: string,
    opts?: { timeoutMs?: number; pollIntervalMs?: number },
  ): Promise<GetConversationResponse> {
    const timeoutMs = opts?.timeoutMs ?? 20 * 60_000;
    const pollIntervalMs = opts?.pollIntervalMs ?? 30_000;

    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const convo = await this.getConversation(conversationId);
      const s = String(convo.status ?? "").toUpperCase();
      if (["STOPPED", "ERROR", "FAILED", "CANCELLED"].includes(s)) return convo;
      await new Promise((r) => setTimeout(r, pollIntervalMs));
    }

    throw new Error(`Conversation ${conversationId} did not reach terminal within ${timeoutMs}ms`);
  }
}
