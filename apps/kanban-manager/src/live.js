/* Everything the board derives at read time rather than storing on disk:
   automation health, per-conversation action summaries, LLM model names and
   what each conversation has spent.

   They all used to be computed server-side by the vibe-manager service. They
   are derived here instead so they cannot go stale in the store, and they all
   go through the Canvas host client, which attaches the session key.

   The automation backend is reachable on the same host as the agent server
   (the ingress routes /api/automation to it), so it needs no separate
   credentials — this is exactly how Canvas's own automation client works. */

import { isNotFound } from "./store.js";

const AUTOMATION_BASE = "/api/automation/v1";

/** Cache with a TTL; `sticky` entries are never refetched once known. */
class TtlCache {
  constructor(ttlMs) {
    this.ttlMs = ttlMs;
    this.entries = new Map();
  }

  get(key) {
    const hit = this.entries.get(key);
    if (!hit) return undefined;
    if (hit.sticky) return hit.value;
    if (Date.now() - hit.at > this.ttlMs) return undefined;
    return hit.value;
  }

  /** Returns the cached value even if stale — used to avoid flicker on error. */
  peek(key) {
    return this.entries.get(key)?.value;
  }

  set(key, value, sticky = false) {
    this.entries.set(key, { value, at: Date.now(), sticky });
  }
}

/* Total USD a conversation has spent, across every LLM it used — the same sum
   automation/main.py's conversation_spend() enforces budgets with, so the
   board shows the number the cap is judged against. */
export function conversationSpend(conv) {
  const usage = conv?.stats?.usage_to_metrics;
  if (!usage || typeof usage !== "object") return 0;
  let total = 0;
  for (const metrics of Object.values(usage)) {
    const cost = Number(metrics?.accumulated_cost);
    if (Number.isFinite(cost)) total += cost;
  }
  return total;
}

function runSlim(run) {
  if (!run) return null;
  const out = {};
  for (const k of ["status", "error_detail", "created_at", "started_at", "completed_at"]) {
    out[k] = run[k] ?? null;
  }
  return out;
}

export class Live {
  constructor(host) {
    this.host = host;
    this.models = new TtlCache(5 * 60 * 1000);
    // Short TTL: the live/done indicator has to flip promptly once a worker ends.
    this.statuses = new TtlCache(10 * 1000);
    this.summaries = new TtlCache(10 * 1000);
    // A worker only spends while it runs, and a running worker is already
    // refreshed on the status TTL above; this keeps parked cards from
    // re-polling on every board render.
    this.spends = new TtlCache(60 * 1000);
    this.inFlight = new Set();
  }

  // ------------------------------------------------------------- automation

  async automationStatus(workspace) {
    const automationId = workspace?.automation_id || null;
    const out = {
      automation_id: automationId,
      configured: Boolean(automationId),
      enabled: null,
      last_triggered_at: null,
      run_active: false,
      last_run: null,
      last_finished_run: null,
      consecutive_failures: 0,
      manager_conversation: null,
      // The workspace names an automation the backend doesn't have (deleted
      // out from under us). The UI offers to start a new one rather than
      // reporting a health problem it cannot act on.
      missing: false,
      error: null,
    };
    if (!automationId) return out;

    try {
      const auto = await this.host.agentServer.request({
        path: `${AUTOMATION_BASE}/${automationId}`,
      });
      out.enabled = auto?.enabled ?? null;
      out.last_triggered_at = auto?.last_triggered_at ?? null;

      const runsRes = await this.host.agentServer.request({
        path: `${AUTOMATION_BASE}/${automationId}/runs?limit=10`,
      });
      const runs = runsRes?.runs || [];
      out.run_active = runs.some((r) => r.completed_at == null);
      if (runs.length) out.last_run = runSlim(runs[0]);

      // A cron retry in flight must not mask failures: report the outcome of
      // the most recent *finished* run plus the current failure streak.
      const finished = runs.filter((r) => r.completed_at != null);
      if (finished.length) {
        out.last_finished_run = runSlim(finished[0]);
        let streak = 0;
        for (const run of finished) {
          if (run.status === "COMPLETED") break;
          streak += 1;
        }
        out.consecutive_failures = streak;
      }
    } catch (err) {
      if (isNotFound(err)) out.missing = true;
      // Degrade to "unknown" rather than breaking the badge.
      else out.error = `automation backend unreachable: ${err.message}`;
    }

    const convId = workspace?.manager_conversation_id;
    if (convId) {
      let status = "unknown";
      try {
        const conv = await this.host.agentServer.request({
          path: `/api/conversations/${convId}?include_skills=false`,
        });
        status = conv?.execution_status || "unknown";
      } catch {
        /* keep "unknown" */
      }
      out.manager_conversation = { id: convId, status };
    }
    return out;
  }

  async triggerAutomation(workspace) {
    const automationId = workspace?.automation_id;
    if (!automationId) throw new Error("manager automation not configured for this workspace");
    return this.host.agentServer.request({
      method: "POST",
      path: `${AUTOMATION_BASE}/${automationId}/dispatch`,
    });
  }

  // --------------------------------------------------------- action summary

  /* The LLM-predicted summary lives inside an ActionEvent's
     tool_call.arguments JSON. The old service held a websocket to keep this
     fresh, but the board only ever showed it on its poll, so polling the event
     search endpoint gives the same freshness without a second auth path. */
  extractActionSummary(event) {
    const toolCall = event?.tool_call;
    if (!toolCall) return null;
    let args = toolCall.arguments;
    if (typeof args === "string") {
      try {
        args = JSON.parse(args);
      } catch {
        return null;
      }
    }
    const summary = args?.summary;
    if (typeof summary !== "string" || !summary.trim()) return null;
    return {
      summary: summary.trim(),
      tool: toolCall.name || event?.tool_name || null,
      timestamp: event?.timestamp || null,
    };
  }

  /* Newest-first, paging until a summary turns up. The most recent events are
     often state updates and observations rather than actions, so a shallow
     limit misses the summary entirely; the pages are capped so a conversation
     with no summaries at all cannot spin. */
  async fetchActionSummary(convId, maxPages = 3) {
    let pageId = null;
    for (let page = 0; page < maxPages; page += 1) {
      const query = new URLSearchParams({
        sort_order: "TIMESTAMP_DESC",
        limit: "100",
      });
      if (pageId) query.set("page_id", pageId);
      const res = await this.host.agentServer.request({
        path: `/api/conversations/${convId}/events/search?${query}`,
      });
      for (const event of res?.items || []) {
        const summary = this.extractActionSummary(event);
        if (summary) return summary;
      }
      pageId = res?.next_page_id;
      if (!pageId) break;
    }
    return null;
  }

  /** Cached summary; refreshes in the background so the poll never blocks. */
  latestAction(convId) {
    if (!convId) return null;
    const cached = this.summaries.get(convId);
    if (cached !== undefined) return cached;

    const key = `summary:${convId}`;
    if (!this.inFlight.has(key)) {
      this.inFlight.add(key);
      this.fetchActionSummary(convId)
        .then((value) => this.summaries.set(convId, value))
        .catch(() => this.summaries.set(convId, this.summaries.peek(convId) ?? null))
        .finally(() => this.inFlight.delete(key));
    }
    return this.summaries.peek(convId) ?? null;
  }

  // ------------------------------- model + execution status + spend

  /* One conversation-metadata GET feeds all three caches, so a card that shows
     the model, the live/done indicator and the spend still costs a single
     request. */
  refreshConversation(convId, sticky) {
    const key = `conv:${convId}`;
    if (this.inFlight.has(key)) return;
    this.inFlight.add(key);
    this.host.agentServer
      .request({ path: `/api/conversations/${convId}?include_skills=false` })
      .then((conv) => {
        const model = conv?.agent?.llm?.model || null;
        if (model) this.models.set(convId, model, sticky);
        else this.models.set(convId, this.models.peek(convId) ?? null);
        this.statuses.set(convId, conv?.execution_status || null);
        this.spends.set(convId, conversationSpend(conv), sticky);
      })
      // A failed refetch keeps the last known values rather than blanking them.
      .catch(() => {
        this.models.set(convId, this.models.peek(convId) ?? null);
        this.statuses.set(convId, this.statuses.peek(convId) ?? null);
        this.spends.set(convId, this.spends.peek(convId) ?? null);
      })
      .finally(() => this.inFlight.delete(key));
  }

  /** Cached model name. Terminal tickets are sticky: never refetched. */
  llmModel(convId, sticky = false) {
    if (!convId) return null;
    const cached = this.models.get(convId);
    if (cached !== undefined) return cached;
    this.refreshConversation(convId, sticky);
    return this.models.peek(convId) ?? null;
  }

  /** Cached execution_status — whether the worker is still acting. */
  conversationStatus(convId) {
    if (!convId) return null;
    const cached = this.statuses.get(convId);
    if (cached !== undefined) return cached;
    this.refreshConversation(convId, false);
    return this.statuses.peek(convId) ?? null;
  }

  /** Cached USD spend. Terminal tickets are sticky: they spend no more. */
  spendUsd(convId, sticky = false) {
    if (!convId) return null;
    const cached = this.spends.get(convId);
    if (cached !== undefined) return cached;
    this.refreshConversation(convId, sticky);
    return this.spends.peek(convId) ?? null;
  }

  /** The agent server's LLM profiles, for the request-settings picker. */
  async llmProfiles() {
    const res = await this.host.agentServer.request({ path: "/api/profiles" });
    return {
      profiles: res?.profiles || [],
      active_profile: res?.active_profile || null,
    };
  }

  primeModel(convId, model) {
    if (convId && model) this.models.set(convId, model);
  }

  invalidateModel(convId) {
    if (convId) this.models.entries.delete(convId);
  }

  /** Decorate board tickets with the derived fields the UI renders. */
  decorate(tickets, canvasBase) {
    return tickets.map((t) => ({
      ...t,
      conversation_url: t.conversation_id
        ? `${canvasBase}/conversations/${t.conversation_id}`
        : null,
      latest_action:
        t.status === "in_progress" && t.conversation_id
          ? this.latestAction(t.conversation_id)
          : null,
      conversation_status:
        t.status === "in_progress" && t.conversation_id
          ? this.conversationStatus(t.conversation_id)
          : null,
      llm_model: t.conversation_id
        ? this.llmModel(t.conversation_id, ["finished", "verified"].includes(t.status))
        : null,
      spend_usd: t.conversation_id
        ? this.spendUsd(t.conversation_id, ["finished", "verified"].includes(t.status))
        : null,
    }));
  }
}
