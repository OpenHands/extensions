const BUDGET = 6000;
const MEMORY_DIR = ".openhands/memory";
const INDEX_FILE = "MEMORY.md";
const PROJECT_RELPATH = `${MEMORY_DIR}/${INDEX_FILE}`;
const DAILY_FILE_RE = /^\d{4}-\d{2}-\d{2}\.md$/;
const USER_HEADER = "# User memory (~/.openhands/memory/MEMORY.md)";
const PROJECT_HEADER = "# Project memory (.openhands/memory/MEMORY.md)";
const TRUNCATION_NOTICE = "[earlier memory truncated]";
const STYLE = [
  ".agent-memory{--bg:var(--oh-background,#101113);--panel:var(--oh-surface,#191b1f);--text:var(--oh-foreground,#f1f1ed);--muted:var(--oh-text-secondary,#a5a7ab);--border:var(--oh-border-subtle,#36393f);--accent:var(--oh-accent,#b7ef5c);--danger:#fb7185;min-height:100%;color:var(--text);background:var(--bg);font-family:-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif}",
  ".agent-memory *{box-sizing:border-box}.agent-memory__wrap{max-width:1050px;margin:auto;padding:clamp(1.25rem,3vw,3rem)}",
  ".agent-memory h1{margin:0;font-size:clamp(1.7rem,3vw,2.5rem);letter-spacing:-.04em}.agent-memory h2{margin:0;font-size:1.2rem}.agent-memory p{line-height:1.55}",
  ".agent-memory__lede,.agent-memory__meta{color:var(--muted)}.agent-memory__header{display:flex;justify-content:space-between;gap:1rem;align-items:start}",
  ".agent-memory__button{border:1px solid var(--border);border-radius:.4rem;padding:.55rem .8rem;background:var(--panel);color:var(--text);font:inherit;font-size:.82rem;font-weight:650;cursor:pointer}",
  ".agent-memory__button:hover{border-color:var(--accent)}.agent-memory__button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}",
  ".agent-memory__summary{display:grid;grid-template-columns:minmax(12rem,1fr) 2fr;gap:1rem;margin:1.5rem 0}",
  ".agent-memory__card,.agent-memory__entry,.agent-memory__state{border:1px solid var(--border);border-radius:.65rem;background:var(--panel)}.agent-memory__card{padding:1rem}",
  ".agent-memory__label{color:var(--muted);font-size:.69rem;font-weight:750;letter-spacing:.1em;text-transform:uppercase}.agent-memory__number{display:block;margin-top:.35rem;font-size:1.5rem;font-variant-numeric:tabular-nums}",
  ".agent-memory__entries{display:grid;gap:.8rem}.agent-memory__entry{overflow:hidden}.agent-memory__entry--error{border-color:var(--danger)}.agent-memory__entry-header{display:flex;justify-content:space-between;gap:1rem;padding:.85rem 1rem;border-bottom:1px solid var(--border);align-items:start}",
  ".agent-memory__provenance{display:flex;align-items:center;gap:.45rem;min-width:0;font-size:.8rem;font-weight:700}.agent-memory__tier{padding:.15rem .38rem;border:1px solid var(--border);border-radius:999px;color:var(--accent);font-size:.64rem;text-transform:uppercase;letter-spacing:.07em}.agent-memory__tier--project{color:#5eead4}",
  ".agent-memory__path{overflow-wrap:anywhere;color:var(--muted);font:.72rem ui-monospace,SFMono-Regular,Menlo,monospace}.agent-memory__time{flex:none;color:var(--muted);font-size:.73rem}.agent-memory__time::after{display:inline-block;margin-left:.35rem;content:'\\25B8';transition:transform .15s}.agent-memory__entry[open] .agent-memory__time::after{transform:rotate(90deg)}.agent-memory__injected{max-width:26rem;margin:0 0 .4rem;color:var(--muted);font-size:.72rem;line-height:1.5}",
  ".agent-memory__entry summary{list-style:none}.agent-memory__entry summary::-webkit-details-marker{display:none}.agent-memory__entry-header{cursor:pointer}.agent-memory__entry-header:focus-visible{outline:2px solid var(--accent);outline-offset:2px}",
  ".agent-memory__badge{margin-left:.45rem;padding:.12rem .35rem;border:1px solid var(--border);border-radius:999px;color:var(--muted);font:.6rem ui-monospace,SFMono-Regular,Menlo,monospace}",
  ".agent-memory pre{max-height:34rem;margin:0;padding:1rem;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;color:var(--text);font:.79rem/1.55 ui-monospace,SFMono-Regular,Menlo,monospace}",
  ".agent-memory__state{padding:2.5rem 1rem;text-align:center}.agent-memory__state p{max-width:38rem;margin:.65rem auto 0;color:var(--muted)}.agent-memory__state--error{border-color:var(--danger)}.agent-memory__state--error h2{color:var(--danger)}",
  "@media(max-width:650px){.agent-memory__header{display:block}.agent-memory__button{margin-top:1rem}.agent-memory__summary{grid-template-columns:1fr}.agent-memory__entry-header{display:block}.agent-memory__time{display:block;margin-top:.45rem}}",
  "@media(prefers-reduced-motion:reduce){.agent-memory *{transition:none!important;animation:none!important}}",
].join("");

function element(tag, className, text) { const node = document.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = text; return node; }
function record(value) { return value && typeof value === "object" && !Array.isArray(value) ? value : null; }
function text(response) { if (typeof response === "string") return response; const value = record(response); return typeof value?.content === "string" ? value.content : typeof value?.text === "string" ? value.text : ""; }
function isNotFound(error) { return /(?:404|not found|no such file)/i.test(error instanceof Error ? error.message : String(error)); }
function modified(response) { const value = record(response); return value?.modified_at || value?.last_modified || null; }
function formatTime(value) { const date = new Date(value); return Number.isFinite(date.getTime()) ? date.toLocaleString() : "Modification time unavailable"; }
function encodeJson(value) { return btoa(unescape(encodeURIComponent(JSON.stringify(value)))); }
function metadataCommand(paths) {
  const encoded = encodeJson(paths);
  return `python3 -c "import base64,json,os; paths=json.loads(base64.b64decode('${encoded}')); print(json.dumps({p: os.path.getmtime(p) if os.path.isfile(p) else None for p in paths}))"`;
}
function dailyFilesCommand(directories) {
  const encoded = encodeJson(directories);
  return `python3 -c "import base64,json,os,re; dirs=json.loads(base64.b64decode('${encoded}')); pattern=re.compile(r'^\\d{4}-\\d{2}-\\d{2}\\.md$'); exec('def files(directory):\\n try:\\n  return sorted([name for name in os.listdir(directory) if pattern.match(name)], reverse=True) if os.path.isdir(directory) else []\\n except OSError:\\n  return []'); print(json.dumps({directory: files(directory) for directory in dirs}))"`;
}
function commandOutput(response) { const value = record(response); return typeof value?.stdout === "string" ? value.stdout.trim() : ""; }
function truncateTop(body, budget) {
  if (body.length <= budget) return body;
  const lines = body.split("\n");
  while (lines.length) {
    lines.shift();
    const candidate = [TRUNCATION_NOTICE, ...lines].join("\n");
    if (candidate.length <= budget) return candidate;
  }
  return TRUNCATION_NOTICE;
}
function injectedContext(userBody, projectBody) {
  const tiers = [];
  if (userBody) tiers.push({ header: USER_HEADER, body: userBody });
  if (projectBody) tiers.push({ header: PROJECT_HEADER, body: projectBody });
  if (!tiers.length) return "";
  const combined = tiers.map((tier) => `${tier.header}\n${tier.body}`).join("\n\n");
  if (combined.length <= BUDGET) return combined;
  let overhead = 0;
  for (const tier of tiers) overhead += tier.header.length + 1;
  overhead += 2 * (tiers.length - 1);
  const bodyBudget = BUDGET - overhead;
  const fair = Math.floor(bodyBudget / tiers.length);
  const budgets = tiers.map((tier) => Math.min(tier.body.length, fair));
  let leftover = bodyBudget - budgets.reduce((sum, value) => sum + value, 0);
  for (let i = 0; i < tiers.length; i++) {
    const extra = Math.min(leftover, tiers[i].body.length - budgets[i]);
    budgets[i] += extra;
    leftover -= extra;
  }
  return tiers.map((tier, i) => `${tier.header}\n${truncateTop(tier.body, budgets[i])}`).join("\n\n");
}
function baseName(path) { const parts = path.split("/"); return parts[parts.length - 1]; }
async function listWorkspacePaths(request) {
  const paths = new Set();
  const collect = (value) => { if (typeof value === "string" && value.startsWith("/")) paths.add(value); };
  try {
    const response = record(await request({ path: "/api/workspaces" }));
    for (const item of response?.workspaces ?? []) collect(record(item)?.path);
  } catch { /* Registered workspaces are optional; fall through to conversations. */ }
  try {
    const response = record(await request({ path: "/api/conversations/search?limit=100" }));
    for (const conversation of response?.items ?? []) collect(record(conversation)?.workspace?.working_dir);
  } catch { /* Conversation workspaces are optional. */ }
  return [...paths].sort();
}

async function listDailyFiles(request, directories) {
  if (!directories.length) return {};
  try {
    const result = await request({ path: "/api/bash/execute_bash_command", method: "POST", body: { command: dailyFilesCommand(directories) } });
    const filesByDirectory = record(JSON.parse(commandOutput(result))) || {};
    const output = {};
    for (const directory of directories) {
      const files = Array.isArray(filesByDirectory[directory]) ? filesByDirectory[directory] : [];
      output[directory] = files.filter((file) => typeof file === "string" && DAILY_FILE_RE.test(file));
    }
    return output;
  } catch {
    return Object.fromEntries(directories.map((directory) => [directory, []]));
  }
}

async function readMemory(request) {
  const [settings, home, workspaces] = await Promise.all([request({ path: "/api/settings" }), request({ path: "/api/file/home" }), listWorkspacePaths(request)]);
  if (settings?.agent_settings?.agent_context?.load_memory !== true) return { enabled: false, entries: [] };
  const directory = record(home)?.home_directory || record(home)?.home || record(home)?.path;
  if (typeof directory !== "string" || !directory.startsWith("/")) throw new Error("The Agent Server did not provide its home directory.");
  const roots = [
    { tier: "user", label: "User", dir: `${directory}/${MEMORY_DIR}` },
    ...workspaces.map((path) => ({ tier: "project", label: baseName(path), workspace: path, dir: `${path}/${MEMORY_DIR}` })),
  ];
  const dailyFiles = await listDailyFiles(request, roots.map((root) => root.dir));
  const sources = roots.flatMap((root) => [
    { ...root, kind: "index", path: `${root.dir}/${INDEX_FILE}` },
    ...(dailyFiles[root.dir] || []).map((file) => ({ ...root, kind: "daily", date: file.slice(0, -3), path: `${root.dir}/${file}` })),
  ]);
  const results = await Promise.all(sources.map(async (source) => {
    try {
      const response = await request({ path: `/api/file/download?path=${encodeURIComponent(source.path)}&_=${Date.now()}`, headers: { "Cache-Control": "no-cache" } });
      const content = text(response);
      return content ? { entry: { ...source, content, modifiedAt: modified(response) } } : {};
    } catch (error) {
      if (isNotFound(error)) return {};
      return { error: { source, message: error instanceof Error ? error.message : "Unexpected error." } };
    }
  }));
  const existing = results.flatMap((result) => result.entry ? [result.entry] : []);
  const errors = results.flatMap((result) => result.error ? [result.error] : []);
  try {
    const result = await request({ path: "/api/bash/execute_bash_command", method: "POST", body: { command: metadataCommand(existing.map((entry) => entry.path)) } });
    const times = JSON.parse(commandOutput(result));
    for (const entry of existing) entry.modifiedAt ||= typeof times[entry.path] === "number" ? new Date(times[entry.path] * 1000).toISOString() : null;
  } catch { /* The viewer remains usable when the optional metadata probe is unavailable. */ }
  return { enabled: true, entries: existing, errors };
}
function stateBox(title, message, error = false) { const box = element("section", `agent-memory__state${error ? " agent-memory__state--error" : ""}`); box.append(element("h2", "", title), element("p", "", message)); return box; }
function entrySummary(entry, userIndex) {
  if (entry.kind === "daily") return entry.tier === "project" ? `Workspace: ${entry.workspace}. Daily note ${entry.date}; read on demand and not injected automatically.` : `Daily note ${entry.date}; read on demand and not injected automatically.`;
  return entry.tier === "project" ? `Workspace: ${entry.workspace}` : "Applies to every conversation.";
}
function appendBadges(provenance, entry, userIndex) {
  if (entry.kind === "daily") return void provenance.append(element("code", "agent-memory__badge", "daily note"));
  if (entry.tier === "project") provenance.append(element("code", "agent-memory__badge", `≈ simulated injected size ${injectedContext(userIndex, entry.content).length.toLocaleString()} chars`));
}
function sourceError(error) {
  const details = element("details", "agent-memory__entry agent-memory__entry--error");
  const summary = element("summary", "agent-memory__entry-header");
  summary.append(element("div", "agent-memory__provenance", `Could not read ${error.source.path}`), element("span", "agent-memory__time", "Read error"));
  details.append(summary, element("p", "agent-memory__injected", error.message));
  return details;
}
function render(root, state, refresh) {
  root.replaceChildren(); const wrap = element("section", "agent-memory__wrap"); root.append(wrap);
  const header = element("div", "agent-memory__header"); const intro = element("div"); intro.append(element("h1", "", "Agent Memory"), element("p", "agent-memory__lede", "Read-only view of memory indexes and daily notes available to Agent Canvas.")); const button = element("button", "agent-memory__button", "Refresh"); button.type = "button"; button.addEventListener("click", refresh); header.append(intro, button); wrap.append(header);
  if (state.kind === "loading") return void wrap.append(stateBox("Loading memory", "Checking the memory setting and registered workspaces."));
  if (state.kind === "error") return void wrap.append(stateBox("Memory could not be read", state.message, true));
  if (!state.enabled) return void wrap.append(stateBox("Memory is disabled", "Enable Agent Memory in Settings to load user and project memory into new conversations. This viewer cannot change the setting or write memory."));
  if (!state.entries.length && !(state.errors || []).length) return void wrap.append(stateBox("No memory entries yet", "Memory is enabled, but no non-empty MEMORY.md index or YYYY-MM-DD.md daily note was found in the user tier or any registered workspace."));
  const userIndex = state.entries.find((entry) => entry.tier === "user" && entry.kind === "index")?.content || "";
  const sources = element("div", "agent-memory__card"); sources.append(element("div", "agent-memory__label", "Loaded sources"), element("strong", "agent-memory__number", String(state.entries.length)), element("div", "agent-memory__meta", "Discovered automatically from memory directories, registered workspaces, and conversations.")); wrap.append(sources);
  const entries = element("div", "agent-memory__entries");
  for (const entry of state.entries) {
    const details = element("details", "agent-memory__entry");
    const summary = element("summary", "agent-memory__entry-header");
    const provenance = element("div", "agent-memory__provenance");
    provenance.append(element("span", `agent-memory__tier${entry.tier === "project" ? " agent-memory__tier--project" : ""}`, entry.tier), element("span", "agent-memory__path", entry.path));
    appendBadges(provenance, entry, userIndex);
    summary.append(provenance, element("time", "agent-memory__time", entry.modifiedAt ? `Modified ${formatTime(entry.modifiedAt)}` : "Modification time unavailable"));
    details.append(summary, element("p", "agent-memory__injected", entrySummary(entry, userIndex)), element("pre", "", entry.content));
    entries.append(details);
  }
  for (const error of state.errors || []) entries.append(sourceError(error));
  wrap.append(entries);
}
export function activate(host) {
  if (host.apiVersion !== "1") throw new Error("Agent Memory requires Canvas host API 1.");
  return host.registerPage("memory", ({ container, path, navigate }) => {
    const style = element("style", "", STYLE); const root = element("div", "agent-memory"); container.append(style, root); let disposed = false;
    const refresh = async () => { render(root, { kind: "loading" }, refresh); try { const result = await readMemory(host.agentServer.request); if (!disposed) render(root, { kind: "ready", ...result }, refresh); } catch (error) { if (!disposed) render(root, { kind: "error", message: error instanceof Error ? error.message : "Unexpected error." }, refresh); } };
    if (path && path !== "/") navigate("/extensions/agent-memory-viewer/memory"); else refresh();
    return () => { disposed = true; root.remove(); style.remove(); };
  });
}