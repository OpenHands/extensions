/* Usage Insights — a Canvas App for OpenHands conversation token usage and estimated cost.
 *
 * Browser-only, dependency-free ESM. All styles are scoped under `.usage-insights`.
 * Uses host.agentServer.request() with root-relative paths only.
 */

// ─── Constants ────────────────────────────────────────────────────────────

const ROOT_PATH = "/extensions/usage-insights/usage";
const POLL_INTERVAL_MS = 10_000;
const MAX_CONVERSATIONS = 500;
const MAX_EVENTS_PER_CONVERSATION = 2_000;
const CACHE_DB_NAME = "usage-insights-cache";
const CACHE_DB_VERSION = 1;
const CACHE_RETENTION_DAYS = 90;
const CATALOG_VERSION = "2026-09";
const CATALOG_SOURCE_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json";

// ─── Bundled model price catalog (fallback only) ──────────────────────────
// A subset of public per-million-token rates. Source: provider public pricing pages.
// This is an explicit fallback; reported server cost always takes precedence.

const CATALOG = [
  {
    providerId: "openai",
    modelId: "gpt-4o",
    inputUsdPerMillion: 2.5,
    outputUsdPerMillion: 10,
    cacheReadUsdPerMillion: 1.25,
    cacheWriteUsdPerMillion: 0,
  source: "catalog",
    catalogVersion: CATALOG_VERSION,
    sourceUrl: "https://openai.com/api/pricing/",
  },
  {
    providerId: "openai",
    modelId: "gpt-4o-mini",
    inputUsdPerMillion: 0.15,
    outputUsdPerMillion: 0.6,
    cacheReadUsdPerMillion: 0.075,
    cacheWriteUsdPerMillion: 0,
    source: "catalog",
    catalogVersion: CATALOG_VERSION,
    sourceUrl: "https://openai.com/api/pricing/",
  },
  {
    providerId: "anthropic",
    modelId: "claude-sonnet-4-20250514",
    inputUsdPerMillion: 3,
    outputUsdPerMillion: 15,
    cacheReadUsdPerMillion: 0.3,
    cacheWriteUsdPerMillion: 3.75,
    source: "catalog",
    catalogVersion: CATALOG_VERSION,
    sourceUrl: "https://www.anthropic.com/pricing",
  },
  {
    providerId: "anthropic",
    modelId: "claude-3-5-haiku-20241022",
    inputUsdPerMillion: 0.8,
    outputUsdPerMillion: 4,
    cacheReadUsdPerMillion: 0.08,
    cacheWriteUsdPerMillion: 1,
    source: "catalog",
    catalogVersion: CATALOG_VERSION,
    sourceUrl: "https://www.anthropic.com/pricing",
  },
];

// ─── Styles ───────────────────────────────────────────────────────────────

const STYLE = `
.usage-insights {
  --ui-bg: var(--oh-color-base, #0B0E14);
  --ui-panel: var(--oh-color-base-secondary, #21252F);
  --ui-raised: var(--oh-surface-raised, #2C313F);
  --ui-text: var(--oh-foreground, #EEF2F7);
  --ui-contrast: var(--oh-contrast, #FFFFFF);
  --ui-muted: var(--oh-muted, #A3B0C4);
  --ui-dim: var(--oh-text-dim, #7E8A9E);
  --ui-border: var(--oh-border, #4B5468);
  --ui-border-subtle: var(--oh-border-subtle, #383F50);
  --ui-focus: var(--oh-focus, #FFFFFF);
  --ui-primary: var(--oh-color-primary, #C9B974);
  --ui-on-primary: var(--oh-accent-foreground, #0B0E14);
  --ui-danger: var(--oh-danger, #E76A5E);
  --ui-success: var(--oh-success, #A5E75E);
  min-height: 100%;
  color: var(--ui-text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
.usage-insights * { box-sizing: border-box; }
.usage-insights button, .usage-insights input, .usage-insights select { font: inherit; }
.usage-insights__shell { padding: 1rem; max-width: 72rem; margin: 0 auto; }
@media (min-width: 640px) { .usage-insights__shell { padding: 1.5rem; } }
@media (min-width: 1024px) { .usage-insights__shell { padding: 2rem; } }
.usage-insights__header { display: flex; flex-direction: column; gap: .5rem; margin-bottom: 1.5rem; }
@media (min-width: 640px) { .usage-insights__header { flex-direction: row; align-items: flex-start; justify-content: space-between; } }
.usage-insights__heading { min-width: 0; }
.usage-insights__heading h1 { margin: 0; font-size: 1.25rem; font-weight: 600; letter-spacing: -.025em; color: var(--ui-contrast); }
.usage-insights__heading p { margin: .25rem 0 0; font-size: .8rem; color: var(--ui-muted); }
.usage-insights__header-actions { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }
.usage-insights__updated { font-size: .72rem; color: var(--ui-dim); }
.usage-insights__updated--live { color: var(--ui-success); }
.usage-insights__toolbar { display: flex; flex-wrap: wrap; gap: .5rem; align-items: center; margin-bottom: 1rem; }
.usage-insights__select, .usage-insights__input {
  min-height: 2.25rem; border: 1px solid var(--ui-border); border-radius: .5rem;
  padding: .4rem .6rem; color: var(--ui-contrast); background: var(--ui-panel);
  font-size: .8rem;
}
.usage-insights__select:focus-visible, .usage-insights__input:focus-visible,
.usage-insights__button:focus-visible {
  outline: 2px solid var(--ui-focus); outline-offset: 2px;
}
.usage-insights__select:disabled, .usage-insights__input:disabled { opacity: .6; cursor: not-allowed; }
.usage-insights__button {
  min-height: 2.25rem; border: 1px solid var(--ui-border); border-radius: .5rem;
  padding: .4rem .7rem; color: var(--ui-text); background: var(--ui-panel);
  font-size: .8rem; cursor: pointer;
  transition: background-color 75ms, border-color 75ms, opacity 75ms;
}
.usage-insights__button:hover { border-color: var(--ui-muted); background: var(--ui-raised); }
.usage-insights__button:disabled { opacity: .5; cursor: not-allowed; }
.usage-insights__button--primary {
  border: 0; background: var(--ui-primary); color: var(--ui-on-primary); font-weight: 500;
}
.usage-insights__button--primary:hover { opacity: .85; }
.usage-insights__button--small { min-height: 1.75rem; padding: .25rem .5rem; font-size: .72rem; }
.usage-insights__filters { display: flex; flex-wrap: wrap; gap: .5rem; align-items: center; }
.usage-insights__filter-group { display: flex; align-items: center; gap: .35rem; }
.usage-insights__filter-label { font-size: .72rem; color: var(--ui-dim); white-space: nowrap; }
.usage-insights__cards { display: grid; gap: .75rem; grid-template-columns: 1fr; margin-bottom: 1.5rem; }
@media (min-width: 640px) { .usage-insights__cards { grid-template-columns: repeat(2, 1fr); } }
@media (min-width: 1024px) { .usage-insights__cards { grid-template-columns: repeat(3, 1fr); } }
.usage-insights__card {
  border: 1px solid var(--ui-border); border-radius: .75rem; background: var(--ui-panel);
  padding: 1rem 1.25rem;
}
.usage-insights__card-label { font-size: .68rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--ui-dim); }
.usage-insights__card-value { display: block; margin-top: .35rem; font-size: 1.4rem; font-weight: 600; color: var(--ui-contrast); overflow-wrap: anywhere; }
.usage-insights__card-sub { display: block; margin-top: .2rem; font-size: .72rem; color: var(--ui-muted); }
.usage-insights__card--warning { border-color: color-mix(in srgb, var(--ui-danger) 50%, var(--ui-border)); }
.usage-insights__card--warning .usage-insights__card-value { color: var(--ui-danger); }
.usage-insights__section {
  border: 1px solid var(--ui-border); border-radius: .75rem; background: var(--ui-panel);
  padding: 1rem 1.25rem; margin-bottom: 1.5rem;
}
.usage-insights__section h2 { margin: 0 0 .25rem; font-size: 1rem; font-weight: 600; color: var(--ui-contrast); }
.usage-insights__section p { margin: 0 0 .75rem; font-size: .78rem; color: var(--ui-muted); }
.usage-insights__table { width: 100%; border-collapse: collapse; font-size: .78rem; }
.usage-insights__table th, .usage-insights__table td { text-align: left; padding: .5rem .6rem; border-bottom: 1px solid var(--ui-border-subtle); }
.usage-insights__table th { font-weight: 600; color: var(--ui-dim); font-size: .7rem; letter-spacing: .04em; text-transform: uppercase; }
.usage-insights__table td { color: var(--ui-text); overflow-wrap: anywhere; }
.usage-insights__table tr:hover td { background: var(--ui-raised); }
.usage-insights__table--scroll { display: block; overflow-x: auto; }
.usage-insights__table--scroll table { width: 100%; }
.usage-insights__link { color: var(--ui-primary); text-decoration: none; cursor: pointer; background: none; border: 0; padding: 0; font: inherit; text-align: left; }
.usage-insights__link:hover { text-decoration: underline; }
.usage-insights__badge { display: inline-block; padding: .12rem .4rem; border: 1px solid var(--ui-border); border-radius: 999px; font-size: .62rem; color: var(--ui-dim); }
.usage-insights__badge--reported { border-color: color-mix(in srgb, var(--ui-success) 50%, var(--ui-border)); color: var(--ui-success); }
.usage-insights__badge--catalog { border-color: color-mix(in srgb, var(--ui-primary) 50%, var(--ui-border)); color: var(--ui-primary); }
.usage-insights__badge--unpriced { border-color: var(--ui-border); color: var(--ui-dim); }
.usage-insights__badge--mixed { border-color: color-mix(in srgb, var(--ui-muted) 40%, var(--ui-border)); color: var(--ui-muted); }
.usage-insights__notice { padding: 1rem 1.25rem; border: 1px dashed var(--ui-border); border-radius: .5rem; color: var(--ui-muted); font-size: .82rem; text-align: center; }
.usage-insights__notice--error { border-style: solid; border-color: color-mix(in srgb, var(--ui-danger) 50%, var(--ui-border)); color: var(--ui-danger); }
.usage-insights__notice--info { border-style: solid; border-color: var(--ui-border-subtle); color: var(--ui-muted); }
.usage-insights__progress { height: .3rem; border-radius: 999px; background: var(--ui-bg); overflow: hidden; margin-top: .35rem; }
.usage-insights__progress-fill { height: 100%; border-radius: 999px; background: var(--ui-primary); transition: width 75ms; }
.usage-insights__progress-fill--warn { background: #facc15; }
.usage-insights__progress-fill--danger { background: var(--ui-danger); }
.usage-insights__bar-chart { display: flex; align-items: flex-end; gap: 2px; height: 6rem; padding: .5rem; border: 1px solid var(--ui-border); border-radius: .5rem; background: var(--ui-bg); margin-bottom: .5rem; }
.usage-insights__bar { flex: 1; min-width: 2px; border-radius: 2px 2px 0 0; background: var(--ui-primary); opacity: .85; }
.usage-insights__bar--empty { background: var(--ui-border-subtle); opacity: .3; }
.usage-insights__bar-label { font-size: .58rem; color: var(--ui-dim); text-align: center; }
.usage-insights__bar-row { display: flex; gap: 2px; margin-top: .25rem; }
.usage-insights__bar-row .usage-insights__bar-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.usage-insights__back { display: inline-flex; align-items: center; gap: .35rem; margin-bottom: 1rem; }
.usage-insights__detail-grid { display: grid; gap: 1rem; grid-template-columns: 1fr; }
@media (min-width: 768px) { .usage-insights__detail-grid { grid-template-columns: 1fr 1fr; } }
.usage-insights__model-list { display: flex; flex-direction: column; gap: .25rem; }
.usage-insights__model-row { display: grid; grid-template-columns: 1fr auto auto; gap: .5rem; padding: .35rem 0; border-bottom: 1px solid var(--ui-border-subtle); font-size: .75rem; }
.usage-insights__model-row:last-child { border-bottom: 0; }
.usage-insights__model-name { color: var(--ui-muted); overflow-wrap: anywhere; }
.usage-insights__model-cost { color: var(--ui-contrast); }
.usage-insights__model-tokens { color: var(--ui-dim); }
.usage-insights__loading { display: flex; align-items: center; gap: .5rem; color: var(--ui-muted); font-size: .8rem; }
.usage-insights__spinner { width: 1rem; height: 1rem; border: 2px solid var(--ui-border); border-top-color: var(--ui-primary); border-radius: 50%; animation: ui-spin .6s linear infinite; }
@keyframes ui-spin { to { transform: rotate(360deg); } }
.usage-insights__skeleton { background: var(--ui-raised); border-radius: .5rem; animation: ui-pulse 1.5s ease-in-out infinite; }
@keyframes ui-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .5; } }
.usage-insights__partial { display: flex; align-items: center; gap: .35rem; padding: .5rem .75rem; border: 1px solid var(--ui-border-subtle); border-radius: .5rem; background: var(--ui-bg); font-size: .72rem; color: var(--ui-dim); margin-bottom: 1rem; }
.usage-insights__provenance { font-size: .68rem; color: var(--ui-dim); }
.usage-insights__actions { display: flex; gap: .5rem; flex-wrap: wrap; margin-top: .75rem; }
@media (prefers-reduced-motion: reduce) {
  .usage-insights * { animation: none !important; transition: none !important; }
}
`;

// ─── DOM helpers ──────────────────────────────────────────────────────────

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function text(value) {
  if (value == null) return "—";
  return String(value);
}

function formatCost(value) {
  if (value == null || !Number.isFinite(value)) return "—";
  if (value === 0) return "$0";
  if (value < 0.01) return `$${value.toFixed(6)}`;
  if (value < 1) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(2)}`;
}

function formatTokens(value) {
  if (value == null || !Number.isFinite(value) || value === 0) return "0";
  if (value < 1000) return String(Math.round(value));
  if (value < 1_000_000) return `${(value / 1000).toFixed(1)}k`;
  return `${(value / 1_000_000).toFixed(1)}M`;
}

function formatPct(value) {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${value.toFixed(1)}%`;
}

function formatTime(value, options = {}) {
  if (!value) return "—";
  const time = Date.parse(value);
  if (!Number.isFinite(time)) return "—";
  return new Intl.DateTimeFormat(undefined, options).format(new Date(time));
}

function relativeTime(value) {
  if (!value) return "—";
  const time = Date.parse(value);
  if (!Number.isFinite(time)) return "—";
  const seconds = Math.round((time - Date.now()) / 1000);
  const fmt = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  if (Math.abs(seconds) < 60) return fmt.format(seconds, "second");
  const minutes = Math.round(seconds / 60);
  if (Math.abs(minutes) < 60) return fmt.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return fmt.format(hours, "hour");
  return fmt.format(Math.round(hours / 24), "day");
}

function parseTime(value) {
  if (!value) return 0;
  const t = Date.parse(value);
  return Number.isFinite(t) ? t : 0;
}

function finitNum(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function finitNumOr0(value) {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : 0;
}

// ─── Pagination ───────────────────────────────────────────────────────────

function normalizePage(response, label) {
  const page = response && typeof response === "object" && !Array.isArray(response) ? response : null;
  if (!page || !Array.isArray(page.items)) throw new Error(`${label} returned an unexpected response.`);
  return {
    items: page.items.filter((item) => item && typeof item === "object" && !Array.isArray(item)),
    nextPageId: typeof page.next_page_id === "string" && page.next_page_id ? page.next_page_id : null,
  };
}

async function fetchPaginated(host, basePath, disposed, maxItems, onProgress) {
  const items = [];
  let pageId = null;
  let pages = 0;
  const maxPages = Math.ceil(maxItems / 100) + 1;
  do {
    const params = new URLSearchParams({ limit: "100" });
    if (pageId) params.set("page_id", pageId);
    const response = await host.agentServer.request({ path: `${basePath}?${params}` });
    if (disposed()) return { items, truncated: false };
    const page = normalizePage(response, basePath.includes("events") ? "Event search" : "Conversation search");
    items.push(...page.items);
    pages++;
    onProgress?.(items.length);
    // Terminate on repeated cursor (server bug) or item cap
    if (page.nextPageId === pageId) break;
    pageId = page.nextPageId;
    if (items.length >= maxItems) return { items: items.slice(0, maxItems), truncated: true };
  } while (pageId && pages < maxPages);
  return { items, truncated: pages >= maxPages || items.length >= maxItems };
}

async function fetchEventsFromCursor(host, basePath, disposed, maxItems, startPageId) {
  const items = [];
  let pageId = startPageId ?? null;
  let pages = 0;
  const maxPages = Math.ceil(maxItems / 100) + 1;
  do {
    const params = new URLSearchParams({ limit: "100" });
    if (pageId) params.set("page_id", pageId);
    const response = await host.agentServer.request({ path: `${basePath}?${params}` });
    if (disposed()) return { items, nextPageId: pageId };
    const page = normalizePage(response, "Event search");
    items.push(...page.items);
    pages++;
    if (page.nextPageId === pageId) break;
    pageId = page.nextPageId;
    if (items.length >= maxItems) return { items: items.slice(0, maxItems), nextPageId: pageId };
  } while (pageId && pages < maxPages);
  return { items, nextPageId: pageId };
}

// ─── Stats normalization ───────────────────────────────────────────────────

function extractUsageMetrics(value) {
  if (!value || typeof value !== "object") return null;
  const stats = value.stats || value;
  const usage = stats.usage_to_metrics;
  if (!usage || typeof usage !== "object") return null;
  const out = {};
  for (const [key, metrics] of Object.entries(usage)) {
    if (!metrics || typeof metrics !== "object") continue;
    const token = metrics.accumulated_token_usage || {};
    out[key] = {
      usageKey: key,
      modelName: typeof metrics.model_name === "string" ? metrics.model_name : (typeof token.model === "string" ? token.model : null),
      accumulatedCost: finitNum(metrics.accumulated_cost),
      maxBudgetPerTask: finitNum(metrics.max_budget_per_task),
      promptTokens: finitNumOr0(token.prompt_tokens),
      completionTokens: finitNumOr0(token.completion_tokens),
      cacheReadTokens: finitNumOr0(token.cache_read_tokens),
      cacheWriteTokens: finitNumOr0(token.cache_write_tokens),
      reasoningTokens: finitNumOr0(token.reasoning_tokens),
      contextWindow: finitNumOr0(token.context_window),
      perTurnToken: finitNumOr0(token.per_turn_token),
    };
  }
  return Object.keys(out).length ? out : null;
}

function isStatsEvent(event) {
  if (!event || event.kind !== "ConversationStateUpdateEvent") return false;
  const key = event.key;
  if (key === "stats") return true;
  if (key === "full_state" && event.value && event.value.stats) return true;
  return false;
}

function normalizeSample(event, conversationId) {
  const metrics = extractUsageMetrics(event.value);
  if (!metrics) return [];
  const ts = parseTime(event.timestamp);
  const samples = [];
  for (const m of Object.values(metrics)) {
    const id = event.id ?? `${conversationId}-${m.usageKey}-${ts}`;
    samples.push({
      id,
      timestamp: ts,
      conversationId,
      usageKey: m.usageKey,
      modelName: m.modelName,
      accumulatedCost: m.accumulatedCost,
      maxBudgetPerTask: m.maxBudgetPerTask,
      promptTokens: m.promptTokens,
      completionTokens: m.completionTokens,
      cacheReadTokens: m.cacheReadTokens,
      cacheWriteTokens: m.cacheWriteTokens,
      reasoningTokens: m.reasoningTokens,
      contextWindow: m.contextWindow,
      perTurnToken: m.perTurnToken,
    });
  }
  return samples;
}

function dedupeSamples(samples) {
  const seen = new Set();
  return samples.filter((s) => {
    if (seen.has(s.id)) return false;
    seen.add(s.id);
    return true;
  });
}

function sortSamples(samples) {
  return [...samples].sort((a, b) =>
    a.timestamp - b.timestamp ||
    String(a.conversationId).localeCompare(String(b.conversationId)) ||
    String(a.usageKey).localeCompare(String(b.usageKey)) ||
    String(a.id).localeCompare(String(b.id))
  );
}

// ─── Delta calculation ─────────────────────────────────────────────────────

const SAMPLE_KEY = (s) => `${s.conversationId}::${s.usageKey}::${s.modelName ?? ""}`;

function computeDeltasFromSorted(sorted, byKey) {
  const deltas = [];
  for (const s of sorted) {
    const key = SAMPLE_KEY(s);
    const prev = byKey.get(key);
    if (prev) {
      const d = {
        ...s,
        promptTokens: Math.max(0, s.promptTokens - prev.promptTokens),
        completionTokens: Math.max(0, s.completionTokens - prev.completionTokens),
        cacheReadTokens: Math.max(0, s.cacheReadTokens - prev.cacheReadTokens),
        cacheWriteTokens: Math.max(0, s.cacheWriteTokens - prev.cacheWriteTokens),
        reasoningTokens: Math.max(0, s.reasoningTokens - prev.reasoningTokens),
        accumulatedCost: s.accumulatedCost != null && prev.accumulatedCost != null
          ? Math.max(0, s.accumulatedCost - prev.accumulatedCost)
          : null,
        isBaseline: false,
      };
      if (d.promptTokens > 0 || d.completionTokens > 0 || d.cacheReadTokens > 0 ||
          d.cacheWriteTokens > 0 || d.reasoningTokens > 0 || (d.accumulatedCost ?? 0) > 0) {
        deltas.push(d);
      }
    } else {
      deltas.push({ ...s, isBaseline: true, promptTokens: 0, completionTokens: 0,
        cacheReadTokens: 0, cacheWriteTokens: 0, reasoningTokens: 0, accumulatedCost: null });
    }
    byKey.set(key, s);
  }
  return deltas;
}

function computeDeltas(samples) {
  const sorted = sortSamples(dedupeSamples(samples));
  return computeDeltasFromSorted(sorted, new Map());
}

function buildLastByKey(samples) {
  const sorted = sortSamples(dedupeSamples(samples));
  const byKey = new Map();
  for (const s of sorted) byKey.set(SAMPLE_KEY(s), s);
  return byKey;
}

function computeDeltasIncremental(newSamples, byKey) {
  const sorted = sortSamples(dedupeSamples(newSamples));
  return computeDeltasFromSorted(sorted, byKey);
}

function groupDeltasByConversation(deltas) {
  const map = new Map();
  for (const d of deltas) {
    const arr = map.get(d.conversationId);
    if (arr) arr.push(d);
    else map.set(d.conversationId, [d]);
  }
  return map;
}

// ─── Current totals ───────────────────────────────────────────────────────

function computeCurrentTotals(samples) {
  const sorted = sortSamples(dedupeSamples(samples));
  const latest = new Map();
  for (const s of sorted) {
    const key = `${s.conversationId}::${s.usageKey}::${s.modelName ?? ""}`;
    latest.set(key, s);
  }
  return [...latest.values()];
}

// ─── Cost provenance ───────────────────────────────────────────────────────

function matchCatalogEntry(modelName) {
  if (!modelName || typeof modelName !== "string") return null;
  const lower = modelName.toLowerCase();
  // Try exact match first, then prefix/contains
  for (const entry of CATALOG) {
    if (lower === entry.modelId.toLowerCase() || lower === `${entry.providerId}/${entry.modelId}`.toLowerCase()) {
      return entry;
    }
  }
  for (const entry of CATALOG) {
    if (lower.includes(entry.modelId.toLowerCase())) {
      return entry;
    }
  }
  return null;
}

function calculateCatalogCost(delta, entry) {
  if (!entry) return null;
  const prompt = delta.promptTokens;
  const completion = delta.completionTokens;
  const cacheRead = delta.cacheReadTokens;
  const cacheWrite = delta.cacheWriteTokens;
  // Reasoning tokens are part of completion by default — do not price separately
  let cost = 0;
  let hasAllRates = true;
  if (entry.inputUsdPerMillion != null) {
    cost += (prompt * entry.inputUsdPerMillion) / 1_000_000;
  } else { hasAllRates = false; }
  if (entry.outputUsdPerMillion != null) {
    cost += (completion * entry.outputUsdPerMillion) / 1_000_000;
  } else { hasAllRates = false; }
  // Cache dimensions: only price if rate exists, otherwise leave unpriced
  let cacheCost = 0;
  let cachePriced = true;
  if (cacheRead > 0) {
    if (entry.cacheReadUsdPerMillion != null) {
      cacheCost += (cacheRead * entry.cacheReadUsdPerMillion) / 1_000_000;
    } else { cachePriced = false; }
  }
  if (cacheWrite > 0) {
    if (entry.cacheWriteUsdPerMillion != null) {
      cacheCost += (cacheWrite * entry.cacheWriteUsdPerMillion) / 1_000_000;
    } else { cachePriced = false; }
  }
  if (!hasAllRates || !cachePriced) return null;
  return cost + cacheCost;
}

function resolveCostProvenance(delta) {
  // 1. Reported — server accumulated_cost delta
  if (delta.accumulatedCost != null && Number.isFinite(delta.accumulatedCost) && delta.accumulatedCost > 0) {
    return { source: "reported", cost: delta.accumulatedCost };
  }
  // 2. Catalog estimate
  if (delta.modelName) {
    const entry = matchCatalogEntry(delta.modelName);
    if (entry) {
      const calc = calculateCatalogCost(delta, entry);
      if (calc != null) {
        return { source: "catalog", cost: calc, catalogEntry: entry };
      }
    }
  }
  // 3. Unpriced
  return { source: "unpriced", cost: null };
}

function provenanceLabel(source) {
  switch (source) {
    case "reported": return "Reported";
    case "catalog": return "Catalog estimate";
    case "unpriced": return "Unpriced";
    case "mixed": return "Mixed";
    default: return "—";
  }
}

function provenanceBadgeClass(source) {
  switch (source) {
    case "reported": return "usage-insights__badge--reported";
    case "catalog": return "usage-insights__badge--catalog";
    case "unpriced": return "usage-insights__badge--unpriced";
    case "mixed": return "usage-insights__badge--mixed";
    default: return "";
  }
}

// ─── Aggregation ───────────────────────────────────────────────────────────

const PERIODS = [
  { id: "24h", label: "24 hours", days: 1, useHours: true },
  { id: "7d", label: "7 days", days: 7 },
  { id: "30d", label: "30 days", days: 30 },
  { id: "90d", label: "90 days", days: 90 },
];

function periodStart(periodId) {
  const now = Date.now();
  const period = PERIODS.find((p) => p.id === periodId);
  if (!period) return now - 90 * 24 * 60 * 60 * 1000;
  return now - period.days * 24 * 60 * 60 * 1000;
}

function bucketKey(timestamp, periodId) {
  const date = new Date(timestamp);
  const period = PERIODS.find((p) => p.id === periodId);
  if (period?.useHours) {
    // Hourly UTC buckets for 24h window
    return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}-${String(date.getUTCDate()).padStart(2, "0")} ${String(date.getUTCHours()).padStart(2, "0")}:00`;
  }
  // Local day buckets for 7/30/90-day windows
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(date);
}

function aggregateDeltas(deltas, periodId) {
  const start = periodStart(periodId);
  const inRange = deltas.filter((d) => d.timestamp >= start && !d.isBaseline);
  const buckets = new Map();
  let totalCost = 0;
  let totalUnpricedTokens = 0;
  let totalPrompt = 0;
  let totalCompletion = 0;
  let totalCacheRead = 0;
  let totalCacheWrite = 0;
  let totalReasoning = 0;
  const conversations = new Set();
  const models = new Map();
  const budgetWarnings = [];
  let pricedCount = 0;
  let unpricedCount = 0;
  let reportedCount = 0;
  let catalogCount = 0;

  for (const d of inRange) {
    conversations.add(d.conversationId);
    const bucket = bucketKey(d.timestamp, periodId);
    if (!buckets.has(bucket)) {
      buckets.set(bucket, { key: bucket, cost: 0, tokens: 0, unpricedTokens: 0 });
    }
    const b = buckets.get(bucket);
    const prov = resolveCostProvenance(d);
    if (prov.cost != null) {
      totalCost += prov.cost;
      b.cost += prov.cost;
      pricedCount++;
    } else {
      unpricedCount++;
    }
    if (prov.source === "reported") reportedCount++;
    if (prov.source === "catalog") catalogCount++;

    const tokenSum = d.promptTokens + d.completionTokens + d.cacheReadTokens + d.cacheWriteTokens + d.reasoningTokens;
    b.tokens += tokenSum;
    if (prov.cost == null) {
      totalUnpricedTokens += tokenSum;
      b.unpricedTokens += tokenSum;
    }

    totalPrompt += d.promptTokens;
    totalCompletion += d.completionTokens;
    totalCacheRead += d.cacheReadTokens;
    totalCacheWrite += d.cacheWriteTokens;
    totalReasoning += d.reasoningTokens;

    const modelKey = d.modelName ?? "unknown";
    if (!models.has(modelKey)) {
      models.set(modelKey, { name: modelKey, cost: 0, tokens: 0, prompt: 0, completion: 0, cacheRead: 0, cacheWrite: 0, reasoning: 0, provenance: null, conversations: new Set(), unpriced: false });
    }
    const m = models.get(modelKey);
    if (prov.cost != null) m.cost += prov.cost;
    else m.unpriced = true;
    m.tokens += tokenSum;
    m.prompt += d.promptTokens;
    m.completion += d.completionTokens;
    m.cacheRead += d.cacheReadTokens;
    m.cacheWrite += d.cacheWriteTokens;
    m.reasoning += d.reasoningTokens;
    m.conversations.add(d.conversationId);
    // Track provenance: if any delta is reported, mark as reported; else if catalog, mark catalog; else unpriced
    if (prov.source === "reported") m.provenance = "reported";
    else if (m.provenance !== "reported" && prov.source === "catalog") m.provenance = "catalog";
    else if (!m.provenance) m.provenance = "unpriced";

    if (d.maxBudgetPerTask != null && d.maxBudgetPerTask > 0 && d.accumulatedCost != null) {
      const pct = (d.accumulatedCost / d.maxBudgetPerTask) * 100;
      if (pct >= 100) {
        budgetWarnings.push({ conversationId: d.conversationId, pct, cost: d.accumulatedCost, budget: d.maxBudgetPerTask, over: true });
      } else if (pct >= 80 && pct < 100) {
        budgetWarnings.push({ conversationId: d.conversationId, pct, cost: d.accumulatedCost, budget: d.maxBudgetPerTask, over: false });
      }
    }
  }

  const sortedBuckets = [...buckets.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([, v]) => v);
  const cacheTotal = totalCacheRead + totalCacheWrite;
  const tokenTotal = totalPrompt + totalCompletion + cacheTotal + totalReasoning;
  const cacheShare = tokenTotal > 0 ? (cacheTotal / tokenTotal) * 100 : 0;

  let aggregateProvenance = "unpriced";
  if (reportedCount > 0 && catalogCount > 0) aggregateProvenance = "mixed";
  else if (reportedCount > 0) aggregateProvenance = "reported";
  else if (catalogCount > 0) aggregateProvenance = "catalog";

  return {
    buckets: sortedBuckets,
    totalCost,
    totalUnpricedTokens,
    totalPrompt,
    totalCompletion,
    totalCacheRead,
    totalCacheWrite,
    totalReasoning,
    cacheShare,
    conversationCount: conversations.size,
    models: [...models.values()].map((m) => ({ ...m, conversationCount: m.conversations.size })),
    budgetWarnings,
    pricedCount,
    unpricedCount,
    provenance: aggregateProvenance,
  };
}

// ─── Conversation metadata extraction ──────────────────────────────────────

function extractConversationSummary(conv) {
  if (!conv || typeof conv !== "object") return null;
  const usage = conv.stats?.usage_to_metrics;
  let accumulatedCost = 0;
  let maxBudget = null;
  const modelSet = new Set();
  if (usage && typeof usage === "object") {
    for (const m of Object.values(usage)) {
      if (m && typeof m === "object") {
        const c = finitNum(m.accumulated_cost);
        if (c != null) accumulatedCost += c;
        const b = finitNum(m.max_budget_per_task);
        if (b != null && b > 0) maxBudget = Math.max(maxBudget ?? 0, b);
        if (typeof m.model_name === "string") modelSet.add(m.model_name);
        else if (m.accumulated_token_usage?.model) modelSet.add(m.accumulated_token_usage.model);
      }
    }
  }
  return {
    id: conv.id,
    title: conv.title || "Untitled conversation",
    status: conv.execution_status ?? "unknown",
    createdAt: conv.created_at ?? null,
    updatedAt: conv.updated_at ?? null,
    models: [...modelSet],
    accumulatedCost,
    maxBudget,
    currentModelId: conv.current_model_id ?? null,
  };
}

// ─── IndexedDB persistence ─────────────────────────────────────────────────

function openDB(backendId) {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") { resolve(null); return; }
    const req = indexedDB.open(`${CACHE_DB_NAME}-${backendId}`, CACHE_DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("samples")) {
        db.createObjectStore("samples", { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains("meta")) {
        db.createObjectStore("meta", { keyPath: "key" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => resolve(null);
  });
}

async function cacheSamples(db, samples) {
  if (!db) return;
  return new Promise((resolve) => {
    const tx = db.transaction("samples", "readwrite");
    const store = tx.objectStore("samples");
    for (const s of samples) store.put(s);
    tx.oncomplete = () => resolve();
    tx.onerror = () => resolve();
  });
}

async function clearCache(db) {
  if (!db) return;
  return new Promise((resolve) => {
    const tx = db.transaction(["samples", "meta"], "readwrite");
    tx.objectStore("samples").clear();
    tx.objectStore("meta").clear();
    tx.oncomplete = () => resolve();
    tx.onerror = () => resolve();
  });
}

async function pruneExpired(db) {
  if (!db) return;
  const cutoff = Date.now() - CACHE_RETENTION_DAYS * 24 * 60 * 60 * 1000;
  return new Promise((resolve) => {
    const tx = db.transaction("samples", "readwrite");
    const store = tx.objectStore("samples");
    const req = store.openCursor();
    req.onsuccess = () => {
      const cursor = req.result;
      if (cursor) {
        if (cursor.value.timestamp < cutoff) cursor.delete();
        cursor.continue();
      }
    };
    req.onerror = () => resolve();
    tx.oncomplete = () => resolve();
  });
}

// ─── UI Rendering ─────────────────────────────────────────────────────────

function renderOverview(state, nodes, navigate) {
  const { container, host, db } = nodes;
  container.replaceChildren();

  const shell = el("div", "usage-insights__shell");

  // Header
  const header = el("header", "usage-insights__header");
  const heading = el("div", "usage-insights__heading");
  heading.append(
    el("h1", "", "Usage Insights"),
    el("p", "", "Token usage and estimated cost from conversations on this Agent Server.")
  );
  const actions = el("div", "usage-insights__header-actions");
  const refreshBtn = el("button", "usage-insights__button usage-insights__button--primary", state.loading ? "Loading…" : "Refresh");
  refreshBtn.type = "button";
  refreshBtn.disabled = state.loading;
  refreshBtn.addEventListener("click", () => state.refresh());
  actions.append(refreshBtn);
  if (state.lastUpdated) {
    const updated = el("span", `usage-insights__updated${state.hasActiveRuns ? " usage-insights__updated--live" : ""}`);
    updated.textContent = `Updated ${relativeTime(state.lastUpdated)}${state.hasActiveRuns ? " · live" : ""}`;
    actions.append(updated);
  }
  header.append(heading, actions);
  shell.append(header);

  // Error state
  if (state.error) {
    shell.append(el("div", "usage-insights__notice usage-insights__notice--error", state.error));
  }

  // Loading state (initial)
  if (state.loading && state.conversations.length === 0) {
    const loading = el("div", "usage-insights__loading");
    loading.append(el("span", "usage-insights__spinner"), el("span", "", `Loading conversations…${state.loadedCount ? ` ${state.loadedCount} found` : ""}`));
    shell.append(loading);
    container.append(shell);
    return;
  }

  // Error state with no data — show error only
  if (state.error && state.conversations.length === 0) {
    container.append(shell);
    return;
  }

  // Empty state
  if (!state.loading && state.conversations.length === 0 && !state.error) {
    shell.append(el("div", "usage-insights__notice", "No conversations found on this Agent Server."));
    container.append(shell);
    return;
  }

  // Partial history notice
  if (state.partialHistory) {
    const partial = el("div", "usage-insights__partial");
    partial.textContent = `History limited to ${MAX_CONVERSATIONS} conversations and ${MAX_EVENTS_PER_CONVERSATION.toLocaleString()} stats events per conversation. Coverage may be incomplete.`;
    shell.append(partial);
  }

  // Stale cache notice
  if (state.staleCache) {
    shell.append(el("div", "usage-insights__notice usage-insights__notice--info",
      "Showing cached data — the Agent Server is unreachable. Last updated " + relativeTime(state.lastUpdated) + "."));
  }

  // Toolbar
  const toolbar = el("div", "usage-insights__toolbar");
  const filters = el("div", "usage-insights__filters");

  // Metric selector
  const metricGroup = el("div", "usage-insights__filter-group");
  metricGroup.append(el("label", "usage-insights__filter-label", "Metric:"));
  const metricSelect = el("select", "usage-insights__select");
  metricSelect.setAttribute("aria-label", "Metric selector");
  for (const m of ["cost", "tokens"]) {
    const opt = el("option", "", m === "cost" ? "Cost" : "Tokens");
    opt.value = m;
    if (state.metric === m) opt.selected = true;
    metricSelect.append(opt);
  }
  metricSelect.addEventListener("change", () => { state.metric = metricSelect.value; renderOverview(state, nodes, navigate); });
  metricGroup.append(metricSelect);
  filters.append(metricGroup);

  // Period selector
  const periodGroup = el("div", "usage-insights__filter-group");
  periodGroup.append(el("label", "usage-insights__filter-label", "Period:"));
  const periodSelect = el("select", "usage-insights__select");
  periodSelect.setAttribute("aria-label", "Period selector");
  for (const p of PERIODS) {
    const opt = el("option", "", p.label);
    opt.value = p.id;
    if (state.period === p.id) opt.selected = true;
    periodSelect.append(opt);
  }
  periodSelect.addEventListener("change", () => { state.period = periodSelect.value; renderOverview(state, nodes, navigate); });
  periodGroup.append(periodSelect);
  filters.append(periodGroup);

  // Model filter
  const modelGroup = el("div", "usage-insights__filter-group");
  modelGroup.append(el("label", "usage-insights__filter-label", "Model:"));
  const modelSelect = el("select", "usage-insights__select");
  modelSelect.setAttribute("aria-label", "Model filter");
  const allOpt = el("option", "", "All models"); allOpt.value = "all"; if (state.modelFilter === "all") allOpt.selected = true; modelSelect.append(allOpt);
  for (const m of state.allModels) {
    const opt = el("option", "", m); opt.value = m; if (state.modelFilter === m) opt.selected = true; modelSelect.append(opt);
  }
  modelSelect.addEventListener("change", () => { state.modelFilter = modelSelect.value; renderOverview(state, nodes, navigate); });
  modelGroup.append(modelSelect);
  filters.append(modelGroup);

  // Status filter
  const statusGroup = el("div", "usage-insights__filter-group");
  statusGroup.append(el("label", "usage-insights__filter-label", "Status:"));
  const statusSelect = el("select", "usage-insights__select");
  statusSelect.setAttribute("aria-label", "Status filter");
  for (const s of ["all", "running", "idle", "finished", "error", "stopped"]) {
    const opt = el("option", "", s === "all" ? "All statuses" : s); opt.value = s;
    if (state.statusFilter === s) opt.selected = true; statusSelect.append(opt);
  }
  statusSelect.addEventListener("change", () => { state.statusFilter = statusSelect.value; renderOverview(state, nodes, navigate); });
  statusGroup.append(statusSelect);
  filters.append(statusGroup);

  // Clear filters
  const clearBtn = el("button", "usage-insights__button usage-insights__button--small", "Clear filters");
  clearBtn.type = "button";
  clearBtn.addEventListener("click", () => {
    state.modelFilter = "all"; state.statusFilter = "all"; state.metric = "cost"; state.period = "7d";
    renderOverview(state, nodes, navigate);
  });
  filters.append(clearBtn);

  // Clear cache
  const clearCacheBtn = el("button", "usage-insights__button usage-insights__button--small", "Clear local cache");
  clearCacheBtn.type = "button";
  clearCacheBtn.addEventListener("click", async () => {
    await clearCache(db);
    state.refresh();
  });
  filters.append(clearCacheBtn);

  toolbar.append(filters);
  shell.append(toolbar);

  // Aggregate deltas with filters
  const convMap = new Map(state.conversations.map((c) => [c.id, c]));
  const filteredDeltas = state.allDeltas.filter((d) => {
    if (state.modelFilter !== "all" && (d.modelName ?? "unknown") !== state.modelFilter) return false;
    const conv = convMap.get(d.conversationId);
    if (conv && state.statusFilter !== "all" && conv.status !== state.statusFilter) return false;
    return true;
  });

  const agg = aggregateDeltas(filteredDeltas, state.period);

  // Summary cards
  const cards = el("div", "usage-insights__cards");
  const provBadge = el("span", `usage-insights__badge ${provenanceBadgeClass(agg.provenance)}`, provenanceLabel(agg.provenance));

  const costCard = el("div", "usage-insights__card");
  const costLabel = el("span", "usage-insights__card-label", "Known cost");
  const costValue = el("span", "usage-insights__card-value", formatCost(agg.totalCost));
  const costSub = el("span", "usage-insights__card-sub", "Estimated API-equivalent cost — not a provider invoice.");
  costCard.append(costLabel, costValue, costSub, provBadge);
  cards.append(costCard);

  const unpricedCard = el("div", "usage-insights__card");
  unpricedCard.append(
    el("span", "usage-insights__card-label", "Unpriced tokens"),
    el("span", "usage-insights__card-value", formatTokens(agg.totalUnpricedTokens)),
    el("span", "usage-insights__card-sub", agg.totalUnpricedTokens > 0 ? "Token usage available, but no matching price configured." : "All usage has a price source.")
  );
  cards.append(unpricedCard);

  const promptCard = el("div", "usage-insights__card");
  promptCard.append(
    el("span", "usage-insights__card-label", "Prompt tokens"),
    el("span", "usage-insights__card-value", formatTokens(agg.totalPrompt)),
    el("span", "usage-insights__card-sub", `Completion: ${formatTokens(agg.totalCompletion)}`)
  );
  cards.append(promptCard);

  const cacheCard = el("div", "usage-insights__card");
  cacheCard.append(
    el("span", "usage-insights__card-label", "Cache tokens"),
    el("span", "usage-insights__card-value", formatTokens(agg.totalCacheRead + agg.totalCacheWrite)),
    el("span", "usage-insights__card-sub", `Cache share: ${formatPct(agg.cacheShare)} · Read: ${formatTokens(agg.totalCacheRead)} · Write: ${formatTokens(agg.totalCacheWrite)}`)
  );
  cards.append(cacheCard);

  const convCard = el("div", "usage-insights__card");
  convCard.append(
    el("span", "usage-insights__card-label", "Conversations"),
    el("span", "usage-insights__card-value", String(agg.conversationCount)),
    el("span", "usage-insights__card-sub", `Reasoning tokens: ${formatTokens(agg.totalReasoning)}`)
  );
  cards.append(convCard);

  if (agg.budgetWarnings.length > 0) {
    const warnCard = el("div", "usage-insights__card usage-insights__card--warning");
    const overCount = agg.budgetWarnings.filter((w) => w.over).length;
    warnCard.append(
      el("span", "usage-insights__card-label", "Budget warnings"),
      el("span", "usage-insights__card-value", String(agg.budgetWarnings.length)),
      el("span", "usage-insights__card-sub", overCount > 0 ? `${overCount} over budget` : "Approaching budget limit")
    );
    cards.append(warnCard);
  }

  shell.append(cards);

  // Trend chart
  if (agg.buckets.length > 0) {
    const trendSection = el("section", "usage-insights__section");
    trendSection.append(el("h2", "", "Usage trend"), el("p", "", state.metric === "cost" ? "Known cost per time bucket." : "Token volume per time bucket."));
    const chart = el("div", "usage-insights__bar-chart");
    chart.setAttribute("role", "img");
    chart.setAttribute("aria-label", `${state.metric === "cost" ? "Cost" : "Token"} trend over ${PERIODS.find((p) => p.id === state.period)?.label ?? "selected period"}`);
    const maxVal = Math.max(...agg.buckets.map((b) => state.metric === "cost" ? b.cost : b.tokens), 1);
    const displayBuckets = agg.buckets.slice(-30);
    for (const b of displayBuckets) {
      const val = state.metric === "cost" ? b.cost : b.tokens;
      const bar = el("div", "usage-insights__bar");
      bar.style.height = `${Math.max(2, (val / maxVal) * 100)}%`;
      bar.title = `${b.key}: ${state.metric === "cost" ? formatCost(val) : formatTokens(val)}`;
      chart.append(bar);
    }
    trendSection.append(chart);

    // Table alternative
    const tableWrap = el("div", "usage-insights__table--scroll");
    const table = el("table", "usage-insights__table");
    const thead = el("thead");
    { const tr = el("tr"); tr.append(...["Bucket", state.metric === "cost" ? "Cost" : "Tokens", "Unpriced tokens"].map((h) => el("th", "", h))); thead.append(tr); }
    const tbody = el("tbody");
    for (const b of displayBuckets) {
      const row = el("tr");
      row.append(
        el("td", "", b.key),
        el("td", "", state.metric === "cost" ? formatCost(b.cost) : formatTokens(b.tokens)),
        el("td", "", formatTokens(b.unpricedTokens))
      );
      tbody.append(row);
    }
    table.append(thead, tbody);
    tableWrap.append(table);
    trendSection.append(tableWrap);
    shell.append(trendSection);
  }

  // Model breakdown table
  if (agg.models.length > 0) {
    const modelSection = el("section", "usage-insights__section");
    modelSection.append(el("h2", "", "Model breakdown"), el("p", "", "Cost and token usage by model with price provenance."));
    const tableWrap = el("div", "usage-insights__table--scroll");
    const table = el("table", "usage-insights__table");
    const thead = el("thead");
    { const tr = el("tr"); tr.append(...["Model", "Cost", "Tokens", "Conversations", "Provenance"].map((h) => el("th", "", h))); thead.append(tr); }
    const tbody = el("tbody");
    for (const m of agg.models) {
      const row = el("tr");
      row.append(
        el("td", "", m.name),
        el("td", "", m.unpriced && m.cost === 0 ? "—" : formatCost(m.cost)),
        el("td", "", formatTokens(m.tokens)),
        el("td", "", String(m.conversationCount)),
        el("td", "", "")
      );
      const badge = el("span", `usage-insights__badge ${provenanceBadgeClass(m.provenance)}`, provenanceLabel(m.provenance));
      row.lastChild.append(badge);
      tbody.append(row);
    }
    table.append(thead, tbody);
    tableWrap.append(table);
    modelSection.append(tableWrap);
    shell.append(modelSection);
  }

  // Conversation table
  const convSection = el("section", "usage-insights__section");
  convSection.append(el("h2", "", "Conversations"), el("p", "", "Click a conversation for detailed usage."));
  const convTableWrap = el("div", "usage-insights__table--scroll");
  const convTable = el("table", "usage-insights__table");
  const convThead = el("thead");
  { const cvtr = el("tr"); cvtr.append(...["Title", "Status", "Model", "Cost", "Tokens", "Budget", "Provenance"].map((h) => el("th", "", h))); convThead.append(cvtr); }
  const convTbody = el("tbody");

  const filteredConversations = state.conversations.filter((c) => {
    if (state.statusFilter !== "all" && c.status !== state.statusFilter) return false;
    if (state.modelFilter !== "all" && !c.models.includes(state.modelFilter)) return false;
    return true;
  });

  const deltaByConv = groupDeltasByConversation(state.allDeltas);

  for (const conv of filteredConversations) {
    const convDeltas = (deltaByConv.get(conv.id) ?? []).filter((d) => !d.isBaseline);
    const convAgg = aggregateDeltas(convDeltas, state.period);
    const row = el("tr");
    const titleCell = el("td");
    const link = el("button", "usage-insights__link", conv.title);
    link.type = "button";
    link.addEventListener("click", () => navigate(`${ROOT_PATH}/conversations/${encodeURIComponent(conv.id)}`));
    titleCell.append(link);
    row.append(
      titleCell,
      el("td", "", conv.status),
      el("td", "", conv.models.join(", ") || "—"),
      el("td", "", formatCost(convAgg.totalCost)),
      el("td", "", formatTokens(convAgg.totalPrompt + convAgg.totalCompletion + convAgg.totalCacheRead + convAgg.totalCacheWrite + convAgg.totalReasoning)),
      el("td", "", conv.maxBudget ? `${formatPct((conv.accumulatedCost / conv.maxBudget) * 100)} of ${formatCost(conv.maxBudget)}` : "—"),
      el("td", "", "")
    );
    const pBadge = el("span", `usage-insights__badge ${provenanceBadgeClass(convAgg.provenance)}`, provenanceLabel(convAgg.provenance));
    row.lastChild.append(pBadge);
    convTbody.append(row);
  }
  convTable.append(convThead, convTbody);
  convTableWrap.append(convTable);
  convSection.append(convTableWrap);
  shell.append(convSection);

  // Pricing link
  const pricingLink = el("button", "usage-insights__link", "View pricing coverage →");
  pricingLink.type = "button";
  pricingLink.addEventListener("click", () => navigate(`${ROOT_PATH}/pricing`));
  shell.append(pricingLink);

  container.append(shell);
}

function renderDetail(state, nodes, navigate) {
  const { container } = nodes;
  container.replaceChildren();

  const shell = el("div", "usage-insights__shell");

  // Back link
  const back = el("button", "usage-insights__link usage-insights__back", "← Back to overview");
  back.type = "button";
  back.addEventListener("click", () => navigate(ROOT_PATH));
  shell.append(back);

  if (state.loading) {
    const loading = el("div", "usage-insights__loading");
    loading.append(el("span", "usage-insights__spinner"), el("span", "", "Loading usage data…"));
    shell.append(loading);
    container.append(shell);
    return;
  }

  const conv = state.conversations.find((c) => c.id === state.selectedId);
  if (!conv) {
    shell.append(el("div", "usage-insights__notice", "Conversation not found."));
    container.append(shell);
    return;
  }

  // Header
  const header = el("header", "usage-insights__header");
  const heading = el("div", "usage-insights__heading");
  heading.append(el("h1", "", conv.title), el("p", "", `${conv.status} · ${conv.id}`));
  header.append(heading);
  shell.append(header);

  if (state.eventsLoading) {
    const loading = el("div", "usage-insights__loading");
    loading.append(el("span", "usage-insights__spinner"), el("span", "", "Loading usage history…"));
    shell.append(loading);
    container.append(shell);
    return;
  }

  if (state.eventError) {
    shell.append(el("div", "usage-insights__notice usage-insights__notice--error", state.eventError));
    container.append(shell);
    return;
  }

  // Current totals
  const convSamples = state.allSamples.filter((s) => s.conversationId === conv.id);
  const totals = computeCurrentTotals(convSamples);
  const deltas = computeDeltas(convSamples);

  // Summary cards
  const cards = el("div", "usage-insights__cards");
  let totalCost = 0;
  let totalPrompt = 0;
  let totalCompletion = 0;
  let totalCacheRead = 0;
  let totalCacheWrite = 0;
  let totalReasoning = 0;
  for (const t of totals) {
    if (t.accumulatedCost != null) totalCost += t.accumulatedCost;
    totalPrompt += t.promptTokens;
    totalCompletion += t.completionTokens;
    totalCacheRead += t.cacheReadTokens;
    totalCacheWrite += t.cacheWriteTokens;
    totalReasoning += t.reasoningTokens;
  }

  cards.append(
    el("div", "usage-insights__card",
      el("span", "usage-insights__card-label", "Latest known cost"),
      el("span", "usage-insights__card-value", formatCost(totalCost)),
      el("span", "usage-insights__card-sub", "Reported by Agent Server")
    )
  );
  cards.append(
    el("div", "usage-insights__card",
      el("span", "usage-insights__card-label", "Prompt tokens"),
      el("span", "usage-insights__card-value", formatTokens(totalPrompt)),
      el("span", "usage-insights__card-sub", `Completion: ${formatTokens(totalCompletion)}`)
    )
  );
  cards.append(
    el("div", "usage-insights__card",
      el("span", "usage-insights__card-label", "Cache tokens"),
      el("span", "usage-insights__card-value", formatTokens(totalCacheRead + totalCacheWrite)),
      el("span", "usage-insights__card-sub", `Reasoning: ${formatTokens(totalReasoning)}`)
    )
  );
  if (conv.maxBudget && conv.maxBudget > 0) {
    const pct = Math.min(100, (totalCost / conv.maxBudget) * 100);
    const budgetCard = el("div", `usage-insights__card${pct >= 100 ? " usage-insights__card--warning" : ""}`);
    budgetCard.append(
      el("span", "usage-insights__card-label", "Budget"),
      el("span", "usage-insights__card-value", formatPct(pct)),
      el("span", "usage-insights__card-sub", `${formatCost(totalCost)} of ${formatCost(conv.maxBudget)}`)
    );
    const bar = el("div", "usage-insights__progress");
    const fill = el("div", `usage-insights__progress-fill${pct >= 100 ? " usage-insights__progress-fill--danger" : pct >= 80 ? " usage-insights__progress-fill--warn" : ""}`);
    fill.style.width = `${pct}%`;
    bar.append(fill);
    budgetCard.append(bar);
    cards.append(budgetCard);
  }
  shell.append(cards);

  // Model breakdown
  const modelMap = new Map();
  for (const t of totals) {
    const key = t.modelName ?? "unknown";
    if (!modelMap.has(key)) modelMap.set(key, { name: key, cost: 0, prompt: 0, completion: 0, cacheRead: 0, cacheWrite: 0, reasoning: 0, provenance: null });
    const m = modelMap.get(key);
    if (t.accumulatedCost != null) m.cost += t.accumulatedCost;
    m.prompt += t.promptTokens;
    m.completion += t.completionTokens;
    m.cacheRead += t.cacheReadTokens;
    m.cacheWrite += t.cacheWriteTokens;
    m.reasoning += t.reasoningTokens;
    m.provenance = "reported";
  }

  if (modelMap.size > 0) {
    const modelSection = el("section", "usage-insights__section");
    modelSection.append(el("h2", "", "Model / usage-key breakdown"));
    const list = el("div", "usage-insights__model-list");
    for (const m of [...modelMap.values()]) {
      const row = el("div", "usage-insights__model-row");
      row.append(
        el("span", "usage-insights__model-name", m.name),
        el("span", "usage-insights__model-cost", formatCost(m.cost)),
        el("span", "usage-insights__model-tokens", formatTokens(m.prompt + m.completion + m.cacheRead + m.cacheWrite + m.reasoning))
      );
      list.append(row);
    }
    modelSection.append(list);
    shell.append(modelSection);
  }

  // Token/cost progression
  if (deltas.length > 0) {
    const progressSection = el("section", "usage-insights__section");
    progressSection.append(el("h2", "", "Token and cost progression"), el("p", "", "Observed deltas from persisted stats snapshots."));
    const tableWrap = el("div", "usage-insights__table--scroll");
    const table = el("table", "usage-insights__table");
    const thead = el("thead");
    { const tr = el("tr"); tr.append(...["Time", "Model", "Prompt", "Completion", "Cache R/W", "Cost", "Source"].map((h) => el("th", "", h))); thead.append(tr); }
    const tbody = el("tbody");
    for (const d of deltas) {
      if (d.isBaseline) continue;
      const prov = resolveCostProvenance(d);
      const row = el("tr");
      row.append(
        el("td", "", formatTime(new Date(d.timestamp).toISOString(), { dateStyle: "short", timeStyle: "short" })),
        el("td", "", d.modelName ?? "—"),
        el("td", "", formatTokens(d.promptTokens)),
        el("td", "", formatTokens(d.completionTokens)),
        el("td", "", `${formatTokens(d.cacheReadTokens)} / ${formatTokens(d.cacheWriteTokens)}`),
        el("td", "", prov.cost != null ? formatCost(prov.cost) : "—"),
        el("td", "", "")
      );
      row.lastChild.append(el("span", `usage-insights__badge ${provenanceBadgeClass(prov.source)}`, provenanceLabel(prov.source)));
      tbody.append(row);
    }
    table.append(thead, tbody);
    tableWrap.append(table);
    progressSection.append(tableWrap);
    shell.append(progressSection);
  }

  // Provenance notice
  const provSection = el("section", "usage-insights__section");
  provSection.append(el("h2", "", "Data quality and provenance"));
  const provList = el("div");
  provList.append(
    el("p", "", "Cost shown here is reported by the Agent Server when available. When no server-reported cost exists, a catalog estimate may be used as a fallback."),
    el("p", "", "Reasoning tokens are treated as part of completion tokens to avoid double counting, unless a source explicitly proves otherwise."),
    el("p", "", "History begins with the earliest persisted stats snapshot available to this Agent Server."),
    el("p", "", "Profile-detail pricing is intentionally not read by this App. Manage profile prices in Settings → LLM.")
  );
  provSection.append(provList);
  shell.append(provSection);

  container.append(shell);
}

function renderPricing(state, nodes, navigate) {
  const { container } = nodes;
  container.replaceChildren();

  const shell = el("div", "usage-insights__shell");

  // Back link
  const back = el("button", "usage-insights__link usage-insights__back", "← Back to overview");
  back.type = "button";
  back.addEventListener("click", () => navigate(ROOT_PATH));
  shell.append(back);

  if (state.loading) {
    const loading = el("div", "usage-insights__loading");
    loading.append(el("span", "usage-insights__spinner"), el("span", "", "Loading usage data…"));
    shell.append(loading);
    container.append(shell);
    return;
  }

  shell.append(
    el("h1", "", "Pricing coverage"),
    el("p", "", "Read-only price coverage by model/provider identity. Profile-detail pricing is intentionally not read by this App.")
  );

  // Catalog table
  const section = el("section", "usage-insights__section");
  section.append(el("h2", "", "Bundled catalog rates"), el("p", "", "Public per-million-token rates used as a fallback when server-reported cost is unavailable."));
  const tableWrap = el("div", "usage-insights__table--scroll");
  const table = el("table", "usage-insights__table");
  const thead = el("thead");
  { const tr = el("tr"); tr.append(...["Provider", "Model", "Input $/M", "Output $/M", "Cache read $/M", "Cache write $/M", "Source"].map((h) => el("th", "", h))); thead.append(tr); }
  const tbody = el("tbody");
  for (const entry of CATALOG) {
    const row = el("tr");
    row.append(
      el("td", "", entry.providerId),
      el("td", "", entry.modelId),
      el("td", "", entry.inputUsdPerMillion != null ? `$${entry.inputUsdPerMillion}` : "—"),
      el("td", "", entry.outputUsdPerMillion != null ? `$${entry.outputUsdPerMillion}` : "—"),
      el("td", "", entry.cacheReadUsdPerMillion != null ? `$${entry.cacheReadUsdPerMillion}` : "—"),
      el("td", "", entry.cacheWriteUsdPerMillion != null ? `$${entry.cacheWriteUsdPerMillion}` : "—"),
      el("td", "", "")
    );
    row.lastChild.append(el("span", "usage-insights__badge usage-insights__badge--catalog", `Catalog v${entry.catalogVersion}`));
    tbody.append(row);
  }
  table.append(thead, tbody);
  tableWrap.append(table);
  section.append(tableWrap);

  // Catalog metadata
  section.append(el("p", "usage-insights__provenance", `Catalog version: ${CATALOG_VERSION} · Source: ${CATALOG_SOURCE_URL}`));
  section.append(el("p", "usage-insights__provenance", "Catalog rates require exact provider/model identity match. Omitted cache rates are not inferred from input rates."));
  shell.append(section);

  // Coverage table — models with usage but incomplete coverage
  const usedModels = new Set();
  for (const d of state.allDeltas) {
    if (d.modelName) usedModels.add(d.modelName);
  }
  if (usedModels.size > 0) {
    const coverageSection = el("section", "usage-insights__section");
    coverageSection.append(el("h2", "", "Model coverage"), el("p", "", "Models with observed usage and their price coverage status."));
    const covTableWrap = el("div", "usage-insights__table--scroll");
    const covTable = el("table", "usage-insights__table");
    const covThead = el("thead");
    { const ctr = el("tr"); ctr.append(...["Model", "Coverage", "Match type"].map((h) => el("th", "", h))); covThead.append(ctr); }
    const covTbody = el("tbody");
    for (const model of [...usedModels].sort()) {
      const entry = matchCatalogEntry(model);
      const row = el("tr");
      row.append(
        el("td", "", model),
        el("td", "", ""),
        el("td", "", entry ? (model === `${entry.providerId}/${entry.modelId}` || model === entry.modelId ? "Exact" : "Partial") : "No match")
      );
      if (entry) {
        row.children[1].append(el("span", "usage-insights__badge usage-insights__badge--catalog", "Catalog estimate"));
      } else {
        row.children[1].append(el("span", "usage-insights__badge usage-insights__badge--unpriced", "Unpriced"));
      }
      covTbody.append(row);
    }
    covTable.append(covThead, covTbody);
    covTableWrap.append(covTable);
    coverageSection.append(covTableWrap);
    shell.append(coverageSection);
  }

  // Configured source note
  shell.append(
    el("div", "usage-insights__notice usage-insights__notice--info",
      "Configured source is reserved for a future documented redacted server rate-card capability. It is not available in this version.")
  );

  // Settings link
  shell.append(el("p", "", "Manage profile prices in Settings → LLM."));

  container.append(shell);
}

function renderNotFound(container, navigate) {
  container.replaceChildren();
  const shell = el("div", "usage-insights__shell");
  shell.append(el("div", "usage-insights__notice", "Page not found. "));
  const link = el("button", "usage-insights__link", "Return to Usage Insights");
  link.type = "button";
  link.addEventListener("click", () => navigate(ROOT_PATH));
  shell.lastChild.append(link);
  container.append(shell);
}

// ─── Route parsing ─────────────────────────────────────────────────────────

function parseRoute(path) {
  const trimmed = path.replace(/^\/+|\/+$/g, "");
  if (!trimmed) return { route: "overview" };
  const detailMatch = /^conversations\/([^/]+)$/.exec(trimmed);
  if (detailMatch) {
    try { return { route: "detail", id: decodeURIComponent(detailMatch[1]) }; }
    catch { return { route: "detail", id: detailMatch[1] }; }
  }
  if (trimmed === "pricing") return { route: "pricing" };
  return { route: "unknown" };
}

// ─── Mount ────────────────────────────────────────────────────────────────

function mountUsage(host, { container, path, navigate }) {
  let disposed = false;
  let pollTimer = null;
  let db = null;

  const style = el("style");
  style.textContent = STYLE;
  document.head.append(style);

  const root = el("div", "usage-insights");
  container.append(root);

  const backendId = host.backend?.id || "default";
  const state = {
    conversations: [],
    allSamples: [],
    allDeltas: [],
    allModels: [],
    selectedId: null,
    loading: true,
    eventsLoading: false,
    error: null,
    eventError: null,
    lastUpdated: null,
    hasActiveRuns: false,
    partialHistory: false,
    staleCache: false,
    loadedCount: 0,
    metric: "cost",
    period: "7d",
    modelFilter: "all",
    statusFilter: "all",
    refresh: () => {},
  };

  const nodes = { container: root, host, db: null };
  const isDisposed = () => disposed;

  const route = parseRoute(path);

  const paint = () => {
    if (disposed) return;
    nodes.db = db;
    if (route.route === "overview") {
      renderOverview(state, nodes, navigate);
    } else if (route.route === "detail") {
      state.selectedId = route.id;
      renderDetail(state, nodes, navigate);
    } else if (route.route === "pricing") {
      renderPricing(state, nodes, navigate);
    } else {
      renderNotFound(root, navigate);
    }
  };

  async function loadData() {
    state.loading = true;
    state.error = null;
    state.loadedCount = 0;
    paint();

    try {
      // Open DB
      db = await openDB(backendId);
      await pruneExpired(db);

      // Fetch conversations
      const convResult = await fetchPaginated(host, "/api/conversations/search", isDisposed, MAX_CONVERSATIONS, (count) => {
        state.loadedCount = count;
        paint();
      });
      if (disposed) return;

      state.partialHistory = convResult.truncated;

      const convSummaries = convResult.items.map(extractConversationSummary).filter(Boolean);
      state.conversations = convSummaries.sort((a, b) => parseTime(b.updatedAt) - parseTime(a.updatedAt));

      // Check for active runs
      state.hasActiveRuns = state.conversations.some((c) => c.status === "running" || c.status === "idle");

      // Collect all models
      const modelSet = new Set();
      for (const c of state.conversations) {
        for (const m of c.models) modelSet.add(m);
      }
      state.allModels = [...modelSet].sort();

      // Fetch events for each conversation with bounded concurrency
      const allSamples = [];
      const CONCURRENCY = 5;
      let truncatedAny = false;

      for (let i = 0; i < state.conversations.length; i += CONCURRENCY) {
        if (disposed) return;
        const batch = state.conversations.slice(i, i + CONCURRENCY);
        const results = await Promise.all(batch.map(async (conv) => {
          try {
            const evResult = await fetchPaginated(
              host,
              `/api/conversations/${encodeURIComponent(conv.id)}/events/search`,
              isDisposed,
              MAX_EVENTS_PER_CONVERSATION
            );
            if (disposed) return [];
            if (evResult.truncated) truncatedAny = true;
            const statsEvents = evResult.items.filter(isStatsEvent);
            const samples = [];
            for (const ev of statsEvents) {
              samples.push(...normalizeSample(ev, conv.id));
            }
            return samples;
          } catch {
            return [];
          }
        }));
        if (disposed) return;
        for (const samples of results) allSamples.push(...samples);
      }

      if (truncatedAny) state.partialHistory = true;

      state.allSamples = allSamples;
      state.allDeltas = computeDeltas(allSamples);
      state._deltaByKey = buildLastByKey(allSamples);
      state._pollCursors = new Map();

      // Cache samples
      await cacheSamples(db, allSamples);

      state.loading = false;
      state.lastUpdated = new Date().toISOString();
      state.staleCache = false;
      paint();
    } catch (err) {
      if (disposed) return;
      state.loading = false;
      state.error = err instanceof Error ? err.message : "Unable to load usage data.";
      state.staleCache = state.conversations.length > 0;
      paint();
    }
  }

  state.refresh = () => loadData();

  // Initial load
  loadData();

  // Poll for active conversations
  pollTimer = window.setInterval(async () => {
    if (disposed) return;
    const active = state.conversations.filter((c) => c.status === "running" || c.status === "idle");
    if (active.length === 0) return;
    const byKey = state._deltaByKey;
    const cursors = state._pollCursors ?? new Map();

    for (const conv of active) {
      if (disposed) return;
      try {
        const basePath = `/api/conversations/${encodeURIComponent(conv.id)}/events/search`;
        const cursor = cursors.get(conv.id);
        const evResult = await fetchEventsFromCursor(host, basePath, isDisposed, MAX_EVENTS_PER_CONVERSATION, cursor);
        if (disposed) return;

        // Update cursor for next poll — falls back to null to resume from start
        cursors.set(conv.id, evResult.nextPageId);

        const statsEvents = evResult.items.filter(isStatsEvent);
        const samples = [];
        for (const ev of statsEvents) samples.push(...normalizeSample(ev, conv.id));

        const existingIds = new Set(state.allSamples.map((s) => s.id));
        const newSamples = samples.filter((s) => !existingIds.has(s.id));
        if (newSamples.length > 0) {
          state.allSamples = [...state.allSamples, ...newSamples];
          state.allDeltas = [...state.allDeltas, ...computeDeltasIncremental(newSamples, byKey)];
          await cacheSamples(db, newSamples);
          paint();
        }
      } catch {
        // Ignore polling errors — cursor may be stale on next cycle
      }
    }
  }, POLL_INTERVAL_MS);

  return () => {
    disposed = true;
    if (pollTimer !== null) window.clearInterval(pollTimer);
    style.remove();
    root.remove();
  };
}

// ─── Activation ────────────────────────────────────────────────────────────

export function activate(host) {
  if (host.apiVersion !== "1") throw new Error("Usage Insights requires Canvas host API 1.");
  return host.registerPage("usage", (context) => mountUsage(host, context));
}
