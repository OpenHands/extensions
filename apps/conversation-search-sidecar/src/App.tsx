import { useCallback, useEffect, useMemo, useState } from "react";
import {
  IDLE_SHUTDOWN_SECONDS,
  SIDECAR_VERSION,
  SOURCE_SHA256,
  agentSetupText,
  dataDirectory,
  deleteAppData,
  discoverHome,
  inspectResult,
  installOrRepair,
  loadStatus,
  probePrerequisites,
  repairRuntime,
  search,
  startService,
  stopService,
  updateIndex,
} from "./native-service";
import type { CanvasHost, DataLocation, IndexStatus, ProbeStatus, SearchFilters, SearchHit, SearchResponse } from "./types";

export const SEARCH_ROUTE = "/extensions/conversation-search-sidecar/search";
export const OPERATIONS_ROUTE = `${SEARCH_ROUTE}/operations`;
type View = "search" | "operations" | "not-found";

export function normalizeRoute(path: string): View {
  const segment = path.replace(/^\/+|\/+$/g, "").split("/").filter(Boolean)[0] ?? "";
  if (segment === "" || segment === "search") return "search";
  if (segment === "operations") return "operations";
  return "not-found";
}

function message(error: unknown): string { return error instanceof Error ? error.message : String(error); }
function isAbort(error: unknown): boolean { return error instanceof DOMException && error.name === "AbortError"; }
function formatBytes(value: number): string {
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toFixed(index ? 1 : 0)} ${units[index]}`;
}
function plainExcerpt(value: string): string { return value.replace(/<[^>]*>/g, "").replace(/\s+/g, " ").trim(); }

export function conversationPath(conversationId: string, backendId?: string | null): string {
  const path = `/conversations/${encodeURIComponent(conversationId)}`;
  return backendId ? `${path}?backend=${encodeURIComponent(backendId)}` : path;
}

function ConversationLink({ host, conversationId, navigate, children }: { host: CanvasHost; conversationId: string; navigate: (path: string) => void; children: React.ReactNode }) {
  const path = conversationPath(conversationId, host.backend.id);
  const open = (event: React.MouseEvent<HTMLAnchorElement>) => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(path);
  };
  return <a className="css-conversation-link" href={path} onClick={open}>{children}</a>;
}

function Header({ view, ready, running, navigate }: { view: View; ready: boolean; running: boolean; navigate: (path: string) => void }) {
  return <header className="css-header">
    <button type="button" className="css-brand" onClick={() => navigate(SEARCH_ROUTE)}>
      <span className="css-logo" aria-hidden="true"><i /><i /><i /></span>
      <span><small>LOCAL NATIVE INDEX</small><strong>Conversation Search</strong></span>
    </button>
    <nav aria-label="Conversation Search views">
      <button type="button" aria-current={view === "search" ? "page" : undefined} onClick={() => navigate(SEARCH_ROUTE)}>Search</button>
      <button type="button" aria-current={view === "operations" ? "page" : undefined} onClick={() => navigate(OPERATIONS_ROUTE)}>Index operations</button>
    </nav>
    <div className={`css-runtime ${ready ? "ready" : ""}`}><span />{ready ? (running ? "Service active" : "Command mode") : "Setup needed"}</div>
  </header>;
}

function LocationCard({ location }: { location: DataLocation }) {
  return <article className="css-location">
    <div><span className={`css-pill ${location.state}`}>{location.state}</span><small>{location.layout}</small></div>
    <code>{location.path}</code>
    <p>{location.state === "ready" ? `${location.conversations.toLocaleString()} conversations · ${location.files.toLocaleString()} indexable files` : location.message ?? "No conversation data detected here."}</p>
  </article>;
}

function Setup({ home, probe, busy, error, onInstall, onRecheck }: { home: string; probe: ProbeStatus; busy: string; error: string; onInstall: () => void; onRecheck: () => void }) {
  const [confirmed, setConfirmed] = useState(false);
  const [copied, setCopied] = useState(false);
  const canBuild = probe.supported && probe.goReady;
  const copy = async () => { await navigator.clipboard.writeText(agentSetupText(home)); setCopied(true); };
  return <main className="css-setup">
    <section className="css-hero">
      <div><span className="css-eyebrow">PRIVATE BY CONSTRUCTION</span><h1>Search years of agent work in milliseconds.</h1><p>Conversation text stays on this Agent Server. The read-only probe below did not create a directory, compile code, or open a conversation file.</p></div>
      <div className="css-orbit" aria-hidden="true"><span /><span /><span /><b>⌕</b></div>
    </section>
    <section className="css-setup-grid">
      <article><span className={probe.supported ? "ok" : "bad"}>{probe.supported ? "SUPPORTED" : "UNSUPPORTED"}</span><h2>{probe.target}</h2><p>{probe.os} · {probe.arch}</p><small>Supported: macOS and Linux on arm64/amd64.</small></article>
      <article><span className={probe.goReady ? "ok" : "warn"}>{probe.goReady ? "READY" : "MISSING / OLD"}</span><h2>Local Go build</h2><p>{probe.goVersion ?? "Go 1.23+ was not found."}</p><small>Go 1.23+ is required; no unverified prebuilt binary is executed.</small></article>
      <article><span className="neutral">APP-OWNED</span><h2>Durable local state</h2><code>{dataDirectory(home)}</code><small>Source, module/build cache, binary, index, logs, and run state live only here.</small></article>
    </section>
    <section className="css-section">
      <div className="css-section-title"><div><span className="css-eyebrow">DATA LOCATION DIAGNOSTICS</span><h2>Candidate SDK stores</h2></div><button className="css-button quiet" type="button" onClick={onRecheck} disabled={Boolean(busy)}>Recheck</button></div>
      <div className="css-locations">{probe.locations.map((location) => <LocationCard key={location.path} location={location} />)}</div>
    </section>
    <section className="css-trust">
      <div><span className="css-eyebrow">DELIBERATE INSTALL</span><h2>Build Conversation Search {SIDECAR_VERSION}</h2><p>The App writes its reviewed Go source, verifies SHA-256 <code>{SOURCE_SHA256.slice(0, 16)}…</code>, downloads the pinned Bleve module graph using the configured Go proxy, compiles locally for <strong>{probe.target}</strong>, records the binary SHA-256, and verifies the version and hash before every native execution.</p><p className="css-privacy"><strong>Sensitive local data:</strong> indexing creates a searchable copy of message text, selected command/output text, titles, timestamps, roles, and tool summaries. Hidden reasoning, system prompts, base state, and configured secrets are excluded. Nothing is uploaded by the App.</p></div>
      <label className="css-confirm"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /> I understand the disk/network actions and local sensitive-data copy.</label>
      {!canBuild ? <div className="css-warning" role="alert">This target needs a supported platform and Go 1.23+. Use the copyable agent prompt to inspect and install prerequisites with your approval.</div> : null}
      {error ? <div className="css-error" role="alert">{error}</div> : null}
      <div className="css-actions"><button className="css-button primary" type="button" disabled={!confirmed || !canBuild || Boolean(busy)} onClick={onInstall}>{busy || "Build & install locally"}</button><button className="css-button" type="button" onClick={() => void copy()}>{copied ? "Prompt copied" : "Copy agent setup prompt"}</button></div>
    </section>
  </main>;
}

function StatusStrip({ status }: { status: IndexStatus }) {
  return <section className="css-stats" aria-label="Index status">
    <article><small>DOCUMENTS</small><strong>{status.documents.toLocaleString()}</strong><span>{status.sourceFiles.toLocaleString()} source files</span></article>
    <article><small>CONVERSATIONS</small><strong>{status.conversations.toLocaleString()}</strong><span>{status.malformedFiles} malformed skipped</span></article>
    <article><small>INDEX SIZE</small><strong>{formatBytes(status.indexBytes)}</strong><span>{status.lastIndexedAt ? `Updated ${new Date(status.lastIndexedAt).toLocaleString()}` : "Not indexed yet"}</span></article>
    <article><small>EXECUTION</small><strong>{status.service.running ? "Service" : "Command"}</strong><span>{status.service.running ? `Idle stop in ${Math.max(0, IDLE_SHUTDOWN_SECONDS - (status.service.idleSeconds ?? 0))}s` : "One-shot CLI bridge"}</span></article>
  </section>;
}

function Inspector({ host, hit, navigate, close }: { host: CanvasHost; hit: SearchHit; navigate: (path: string) => void; close: () => void }) {
  return <aside className="css-inspector" aria-label="Indexed event inspector">
    <button type="button" className="css-close" onClick={close} aria-label="Close inspector">×</button>
    <span className="css-eyebrow">INDEXED EVENT</span><h2><ConversationLink host={host} conversationId={hit.conversationId} navigate={navigate}>{hit.title || "Untitled conversation"}</ConversationLink></h2>
    <dl><div><dt>Conversation</dt><dd><ConversationLink host={host} conversationId={hit.conversationId} navigate={navigate}>{hit.conversationId}</ConversationLink></dd></div><div><dt>Event</dt><dd>{hit.eventId}</dd></div><div><dt>Kind / role</dt><dd>{hit.kind} · {hit.role}</dd></div><div><dt>Tool</dt><dd>{hit.tool || "—"}</dd></div><div><dt>Timestamp</dt><dd>{hit.timestamp || "—"}</dd></div><div><dt>Source</dt><dd><code>{hit.sourcePath}</code></dd></div></dl>
    <h3>Indexed text</h3><pre>{hit.text || hit.summary || "This record contains metadata only."}</pre>
    <p className="css-muted">This is the selected, locally indexed representation—not the raw source JSON.</p>
  </aside>;
}

function SearchView({ host, home, status, setStatus, navigate, signal }: { host: CanvasHost; home: string; status: IndexStatus; setStatus: (value: IndexStatus) => void; navigate: (path: string) => void; signal: AbortSignal }) {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<SearchFilters>({});
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [selected, setSelected] = useState<SearchHit | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const mode = status.service.running ? "rpc" : "once";
  const runSearch = async (event?: React.FormEvent) => {
    event?.preventDefault(); setBusy("Searching…"); setError("");
    try { const response = await search(host, home, query, filters, mode, signal); setResults(response); setStatus(response.status); }
    catch (cause) { if (!isAbort(cause)) setError(message(cause)); }
    finally { setBusy(""); }
  };
  const inspect = async (id: string) => {
    setBusy("Loading event…"); setError("");
    try { setSelected(await inspectResult(host, home, id, mode, signal)); }
    catch (cause) { if (!isAbort(cause)) setError(message(cause)); }
    finally { setBusy(""); }
  };
  return <main className="css-workbench">
    <StatusStrip status={status} />
    <section className="css-search-panel">
      <div className="css-section-title"><div><span className="css-eyebrow">BLEVE FULL-TEXT INDEX</span><h1>Find the moment, not the folder.</h1></div><span className="css-mode">{mode === "rpc" ? "Persistent service bridge" : "One-shot command bridge"}</span></div>
      <form onSubmit={(event) => void runSearch(event)}>
        <div className="css-searchbox"><span aria-hidden="true">⌕</span><input aria-label="Search conversation index" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search messages, commands, summaries, titles…" /><button className="css-button primary" type="submit" disabled={Boolean(busy)}>{busy === "Searching…" ? busy : "Search"}</button></div>
        <div className="css-filters">
          <label>Role<select aria-label="Role filter" value={filters.role ?? ""} onChange={(event) => setFilters({ ...filters, role: event.target.value })}><option value="">Any role</option><option value="user">User</option><option value="agent">Agent</option><option value="environment">Environment</option><option value="conversation">Conversation</option></select></label>
          <label>Kind<input aria-label="Kind filter" value={filters.kind ?? ""} onChange={(event) => setFilters({ ...filters, kind: event.target.value })} placeholder="MessageEvent" /></label>
          <label>Tool<input aria-label="Tool filter" value={filters.tool ?? ""} onChange={(event) => setFilters({ ...filters, tool: event.target.value })} placeholder="terminal" /></label>
          <label>After<input aria-label="After date" type="date" value={filters.after ?? ""} onChange={(event) => setFilters({ ...filters, after: event.target.value })} /></label>
          <label>Before<input aria-label="Before date" type="date" value={filters.before ?? ""} onChange={(event) => setFilters({ ...filters, before: event.target.value })} /></label>
        </div>
      </form>
      {error ? <div className="css-error" role="alert">{error}</div> : null}
    </section>
    <section className="css-results">
      <div className="css-results-title"><strong>{results ? `${results.total.toLocaleString()} matches` : "Ready to search"}</strong>{results ? <span>{results.durationMs.toFixed(1)} ms · top {results.hits.length}</span> : <span>Run Index now from operations if this is your first visit.</span>}</div>
      {results?.hits.map((hit) => <article className="css-hit" key={hit.id}>
        <div><span className="css-role">{hit.role || "unknown"}</span><span>{hit.kind}</span>{hit.tool ? <span>{hit.tool}</span> : null}<time>{hit.timestamp ? new Date(hit.timestamp).toLocaleString() : "No timestamp"}</time></div>
        <h2><ConversationLink host={host} conversationId={hit.conversationId} navigate={navigate}>{hit.title || hit.conversationId}</ConversationLink></h2><p>{plainExcerpt(hit.excerpt) || "Metadata-only indexed record"}</p><button type="button" className="css-inspect-hit" onClick={() => void inspect(hit.id)}>Inspect indexed event</button><code>{hit.sourcePath}</code>
      </article>)}
      {results && results.hits.length === 0 ? <div className="css-empty"><span>⌕</span><h2>No indexed events matched.</h2><p>Try fewer filters, a broader phrase, or refresh the index.</p></div> : null}
    </section>
    {selected ? <Inspector host={host} hit={selected} navigate={navigate} close={() => setSelected(null)} /> : null}
  </main>;
}

function Operations({ host, home, status, setStatus, recheck, signal }: { host: CanvasHost; home: string; status: IndexStatus; setStatus: (value: IndexStatus) => void; recheck: () => void; signal: AbortSignal }) {
  const [busy, setBusy] = useState(""); const [error, setError] = useState(""); const [notice, setNotice] = useState(""); const [deleteArmed, setDeleteArmed] = useState(false);
  const mode = status.service.running ? "rpc" : "once";
  const action = async (label: string, work: () => Promise<void>) => { setBusy(label); setError(""); setNotice(""); try { await work(); setNotice(`${label} completed.`); } catch (cause) { if (!isAbort(cause)) setError(message(cause)); } finally { setBusy(""); } };
  const refresh = () => action("Recheck", async () => setStatus(await loadStatus(host, home, status.service.running ? "rpc" : "once", signal)));
  const index = (rebuild: boolean) => { if (rebuild && !window.confirm("Rebuild deletes only the App-owned Bleve index and source manifest, then recreates them from read-only conversation data. Continue?")) return; void action(rebuild ? "Full rebuild" : "Incremental index", async () => setStatus(await updateIndex(host, home, rebuild, mode, signal))); };
  const toggleService = () => void action(status.service.running ? "Stop service" : "Start service", async () => { if (status.service.running) await stopService(host, home, signal); else await startService(host, home, signal); setStatus(await loadStatus(host, home, "once", signal)); });
  const repair = () => { if (!window.confirm("Repair runtime stops the service, rewrites the reviewed source, verifies checksums, and recompiles the binary. The index is preserved. Continue?")) return; void action("Repair runtime", async () => { await repairRuntime(host, home, signal); recheck(); }); };
  const remove = () => void action("Delete App data", async () => { await deleteAppData(host, home, signal); recheck(); });
  return <main className="css-operations">
    <StatusStrip status={status} />
    <section className="css-section css-operation-hero"><div><span className="css-eyebrow">CONTROL PLANE</span><h1>Own the index lifecycle.</h1><p>Conversation sources are always read-only. Every mutation stays below <code>{dataDirectory(home)}</code>.</p></div><button className="css-button" type="button" onClick={() => void refresh()} disabled={Boolean(busy)}>Refresh status</button></section>
    {error ? <div className="css-error" role="alert">{error}</div> : null}{notice ? <div className="css-notice" role="status">{notice}</div> : null}
    <section className="css-operation-grid">
      <article><span className="css-step">01</span><h2>Index content</h2><p>Incremental updates compare source path, size, nanosecond mtime, and SHA-256 fallback. Changed records are upserted and deleted sources are removed.</p><div className="css-actions"><button className="css-button primary" onClick={() => index(false)} disabled={Boolean(busy)}>{busy === "Incremental index" ? "Indexing…" : "Index now"}</button><button className="css-button" onClick={() => index(true)} disabled={Boolean(busy)}>Full rebuild</button></div>{status.added || status.updated || status.removed || status.skipped ? <small>Last run: {status.added ?? 0} added · {status.updated ?? 0} updated · {status.removed ?? 0} removed · {status.skipped ?? 0} unchanged</small> : null}</article>
      <article><span className="css-step">02</span><h2>Native service</h2><p>The browser never calls localhost. Bash invokes the verified companion CLI, which reads an App-private token/port state file and performs JSON RPC.</p><div className="css-actions"><button className="css-button primary" onClick={toggleService} disabled={Boolean(busy)}>{status.service.running ? "Stop service" : "Start service"}</button></div><small>Automatic idle shutdown after {IDLE_SHUTDOWN_SECONDS / 60} minutes; App disablement leaves no permanent daemon.</small></article>
      <article><span className="css-step">03</span><h2>Recover safely</h2><p>Repair runtime recompiles from verified source and preserves the index. Full rebuild repairs an unreadable index from unchanged source data.</p><button className="css-button" onClick={repair} disabled={Boolean(busy)}>Repair runtime</button></article>
    </section>
    <section className="css-section"><div className="css-section-title"><div><span className="css-eyebrow">SOURCE HEALTH</span><h2>Validated locations</h2></div></div><div className="css-locations">{status.locations.map((location) => <LocationCard key={location.path} location={location} />)}</div></section>
    <section className="css-danger"><div><h2>Uninstall App-owned data</h2><p>Stop the service and permanently delete the binary, local source/build cache, Bleve index, manifests, logs, and run state. Conversation sources and sibling Apps are untouched.</p><code>{dataDirectory(home)}</code></div>{deleteArmed ? <div className="css-actions"><button className="css-button danger" onClick={() => void remove()} disabled={Boolean(busy)}>Delete exact directory</button><button className="css-button" onClick={() => setDeleteArmed(false)}>Cancel</button></div> : <button className="css-button danger" onClick={() => setDeleteArmed(true)}>Review deletion</button>}</section>
  </main>;
}

export function App({ host, path, navigate, signal }: { host: CanvasHost; path: string; navigate: (path: string) => void; signal: AbortSignal }) {
  const view = normalizeRoute(path);
  const [attempt, setAttempt] = useState(0); const [home, setHome] = useState(""); const [probe, setProbe] = useState<ProbeStatus | null>(null); const [status, setStatus] = useState<IndexStatus | null>(null); const [busy, setBusy] = useState(""); const [error, setError] = useState("");
  useEffect(() => {
    setHome(""); setProbe(null); setStatus(null); setError("");
    discoverHome(host, signal).then(async (nextHome) => { setHome(nextHome); const nextProbe = await probePrerequisites(host, nextHome, signal); setProbe(nextProbe); if (nextProbe.installed) setStatus(await loadStatus(host, nextHome, "once", signal)); }).catch((cause: unknown) => { if (!isAbort(cause)) setError(message(cause)); });
  }, [attempt, host, signal]);
  const recheck = useCallback(() => setAttempt((value) => value + 1), []);
  const install = useCallback(async () => { setBusy("Building native sidecar…"); setError(""); try { await installOrRepair(host, home, signal); setAttempt((value) => value + 1); } catch (cause) { if (!isAbort(cause)) setError(message(cause)); } finally { setBusy(""); } }, [home, host, signal]);
  const content = useMemo(() => {
    if (view === "not-found") return <main className="css-state"><span className="css-eyebrow">UNKNOWN ROUTE</span><h1>This page is not part of Conversation Search.</h1><button className="css-button primary" onClick={() => navigate(SEARCH_ROUTE)}>Open search</button></main>;
    if (error && !probe) return <main className="css-state"><span className="css-eyebrow">BACKEND ERROR</span><h1>Could not inspect this Agent Server.</h1><p>{error}</p><button className="css-button primary" onClick={recheck}>Try again</button></main>;
    if (!home || !probe) return <main className="css-state"><div className="css-loader"><i /><i /><i /></div><span className="css-eyebrow">READ-ONLY PROBE</span><h1>Mapping local conversation stores…</h1></main>;
    if (!probe.installed || !status) return <Setup home={home} probe={probe} busy={busy} error={error} onInstall={() => void install()} onRecheck={recheck} />;
    return view === "operations" ? <Operations host={host} home={home} status={status} setStatus={setStatus} recheck={recheck} signal={signal} /> : <SearchView host={host} home={home} status={status} setStatus={setStatus} navigate={navigate} signal={signal} />;
  }, [busy, error, home, host, install, navigate, probe, recheck, signal, status, view]);
  return <section className="conversation-search-sidecar"><Header view={view} ready={Boolean(probe?.installed && status)} running={Boolean(status?.service.running)} navigate={navigate} />{content}<footer><span>Local-only index · {host.backend.kind ?? "unknown"} / {host.backend.id ?? "unavailable"}</span><span>No conversation content is transmitted by this App</span></footer></section>;
}
