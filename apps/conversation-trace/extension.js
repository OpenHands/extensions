const POLL_INTERVAL_MS = 5_000;
const MAX_EVENTS = 5_000;
const ROOT_PATH = "/extensions/conversation-trace/trace";

const STYLE = `
  .conversation-trace {
    --trace-bg: var(--oh-background, #0b0c0e);
    --trace-panel: var(--oh-surface, #15171a);
    --trace-raised: var(--oh-surface-raised, #1d2024);
    --trace-deep: var(--oh-surface-deep, #0f1113);
    --trace-text: var(--oh-foreground, #f1efe8);
    --trace-muted: var(--oh-text-secondary, #a4a6a9);
    --trace-dim: var(--oh-text-dim, #73777c);
    --trace-border: var(--oh-border-subtle, #30343a);
    --trace-focus: var(--oh-focus, #fff);
    --trace-accent: var(--oh-accent, #d6ff5f);
    --trace-agent: #7dd3fc;
    --trace-user: #fbbf24;
    --trace-tool: #c4b5fd;
    --trace-file: #5eead4;
    --trace-command: #fb923c;
    --trace-error: #fb7185;
    --trace-approval: #facc15;
    min-height: 100%; color: var(--trace-text); background: var(--trace-bg);
    font-family: -apple-system, "SF Pro", BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
  }
  .conversation-trace * { box-sizing: border-box; }
  .conversation-trace button, .conversation-trace input, .conversation-trace select { font: inherit; }
  .conversation-trace__layout { display: grid; grid-template-columns: 19rem minmax(0, 1fr); min-height: 100%; }
  .conversation-trace__sidebar { position: sticky; top: 0; height: 100vh; overflow: auto; border-right: 1px solid var(--trace-border); background: var(--trace-deep); }
  .conversation-trace__brand { padding: 1.2rem 1rem 1rem; border-bottom: 1px solid var(--trace-border); }
  .conversation-trace__eyebrow { margin: 0 0 .35rem; color: var(--trace-accent); font-family: source-code-pro, Menlo, Monaco, Consolas, "Courier New", monospace; font-size: .65rem; font-weight: 800; letter-spacing: .16em; text-transform: uppercase; }
  .conversation-trace__brand h1 { margin: 0; font-family: -apple-system, "SF Pro", BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif; font-size: 1.45rem; font-weight: 500; letter-spacing: -.025em; }
  .conversation-trace__brand p { margin: .45rem 0 0; color: var(--trace-dim); font-size: .72rem; line-height: 1.45; }
  .conversation-trace__sidebar-tools { display: grid; gap: .55rem; padding: .85rem; border-bottom: 1px solid var(--trace-border); }
  .conversation-trace__input, .conversation-trace__select { width: 100%; min-height: 2.25rem; border: 1px solid var(--trace-border); border-radius: .35rem; padding: .48rem .62rem; color: var(--trace-text); background: var(--trace-panel); }
  .conversation-trace__input:focus-visible, .conversation-trace__select:focus-visible, .conversation-trace__button:focus-visible, .conversation-trace__conversation:focus-visible, .conversation-trace__event:focus-visible, .conversation-trace__filter:focus-visible { outline: 2px solid var(--trace-focus); outline-offset: 2px; }
  .conversation-trace__list { display: grid; padding: .45rem; gap: .22rem; }
  .conversation-trace__conversation { width: 100%; display: grid; grid-template-columns: .45rem minmax(0, 1fr); gap: .65rem; align-items: start; border: 1px solid transparent; border-radius: .4rem; padding: .7rem .62rem; color: inherit; background: transparent; text-align: left; cursor: pointer; }
  .conversation-trace__conversation:hover { background: var(--trace-panel); }
  .conversation-trace__conversation[aria-current="true"] { border-color: color-mix(in srgb, var(--trace-accent) 50%, var(--trace-border)); background: var(--trace-panel); }
  .conversation-trace__status-dot { width: .45rem; height: .45rem; margin-top: .25rem; border-radius: 50%; background: var(--trace-dim); }
  .conversation-trace__status-dot--running { background: var(--trace-accent); box-shadow: 0 0 .65rem color-mix(in srgb, var(--trace-accent) 70%, transparent); }
  .conversation-trace__status-dot--error, .conversation-trace__status-dot--stuck { background: var(--trace-error); }
  .conversation-trace__conversation-title { display: block; overflow: hidden; font-size: .78rem; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
  .conversation-trace__conversation-meta { display: flex; justify-content: space-between; gap: .5rem; margin-top: .25rem; color: var(--trace-dim); font-family: source-code-pro, Menlo, Monaco, Consolas, "Courier New", monospace; font-size: .61rem; overflow-wrap: anywhere; }
  .conversation-trace__main { min-width: 0; padding: clamp(1rem, 2vw, 1.8rem); }
  .conversation-trace__empty-page { min-height: calc(100vh - 3.6rem); display: grid; place-items: center; text-align: center; }
  .conversation-trace__empty-mark { width: 4.5rem; height: 4.5rem; display: grid; place-items: center; margin: 0 auto 1rem; border: 1px solid var(--trace-border); border-radius: 50%; color: var(--trace-accent); font-family: -apple-system, "SF Pro", BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif; font-size: 2.4rem; }
  .conversation-trace__empty-page h2 { margin: 0; font-family: -apple-system, "SF Pro", BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif; font-weight: 500; }
  .conversation-trace__empty-page p { max-width: 32rem; margin: .55rem auto 0; color: var(--trace-muted); font-size: .84rem; line-height: 1.55; }
  .conversation-trace__header { display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start; margin-bottom: 1rem; }
  .conversation-trace__header h2 { margin: 0; font-family: -apple-system, "SF Pro", BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif; font-size: clamp(1.5rem, 3vw, 2.25rem); font-weight: 500; letter-spacing: -.035em; }
  .conversation-trace__header-meta { display: flex; flex-wrap: wrap; gap: .45rem .8rem; margin-top: .48rem; color: var(--trace-dim); font-family: source-code-pro, Menlo, Monaco, Consolas, "Courier New", monospace; font-size: .65rem; overflow-wrap: anywhere; }
  .conversation-trace__actions { display: flex; gap: .5rem; flex-wrap: wrap; justify-content: flex-end; }
  .conversation-trace__button { min-height: 2.2rem; border: 1px solid var(--trace-border); border-radius: .35rem; padding: .45rem .7rem; color: var(--trace-text); background: var(--trace-panel); font-size: .72rem; font-weight: 700; cursor: pointer; }
  .conversation-trace__button:hover { border-color: var(--trace-muted); background: var(--trace-raised); }
  .conversation-trace__button:disabled { opacity: .55; cursor: wait; }
  .conversation-trace__overview { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); border: 1px solid var(--trace-border); border-radius: .5rem; overflow: hidden; background: var(--trace-panel); }
  .conversation-trace__metric { min-width: 0; padding: .75rem .85rem; border-right: 1px solid var(--trace-border); }
  .conversation-trace__metric:last-child { border-right: 0; }
  .conversation-trace__metric-label { color: var(--trace-dim); font-size: .6rem; font-weight: 800; letter-spacing: .11em; text-transform: uppercase; }
  .conversation-trace__metric-value { display: block; margin-top: .35rem; overflow: hidden; font-family: source-code-pro, Menlo, Monaco, Consolas, "Courier New", monospace; font-size: 1.05rem; overflow-wrap: anywhere; }
  .conversation-trace__usage { display: grid; grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr)); gap: 1px; margin: .9rem 0; border: 1px solid var(--trace-border); border-radius: .5rem; overflow: hidden; background: var(--trace-border); }
  .conversation-trace__usage-card { padding: .6rem .75rem; background: var(--trace-panel); }
  .conversation-trace__usage-card--cost { grid-column: span 2; }
  .conversation-trace__usage-label { color: var(--trace-dim); font-size: .58rem; font-weight: 800; letter-spacing: .11em; text-transform: uppercase; }
  .conversation-trace__usage-value { display: block; margin-top: .25rem; font-family: source-code-pro, Menlo, Monaco, Consolas, "Courier New", monospace; font-size: .9rem; overflow-wrap: anywhere; }
  .conversation-trace__usage-value--accent { color: var(--trace-accent); font-size: 1.1rem; }
  .conversation-trace__usage-sub { display: block; margin-top: .2rem; color: var(--trace-dim); font-family: source-code-pro, Menlo, Monaco, Consolas, "Courier New", monospace; font-size: .55rem; overflow-wrap: anywhere; }
  .conversation-trace__context-bar { height: .3rem; margin-top: .35rem; border-radius: 999px; background: var(--trace-deep); overflow: hidden; }
  .conversation-trace__context-fill { height: 100%; border-radius: 999px; background: var(--trace-accent); }
  .conversation-trace__context-fill--warn { background: var(--trace-approval); }
  .conversation-trace__context-fill--danger { background: var(--trace-error); }
  .conversation-trace__model-row { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: .5rem; padding: .3rem 0; border-bottom: 1px solid var(--trace-border); font-family: source-code-pro, Menlo, Monaco, Consolas, "Courier New", monospace; font-size: .62rem; }
  .conversation-trace__model-row:last-child { border-bottom: 0; }
  .conversation-trace__model-name { min-width: 0; color: var(--trace-muted); overflow-wrap: anywhere; }
  .conversation-trace__model-cost { color: var(--trace-accent); }
  .conversation-trace__model-tokens { color: var(--trace-dim); }
  .conversation-trace__rail { height: 3.5rem; display: flex; align-items: flex-end; gap: 2px; margin: .9rem 0; padding: .45rem; border: 1px solid var(--trace-border); border-radius: .4rem; background: var(--trace-deep); }
  .conversation-trace__rail-segment { flex: 1; min-width: 2px; height: var(--height, 35%); border-radius: 1px 1px 0 0; background: var(--color, var(--trace-muted)); opacity: .8; }
  .conversation-trace__toolbar { display: flex; align-items: center; gap: .55rem; flex-wrap: wrap; margin-bottom: .8rem; }
  .conversation-trace__toolbar .conversation-trace__input { flex: 1 1 16rem; }
  .conversation-trace__filters { display: flex; gap: .3rem; flex-wrap: wrap; }
  .conversation-trace__filter { border: 1px solid var(--trace-border); border-radius: 999px; padding: .35rem .58rem; color: var(--trace-muted); background: transparent; font-size: .65rem; font-weight: 750; cursor: pointer; }
  .conversation-trace__filter[aria-pressed="true"] { border-color: color-mix(in srgb, var(--filter-color) 65%, var(--trace-border)); color: var(--trace-text); background: color-mix(in srgb, var(--filter-color) 14%, transparent); }
  .conversation-trace__body { display: grid; grid-template-columns: minmax(0, 1fr) minmax(18rem, 30%); gap: .8rem; align-items: start; }
  .conversation-trace__timeline, .conversation-trace__inspector { min-width: 0; border: 1px solid var(--trace-border); border-radius: .5rem; background: var(--trace-panel); }
  .conversation-trace__timeline { position: relative; padding: .5rem; }
  .conversation-trace__timeline::before { content: ""; position: absolute; top: 1.2rem; bottom: 1.2rem; left: 2.05rem; width: 1px; background: var(--trace-border); }
  .conversation-trace__event { --event-color: var(--trace-muted); position: relative; width: 100%; display: grid; grid-template-columns: 2.45rem minmax(0, 1fr); gap: .55rem; border: 0; border-radius: .38rem; padding: .55rem; color: inherit; background: transparent; text-align: left; cursor: pointer; }
  .conversation-trace__event:hover { background: var(--trace-raised); }
  .conversation-trace__event[aria-selected="true"] { background: color-mix(in srgb, var(--event-color) 9%, var(--trace-raised)); box-shadow: inset 2px 0 var(--event-color); }
  .conversation-trace__node { position: relative; z-index: 1; width: 1.25rem; height: 1.25rem; display: grid; place-items: center; margin: .13rem auto 0; border: 1px solid color-mix(in srgb, var(--event-color) 70%, var(--trace-border)); border-radius: 50%; color: var(--event-color); background: var(--trace-panel); font-family: source-code-pro, Menlo, Monaco, Consolas, "Courier New", monospace; font-size: .58rem; font-weight: 900; }
  .conversation-trace__event-top { display: flex; justify-content: space-between; gap: 1rem; align-items: baseline; }
  .conversation-trace__event-name { display: flex; gap: .45rem; align-items: center; min-width: 0; font-size: .74rem; font-weight: 800; }
  .conversation-trace__event-category { color: var(--event-color); font-family: source-code-pro, Menlo, Monaco, Consolas, "Courier New", monospace; font-size: .58rem; letter-spacing: .08em; text-transform: uppercase; }
  .conversation-trace__event-time { flex: none; color: var(--trace-dim); font-family: source-code-pro, Menlo, Monaco, Consolas, "Courier New", monospace; font-size: .6rem; }
  .conversation-trace__event-summary { margin-top: .22rem; overflow: hidden; color: var(--trace-muted); font-size: .72rem; line-height: 1.4; overflow-wrap: anywhere; }
  .conversation-trace__event-badges { display: flex; gap: .3rem; flex-wrap: wrap; margin-top: .35rem; }
  .conversation-trace__badge { padding: .17rem .38rem; border: 1px solid var(--trace-border); border-radius: 999px; color: var(--trace-dim); font-family: source-code-pro, Menlo, Monaco, Consolas, "Courier New", monospace; font-size: .55rem; }
  .conversation-trace__badge--error { border-color: color-mix(in srgb, var(--trace-error) 55%, var(--trace-border)); color: var(--trace-error); }
  .conversation-trace__inspector { position: sticky; top: 1rem; max-height: calc(100vh - 2rem); overflow: auto; }
  .conversation-trace__inspector-header { padding: .85rem; border-bottom: 1px solid var(--trace-border); }
  .conversation-trace__inspector-header h3 { margin: 0; font-family: -apple-system, "SF Pro", BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif; font-size: 1rem; font-weight: 500; }
  .conversation-trace__inspector-header p { margin: .25rem 0 0; color: var(--trace-dim); font-family: source-code-pro, Menlo, Monaco, Consolas, "Courier New", monospace; font-size: .6rem; overflow-wrap: anywhere; word-break: break-all; }
  .conversation-trace__detail { padding: .8rem; border-bottom: 1px solid var(--trace-border); }
  .conversation-trace__detail h4 { margin: 0 0 .45rem; color: var(--trace-dim); font-size: .59rem; letter-spacing: .12em; text-transform: uppercase; }
  .conversation-trace__detail p, .conversation-trace__detail pre { margin: 0; color: var(--trace-muted); font-size: .7rem; line-height: 1.5; overflow-wrap: anywhere; white-space: pre-wrap; }
  .conversation-trace__detail pre { max-height: 19rem; overflow: auto; padding: .65rem; border-radius: .3rem; color: #d7dae0; background: #090a0c; font-family: source-code-pro, Menlo, Monaco, Consolas, "Courier New", monospace; font-size: .62rem; }
  .conversation-trace__notice { padding: 1rem; border: 1px dashed var(--trace-border); border-radius: .4rem; color: var(--trace-muted); font-size: .76rem; line-height: 1.5; text-align: center; }
  .conversation-trace__notice--error { border-style: solid; border-color: color-mix(in srgb, var(--trace-error) 55%, var(--trace-border)); color: var(--trace-error); }
  .conversation-trace__truncate { margin: .6rem 0; color: var(--trace-approval); font-size: .68rem; text-align: center; }
  @media (max-width: 980px) { .conversation-trace__layout { grid-template-columns: 15rem minmax(0, 1fr); } .conversation-trace__body { grid-template-columns: 1fr; } .conversation-trace__inspector { position: static; max-height: none; } }
  @media (max-width: 700px) { .conversation-trace__layout { display: block; } .conversation-trace__sidebar { position: static; height: auto; max-height: 19rem; border-right: 0; border-bottom: 1px solid var(--trace-border); } .conversation-trace__header { flex-direction: column; } .conversation-trace__actions { justify-content: flex-start; } .conversation-trace__overview { grid-template-columns: repeat(2, minmax(0, 1fr)); } .conversation-trace__metric { border-bottom: 1px solid var(--trace-border); } }
  @media (prefers-reduced-motion: reduce) { .conversation-trace * { scroll-behavior: auto !important; transition: none !important; animation: none !important; } }
`;

const CATEGORY = {
  message: { label: "Message", color: "var(--trace-user)", mark: "M" },
  tool: { label: "Tool", color: "var(--trace-tool)", mark: "T" },
  file: { label: "File", color: "var(--trace-file)", mark: "F" },
  command: { label: "Command", color: "var(--trace-command)", mark: ">" },
  approval: { label: "Approval", color: "var(--trace-approval)", mark: "?" },
  error: { label: "Error", color: "var(--trace-error)", mark: "!" },
  state: { label: "State", color: "var(--trace-agent)", mark: "S" },
  other: { label: "Other", color: "var(--trace-muted)", mark: "·" },
};

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function record(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : null;
}

function textContent(value) {
  if (typeof value === "string") return value;
  if (!Array.isArray(value)) return "";
  return value.map((item) => {
    if (typeof item === "string") return item;
    const part = record(item);
    return typeof part?.text === "string" ? part.text : part?.type === "image" ? "[image]" : "";
  }).filter(Boolean).join("\n");
}

function stringify(value, max = 12_000) {
  let output;
  try { output = JSON.stringify(value, null, 2); } catch { output = String(value); }
  return output.length > max ? `${output.slice(0, max)}\n… truncated` : output;
}

function parseTime(value) {
  const time = typeof value === "string" ? Date.parse(value) : NaN;
  return Number.isFinite(time) ? time : 0;
}

function formatTime(value, options = {}) {
  const time = parseTime(value);
  if (!time) return "Unknown time";
  return new Intl.DateTimeFormat(undefined, options).format(new Date(time));
}

function relativeTime(value) {
  const time = parseTime(value);
  if (!time) return "unknown";
  const seconds = Math.round((time - Date.now()) / 1_000);
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  if (Math.abs(seconds) < 60) return formatter.format(seconds, "second");
  const minutes = Math.round(seconds / 60);
  if (Math.abs(minutes) < 60) return formatter.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return formatter.format(hours, "hour");
  return formatter.format(Math.round(hours / 24), "day");
}

function formatDuration(milliseconds) {
  if (!Number.isFinite(milliseconds) || milliseconds < 0) return null;
  if (milliseconds < 1_000) return `${Math.round(milliseconds)} ms`;
  const seconds = milliseconds / 1_000;
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)} s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${Math.round(seconds % 60)}s`;
}

function formatCost(value) {
  if (value == null || !Number.isFinite(value) || value === 0) return "$0";
  if (value < 0.01) return `$${value.toFixed(6)}`;
  return `$${value.toFixed(4)}`;
}

function formatTokenCount(value) {
  if (value == null || !Number.isFinite(value)) return "0";
  if (value < 1_000) return String(Math.round(value));
  if (value < 1_000_000) return `${(value / 1_000).toFixed(1)}k`;
  return `${(value / 1_000_000).toFixed(1)}M`;
}

function combineUsageMetrics(usageToMetrics) {
  const map = record(usageToMetrics);
  if (!map) return null;
  const entries = Object.values(map).filter((m) => record(m));
  if (!entries.length) return null;
  let cost = 0;
  let maxBudget = null;
  let prompt = 0, completion = 0, cacheRead = 0, cacheWrite = 0, reasoning = 0;
  let contextWindow = 0, perTurn = 0;
  const models = new Map();
  for (const metrics of entries) {
    const c = Number(metrics.accumulated_cost);
    if (Number.isFinite(c)) cost += c;
    if (metrics.max_budget_per_task != null && maxBudget == null) maxBudget = Number(metrics.max_budget_per_task);
    const usage = record(metrics.accumulated_token_usage);
    if (usage) {
      prompt += Number(usage.prompt_tokens) || 0;
      completion += Number(usage.completion_tokens) || 0;
      cacheRead += Number(usage.cache_read_tokens) || 0;
      cacheWrite += Number(usage.cache_write_tokens) || 0;
      reasoning += Number(usage.reasoning_tokens) || 0;
      contextWindow = Math.max(contextWindow, Number(usage.context_window) || 0);
      perTurn = Math.max(perTurn, Number(usage.per_turn_token) || 0);
    }
    const modelName = String(metrics.model_name ?? "unknown");
    const prev = models.get(modelName) ?? { cost: 0, prompt: 0, completion: 0 };
    prev.cost += Number.isFinite(c) ? c : 0;
    prev.prompt += Number(usage?.prompt_tokens) || 0;
    prev.completion += Number(usage?.completion_tokens) || 0;
    models.set(modelName, prev);
  }
  return {
    cost, maxBudget,
    tokens: { prompt, completion, cacheRead, cacheWrite, reasoning, contextWindow, perTurn },
    models: [...models.entries()].map(([name, m]) => ({ name, ...m })).sort((a, b) => b.cost - a.cost),
  };
}

function extractConversationUsage(events) {
  let latest = null;
  for (const event of events) {
    if (event?.kind !== "ConversationStateUpdateEvent") continue;
    if (event.key === "stats") {
      latest = record(event.value);
    } else if (event.key === "full_state") {
      latest = record(record(event.value)?.stats);
    }
  }
  if (!latest) return null;
  return combineUsageMetrics(latest.usage_to_metrics);
}

function statsEventMetrics(event) {
  if (event?.kind !== "ConversationStateUpdateEvent") return null;
  const stats = event.key === "stats" ? record(event.value) : event.key === "full_state" ? record(record(event.value)?.stats) : null;
  if (!stats) return null;
  return record(stats.usage_to_metrics);
}

function usageAtEvent(events, targetEvent) {
  if (!targetEvent) return null;
  const targetTime = parseTime(targetEvent.timestamp);
  let latest = null;
  let latestTime = -Infinity;
  for (const event of events) {
    if (event?.kind !== "ConversationStateUpdateEvent") continue;
    const stats = statsEventMetrics(event);
    if (!stats) continue;
    const eventTime = parseTime(event.timestamp);
    if (eventTime <= targetTime && eventTime >= latestTime) { latest = stats; latestTime = eventTime; }
  }
  if (latest) return combineUsageMetrics(latest);
  return extractConversationUsage(events);
}

function formatUsageSection(combined) {
  if (!combined) return null;
  const lines = [
    `Cost: ${formatCost(combined.cost)}`,
    `Prompt: ${formatTokenCount(combined.tokens.prompt)}`,
    `Completion: ${formatTokenCount(combined.tokens.completion)}`,
    `Cache read: ${formatTokenCount(combined.tokens.cacheRead)}`,
    `Cache write: ${formatTokenCount(combined.tokens.cacheWrite)}`,
  ];
  if (combined.tokens.reasoning > 0) lines.push(`Reasoning: ${formatTokenCount(combined.tokens.reasoning)}`);
  if (combined.tokens.contextWindow > 0) lines.push(`Context window: ${formatTokenCount(combined.tokens.perTurn)} / ${formatTokenCount(combined.tokens.contextWindow)}`);
  if (combined.maxBudget != null) lines.push(`Budget: ${formatCost(combined.maxBudget)}`);
  for (const model of combined.models) lines.push(`  ${model.name}: ${formatCost(model.cost)} (${formatTokenCount(model.prompt + model.completion)} tokens)`);
  return lines.join("\n");
}

function kindOf(event) {
  return typeof event?.kind === "string" ? event.kind : "UnknownEvent";
}

function payloadKind(event) {
  return event?.action?.kind ?? event?.observation?.kind ?? "";
}

function categoryOf(event) {
  const kind = `${kindOf(event)} ${payloadKind(event)} ${event?.tool_name ?? ""}`.toLowerCase();
  const observation = record(event?.observation);
  if (kind.includes("error") || observation?.error || observation?.is_error === true) return "error";
  if (kind.includes("reject") || kind.includes("confirm") || kind.includes("approval")) return "approval";
  if (kind.includes("fileeditor") || kind.includes("strreplace") || kind.includes("planningfile")) return "file";
  if (kind.includes("bash") || kind.includes("terminal") || kind.includes("command")) return "command";
  if (kind.includes("message")) return "message";
  if (kind.includes("action") || kind.includes("observation") || kind.includes("tool")) return "tool";
  if (kind.includes("state") || kind.includes("pause") || kind.includes("interrupt") || kind.includes("condens") || kind.includes("stats")) return "state";
  return "other";
}

function eventTitle(event) {
  const kind = kindOf(event);
  const payload = record(event.action) ?? record(event.observation);
  if (kind === "MessageEvent") return `${event.source === "user" ? "User" : "Agent"} message`;
  if (kind === "ActionEvent") return event.summary || event.tool_name || payload?.kind || "Tool call";
  if (kind === "ObservationEvent") return `${event.tool_name || payload?.kind || "Tool"} result`;
  if (kind === "UserRejectObservation") return "Action rejected";
  if (kind === "ConversationErrorEvent") return event.code || "Conversation error";
  if (kind === "AgentErrorEvent" || kind === "ServerErrorEvent") return "Agent error";
  if (kind === "ConversationStateUpdateEvent") return event.key === "stats" ? "Usage stats" : event.key === "full_state" ? "Full state" : event.key ? `${event.key} state` : "State update";
  return kind.replace(/Event$/, "").replace(/([a-z])([A-Z])/g, "$1 $2");
}

function eventSummary(event) {
  const action = record(event.action);
  const observation = record(event.observation);
  const kind = kindOf(event);
  if (kind === "MessageEvent") return textContent(event.llm_message?.content ?? event.content ?? event.message?.content) || "Message content unavailable";
  if (event.summary) return String(event.summary);
  if (action?.path) return `${action.command ?? "edit"} ${action.path}`;
  if (action?.command) return String(action.command);
  if (action?.url) return String(action.url);
  if (event.rejection_reason) return String(event.rejection_reason);
  if (event.detail) return String(event.detail);
  if (event.error) return String(event.error);
  if (observation?.path) return `${observation.command ?? "edited"} ${observation.path}`;
  if (observation?.command) return String(observation.command);
  if (observation?.output) return String(observation.output);
  if (observation?.content) return textContent(observation.content);
  if (kindOf(event) === "ConversationStateUpdateEvent" && event.key === "stats") {
    const combined = combineUsageMetrics(record(event.value)?.usage_to_metrics);
    if (combined) return `${formatCost(combined.cost)} · ${formatTokenCount(combined.tokens.prompt + combined.tokens.completion)} tokens`;
    return "Usage data unavailable";
  }
  return `${event.source ?? "unknown"} · ${payloadKind(event) || kind}`;
}

function eventDetails(event, allEvents) {
  const sections = [];
  const action = record(event.action);
  const observation = record(event.observation);
  const message = textContent(event.llm_message?.content ?? event.content ?? event.message?.content);
  const thought = textContent(event.thought);
  if (message) sections.push(["Content", message]);
  if (thought) sections.push(["Visible thought", thought]);
  if (event.reasoning_content) sections.push(["Reasoning", String(event.reasoning_content)]);
  if (action?.command) sections.push(["Command", String(action.command)]);
  if (action?.path) sections.push(["Path", String(action.path)]);
  if (action?.old_str) sections.push(["Removed", String(action.old_str)]);
  if (action?.new_str) sections.push(["Added", String(action.new_str)]);
  if (observation?.output) sections.push(["Output", String(observation.output)]);
  const observationContent = textContent(observation?.content);
  if (observationContent && observationContent !== observation?.output) sections.push(["Result", observationContent]);
  if (observation?.error) sections.push(["Error", String(observation.error)]);
  if (event.error) sections.push(["Error", String(event.error)]);
  if (event.detail) sections.push(["Detail", String(event.detail)]);
  if (event.rejection_reason) sections.push(["Reason", String(event.rejection_reason)]);
  const combined = allEvents ? usageAtEvent(allEvents, event) : statsEventMetrics(event) ? combineUsageMetrics(statsEventMetrics(event)) : null;
  const usageText = combined ? formatUsageSection(combined) : null;
  if (usageText) sections.push(["Token usage", usageText]);
  else if (allEvents) sections.push(["Token usage", "No usage data available for this event."]);
  return sections;
}

function eventBadges(event, durations) {
  const badges = [];
  if (event.source) badges.push(String(event.source));
  if (event.tool_name) badges.push(String(event.tool_name));
  if (event.security_risk && event.security_risk !== "UNKNOWN") badges.push(`risk ${String(event.security_risk).toLowerCase()}`);
  const observation = record(event.observation);
  if (typeof observation?.exit_code === "number") badges.push(`exit ${observation.exit_code}`);
  if (observation?.timeout) badges.push("timeout");
  const usageToMetrics = statsEventMetrics(event);
  if (usageToMetrics) {
    const combined = combineUsageMetrics(usageToMetrics);
    if (combined) badges.push(formatCost(combined.cost));
  }
  const duration = durations.get(event.id);
  if (duration !== undefined) badges.push(formatDuration(duration));
  return badges.filter(Boolean);
}

function buildDurations(events) {
  const actions = new Map();
  const durations = new Map();
  for (const event of events) {
    if (kindOf(event) === "ActionEvent" && event.tool_call_id) actions.set(event.tool_call_id, event);
    if (["ObservationEvent", "UserRejectObservation", "AgentErrorEvent"].includes(kindOf(event)) && event.tool_call_id) {
      const action = actions.get(event.tool_call_id);
      if (action) durations.set(action.id, Math.max(0, parseTime(event.timestamp) - parseTime(action.timestamp)));
    }
  }
  return durations;
}

function normalizePage(response, label) {
  const page = record(response);
  if (!page || !Array.isArray(page.items)) throw new Error(`${label} returned an unexpected response.`);
  return { items: page.items.filter((item) => record(item)), nextPageId: typeof page.next_page_id === "string" ? page.next_page_id : null };
}

async function fetchAll(host, path, disposed, onProgress) {
  const items = [];
  let pageId = null;
  do {
    const params = new URLSearchParams({ limit: "100" });
    if (pageId) params.set("page_id", pageId);
    const response = await host.agentServer.request({ path: `${path}?${params}` });
    if (disposed()) return items;
    const page = normalizePage(response, path.includes("events") ? "Event search" : "Conversation search");
    items.push(...page.items);
    pageId = page.nextPageId;
    onProgress?.(items.length);
  } while (pageId && items.length < MAX_EVENTS);
  return items;
}

function sortEvents(events) {
  return [...events].sort((a, b) => parseTime(a.timestamp) - parseTime(b.timestamp) || String(a.id ?? "").localeCompare(String(b.id ?? "")));
}

function dedupeEvents(events) {
  const seen = new Set();
  return events.filter((event, index) => {
    const key = event.id ?? `${event.timestamp}-${event.kind}-${index}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function metric(label, value) {
  const node = element("div", "conversation-trace__metric");
  node.append(element("span", "conversation-trace__metric-label", label), element("strong", "conversation-trace__metric-value", value));
  return node;
}

function detailSection(title, content, code = false) {
  const section = element("section", "conversation-trace__detail");
  section.append(element("h4", "", title), element(code ? "pre" : "p", "", content));
  return section;
}

function renderRail(events) {
  const rail = element("div", "conversation-trace__rail");
  rail.setAttribute("role", "img");
  rail.setAttribute("aria-label", `Chronology overview with ${events.length} events`);
  const bucketCount = Math.min(120, Math.max(1, events.length));
  const bucketSize = Math.max(1, Math.ceil(events.length / bucketCount));
  for (let index = 0; index < events.length; index += bucketSize) {
    const bucket = events.slice(index, index + bucketSize);
    const counts = new Map();
    for (const event of bucket) counts.set(categoryOf(event), (counts.get(categoryOf(event)) ?? 0) + 1);
    const dominant = [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? "other";
    const segment = element("span", "conversation-trace__rail-segment");
    segment.style.setProperty("--color", CATEGORY[dominant].color);
    segment.style.setProperty("--height", `${35 + Math.min(65, bucket.length * 13)}%`);
    segment.title = `${CATEGORY[dominant].label}: ${bucket.length} event${bucket.length === 1 ? "" : "s"}`;
    rail.append(segment);
  }
  return rail;
}

function renderUsage(usage) {
  const panel = element("section", "conversation-trace__usage");
  panel.setAttribute("aria-label", "Token usage and cost");
  const { cost, maxBudget, tokens, models } = usage;

  const costCard = element("div", "conversation-trace__usage-card conversation-trace__usage-card--cost");
  costCard.append(element("span", "conversation-trace__usage-label", "Total cost"), element("strong", "conversation-trace__usage-value conversation-trace__usage-value--accent", formatCost(cost)));
  if (maxBudget != null && maxBudget > 0) {
    const pct = Math.min(100, (cost / maxBudget) * 100);
    costCard.append(element("span", "conversation-trace__usage-sub", `${formatCost(maxBudget)} budget · ${pct.toFixed(1)}% used`));
  }
  panel.append(costCard);

  panel.append(usageCard("Prompt", formatTokenCount(tokens.prompt)));
  panel.append(usageCard("Completion", formatTokenCount(tokens.completion)));
  panel.append(usageCard("Cache read", formatTokenCount(tokens.cacheRead)));
  panel.append(usageCard("Cache write", formatTokenCount(tokens.cacheWrite)));
  if (tokens.reasoning > 0) panel.append(usageCard("Reasoning", formatTokenCount(tokens.reasoning)));

  if (tokens.contextWindow > 0) {
    const ctxCard = element("div", "conversation-trace__usage-card");
    const pct = Math.min(100, (tokens.perTurn / tokens.contextWindow) * 100);
    const cls = pct > 90 ? "conversation-trace__context-fill--danger" : pct > 70 ? "conversation-trace__context-fill--warn" : "";
    const fill = element("div", `conversation-trace__context-fill${cls ? ` ${cls}` : ""}`);
    fill.style.width = `${pct}%`;
    const bar = element("div", "conversation-trace__context-bar");
    bar.append(fill);
    ctxCard.append(element("span", "conversation-trace__usage-label", "Context window"), element("span", "conversation-trace__usage-value", `${formatTokenCount(tokens.perTurn)} / ${formatTokenCount(tokens.contextWindow)}`), bar);
    panel.append(ctxCard);
  }

  if (models.length > 1) {
    for (const model of models) {
      const row = element("div", "conversation-trace__model-row");
      row.append(element("span", "conversation-trace__model-name", model.name), element("span", "conversation-trace__model-cost", formatCost(model.cost)), element("span", "conversation-trace__model-tokens", `${formatTokenCount(model.prompt + model.completion)} tokens`));
      panel.append(row);
    }
  }

  return panel;
}

function usageCard(label, value) {
  const card = element("div", "conversation-trace__usage-card");
  card.append(element("span", "conversation-trace__usage-label", label), element("span", "conversation-trace__usage-value", value));
  return card;
}

function renderInspector(container, event, durations, allEvents) {
  container.replaceChildren();
  if (!event) {
    const empty = element("div", "conversation-trace__notice", "Select an event to inspect its full payload and correlated timing.");
    empty.style.margin = ".8rem";
    container.append(empty);
    return;
  }
  const header = element("header", "conversation-trace__inspector-header");
  header.append(element("h3", "", eventTitle(event)), element("p", "", `${kindOf(event)} · ${event.id ?? "no id"}`));
  container.append(header);
  container.append(detailSection("Timestamp", `${formatTime(event.timestamp, { dateStyle: "medium", timeStyle: "medium" })}\n${event.timestamp ?? "Unknown"}`));
  const duration = durations.get(event.id);
  if (duration !== undefined) container.append(detailSection("Tool duration", formatDuration(duration)));
  for (const [title, content] of eventDetails(event, allEvents)) container.append(detailSection(title, content, ["Command", "Output", "Removed", "Added", "Result", "Token usage"].includes(title)));
  container.append(detailSection("Raw event", stringify(event), true));
}

function renderSidebar(state, nodes, navigate) {
  const query = state.conversationQuery.trim().toLowerCase();
  const conversations = state.conversations.filter((conversation) => {
    if (state.statusFilter !== "all" && conversation.execution_status !== state.statusFilter) return false;
    return !query || `${conversation.title ?? ""} ${conversation.id ?? ""}`.toLowerCase().includes(query);
  });
  nodes.list.replaceChildren();
  if (state.conversationsLoading) {
    nodes.list.append(element("div", "conversation-trace__notice", "Loading conversations…"));
    return;
  }
  if (state.conversationError) {
    nodes.list.append(element("div", "conversation-trace__notice conversation-trace__notice--error", state.conversationError));
    return;
  }
  if (!conversations.length) {
    nodes.list.append(element("div", "conversation-trace__notice", "No conversations match this view."));
    return;
  }
  for (const conversation of conversations) {
    const button = element("button", "conversation-trace__conversation");
    button.type = "button";
    button.setAttribute("aria-current", String(conversation.id) === state.selectedId ? "true" : "false");
    const dot = element("span", `conversation-trace__status-dot conversation-trace__status-dot--${conversation.execution_status ?? "unknown"}`);
    const copy = element("span");
    copy.append(element("span", "conversation-trace__conversation-title", conversation.title || "Untitled conversation"));
    const meta = element("span", "conversation-trace__conversation-meta");
    meta.append(element("span", "", conversation.execution_status ?? "unknown"), element("span", "", relativeTime(conversation.updated_at)));
    copy.append(meta);
    button.append(dot, copy);
    button.addEventListener("click", () => navigate(`${ROOT_PATH}/conversations/${encodeURIComponent(conversation.id)}`));
    nodes.list.append(button);
  }
}

function renderMain(state, nodes) {
  nodes.main.replaceChildren();
  const conversation = state.conversations.find((item) => String(item.id) === state.selectedId);
  if (!state.selectedId) {
    const empty = element("section", "conversation-trace__empty-page");
    const inner = element("div");
    inner.append(element("div", "conversation-trace__empty-mark", "↳"), element("h2", "", "Choose a conversation"), element("p", "", "Select any run from the ledger to reconstruct its complete chronology—messages, tool calls, file mutations, commands, approvals, failures, and state changes."));
    empty.append(inner);
    nodes.main.append(empty);
    return;
  }
  const header = element("header", "conversation-trace__header");
  const heading = element("div");
  heading.append(element("p", "conversation-trace__eyebrow", "Chronological event ledger"), element("h2", "", conversation?.title || "Untitled conversation"));
  const meta = element("div", "conversation-trace__header-meta");
  meta.append(element("span", "", conversation?.execution_status ?? "unknown"), element("span", "", state.selectedId), element("span", "", conversation?.current_model_name ?? conversation?.current_model_id ?? conversation?.agent?.llm?.model ?? "model unknown"));
  heading.append(meta);
  const actions = element("div", "conversation-trace__actions");
  const refresh = element("button", "conversation-trace__button", state.eventsLoading ? "Loading…" : "Refresh trace");
  refresh.type = "button"; refresh.disabled = state.eventsLoading; refresh.addEventListener("click", state.refreshEvents);
  actions.append(refresh);
  header.append(heading, actions);
  nodes.main.append(header);
  if (state.eventsLoading && !state.events.length) { nodes.main.append(element("div", "conversation-trace__notice", `Loading event ledger${state.loadedCount ? ` · ${state.loadedCount} found` : ""}…`)); return; }
  if (state.eventError) { nodes.main.append(element("div", "conversation-trace__notice conversation-trace__notice--error", state.eventError)); return; }
  const durations = buildDurations(state.events);
  const categories = new Map();
  for (const event of state.events) categories.set(categoryOf(event), (categories.get(categoryOf(event)) ?? 0) + 1);
  const started = state.events[0]?.timestamp ?? conversation?.created_at;
  const ended = state.events.at(-1)?.timestamp ?? conversation?.updated_at;
  const elapsed = started && ended ? formatDuration(parseTime(ended) - parseTime(started)) : null;
  const overview = element("section", "conversation-trace__overview");
  overview.setAttribute("aria-label", "Trace overview");
  overview.append(metric("Events", String(state.events.length)), metric("Tool calls", String(state.events.filter((event) => kindOf(event) === "ActionEvent").length)), metric("File events", String(categories.get("file") ?? 0)), metric("Errors", String(categories.get("error") ?? 0)), metric("Elapsed", elapsed ?? "Unknown"));
  nodes.main.append(overview, renderRail(state.events));
  const usage = extractConversationUsage(state.events);
  if (usage) nodes.main.append(renderUsage(usage));
  const toolbar = element("div", "conversation-trace__toolbar");
  const search = element("input", "conversation-trace__input");
  search.type = "search"; search.placeholder = "Search event content, paths, commands, IDs…"; search.setAttribute("aria-label", "Search trace"); search.value = state.eventQuery;
  search.addEventListener("input", () => { state.eventQuery = search.value; renderMain(state, nodes); });
  const filters = element("div", "conversation-trace__filters");
  filters.setAttribute("aria-label", "Event categories");
  for (const [key, definition] of Object.entries(CATEGORY)) {
    if (!categories.has(key) && key !== "other") continue;
    const button = element("button", "conversation-trace__filter", `${definition.label} ${categories.get(key) ?? 0}`);
    button.type = "button"; button.style.setProperty("--filter-color", definition.color); button.setAttribute("aria-pressed", String(state.categoryFilter === key));
    button.addEventListener("click", () => { state.categoryFilter = state.categoryFilter === key ? "all" : key; renderMain(state, nodes); });
    filters.append(button);
  }
  toolbar.append(search, filters);
  nodes.main.append(toolbar);
  const query = state.eventQuery.trim().toLowerCase();
  const visible = state.events.filter((event) => (state.categoryFilter === "all" || categoryOf(event) === state.categoryFilter) && (!query || stringify(event).toLowerCase().includes(query)));
  if (!visible.length) { nodes.main.append(element("div", "conversation-trace__notice", state.events.length ? "No events match these filters." : "This conversation has no persisted events.")); return; }
  const body = element("div", "conversation-trace__body");
  const timeline = element("section", "conversation-trace__timeline"); timeline.setAttribute("aria-label", "Conversation event timeline");
  const inspector = element("aside", "conversation-trace__inspector"); inspector.setAttribute("aria-label", "Selected event details");
  const selected = visible.find((event) => event.id === state.selectedEventId) ?? visible[0];
  state.selectedEventId = selected?.id ?? null;
  for (const event of visible) {
    const category = categoryOf(event); const definition = CATEGORY[category];
    const button = element("button", "conversation-trace__event"); button.type = "button"; button.style.setProperty("--event-color", definition.color); button.setAttribute("aria-selected", String(event.id === state.selectedEventId));
    const node = element("span", "conversation-trace__node", definition.mark);
    const content = element("span"); const top = element("span", "conversation-trace__event-top"); const name = element("span", "conversation-trace__event-name");
    name.append(element("span", "conversation-trace__event-category", definition.label), document.createTextNode(eventTitle(event)));
    top.append(name, element("time", "conversation-trace__event-time", formatTime(event.timestamp, { hour: "2-digit", minute: "2-digit", second: "2-digit" })));
    content.append(top, element("span", "conversation-trace__event-summary", eventSummary(event).replace(/\s+/g, " ")));
    const badges = element("span", "conversation-trace__event-badges");
    for (const badgeText of eventBadges(event, durations)) {
      const badge = element("span", `conversation-trace__badge${category === "error" ? " conversation-trace__badge--error" : ""}`, badgeText); badges.append(badge);
    }
    content.append(badges); button.append(node, content);
    button.addEventListener("click", () => { state.selectedEventId = event.id; renderMain(state, nodes); });
    timeline.append(button);
  }
  if (state.events.length >= MAX_EVENTS) timeline.append(element("div", "conversation-trace__truncate", `Trace limited to ${MAX_EVENTS.toLocaleString()} events for browser performance.`));
  renderInspector(inspector, selected, durations, state.events);
  body.append(timeline, inspector); nodes.main.append(body);
}

function selectedConversationId(path) {
  const match = /^conversations\/([^/]+)$/.exec(path.replace(/^\/+|\/+$/g, ""));
  if (!match) return null;
  try { return decodeURIComponent(match[1]); } catch { return match[1]; }
}

function mountTrace(host, { container, path, navigate }) {
  let disposed = false;
  let pollTimer = null;
  const style = element("style"); style.textContent = STYLE;
  const root = element("section", "conversation-trace"); root.setAttribute("aria-label", "Conversation Trace");
  const layout = element("div", "conversation-trace__layout"); const sidebar = element("aside", "conversation-trace__sidebar"); const main = element("main", "conversation-trace__main");
  const brand = element("header", "conversation-trace__brand"); brand.append(element("p", "conversation-trace__eyebrow", "OpenHands forensic view"), element("h1", "", "Conversation Trace"), element("p", "", "A complete, inspectable ledger of agent activity."));
  const sidebarTools = element("div", "conversation-trace__sidebar-tools"); const conversationSearch = element("input", "conversation-trace__input"); conversationSearch.type = "search"; conversationSearch.placeholder = "Find a conversation…"; conversationSearch.setAttribute("aria-label", "Search conversations");
  const statusSelect = element("select", "conversation-trace__select"); statusSelect.setAttribute("aria-label", "Filter by conversation status");
  for (const value of ["all", "running", "idle", "finished", "error", "stuck", "stopped"]) { const option = element("option", "", value === "all" ? "All statuses" : value); option.value = value; statusSelect.append(option); }
  sidebarTools.append(conversationSearch, statusSelect); const list = element("nav", "conversation-trace__list"); list.setAttribute("aria-label", "Conversations"); sidebar.append(brand, sidebarTools, list); layout.append(sidebar, main); root.append(layout); container.append(style, root);
  const nodes = { list, main };
  const state = {
    conversations: [], events: [], selectedId: selectedConversationId(path), selectedEventId: null,
    conversationQuery: "", statusFilter: "all", eventQuery: "", categoryFilter: "all", loadedCount: 0,
    conversationsLoading: true, eventsLoading: false, conversationError: null, eventError: null, refreshEvents: () => {},
  };
  const isDisposed = () => disposed;
  const paint = () => { if (!disposed) { renderSidebar(state, nodes, navigate); renderMain(state, nodes); } };
  async function loadConversations() {
    state.conversationsLoading = true; state.conversationError = null; paint();
    try {
      const conversations = await fetchAll(host, "/api/conversations/search", isDisposed);
      if (disposed) return;
      state.conversations = conversations.sort((a, b) => parseTime(b.updated_at) - parseTime(a.updated_at));
      state.conversationsLoading = false; paint();
      if (state.selectedId) await loadEvents();
    } catch (error) {
      if (disposed) return;
      state.conversationsLoading = false; state.conversationError = error instanceof Error ? error.message : "Unable to load conversations."; paint();
    }
  }
  async function loadEvents(silent = false) {
    if (!state.selectedId || state.eventsLoading) return;
    state.eventsLoading = true; state.eventError = null; state.loadedCount = 0; if (!silent) paint();
    try {
      const events = await fetchAll(host, `/api/conversations/${encodeURIComponent(state.selectedId)}/events/search`, isDisposed, (count) => { state.loadedCount = count; if (!silent) paint(); });
      if (disposed) return;
      state.events = dedupeEvents(sortEvents(events)); state.eventsLoading = false; paint();
    } catch (error) {
      if (disposed) return;
      state.eventsLoading = false; state.eventError = error instanceof Error ? error.message : "Unable to load conversation events."; paint();
    }
  }
  state.refreshEvents = () => loadEvents(false);
  conversationSearch.addEventListener("input", () => { state.conversationQuery = conversationSearch.value; renderSidebar(state, nodes, navigate); });
  statusSelect.addEventListener("change", () => { state.statusFilter = statusSelect.value; renderSidebar(state, nodes, navigate); });
  loadConversations();
  pollTimer = window.setInterval(() => {
    const selected = state.conversations.find((item) => String(item.id) === state.selectedId);
    if (selected && ["running", "idle"].includes(selected.execution_status) && !state.eventsLoading) loadEvents(true);
  }, POLL_INTERVAL_MS);
  return () => { disposed = true; if (pollTimer !== null) window.clearInterval(pollTimer); style.remove(); root.remove(); };
}

export function activate(host) {
  if (host.apiVersion !== "1") throw new Error("Conversation Trace requires Canvas host API 1.");
  return host.registerPage("trace", (context) => mountTrace(host, context));
}
