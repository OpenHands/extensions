import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { addAudit, loadAudit } from "./audit";
import {
  DATABASE_FILENAME,
  MAX_IMPORT_BYTES,
  agentHandoffText,
  agentSetupText,
  dataDirectory,
  discoverHome,
  exportDatabase,
  importDatabase,
  installOrRepair,
  loadDatabase,
  probePrerequisites,
  resetData,
  runQuery,
} from "./backend-service";
import type { AuditEntry, CanvasHost, DatabaseSnapshot, ProbeStatus, QueryResponse, SqlValue } from "./types";

export const STUDIO_ROUTE = "/extensions/backend-sqlite-studio/studio";
export const HANDOFF_ROUTE = "/extensions/backend-sqlite-studio/handoff";
export const DEFAULT_SQL = `SELECT id, title, body, created_at
FROM notes
ORDER BY id DESC
LIMIT 100;`;

type View = "studio" | "handoff" | "not-found";

export function normalizeRoute(pageId: string, path: string): View {
  const segment = path.replace(/^\/+|\/+$/g, "").split("/").filter(Boolean)[0] ?? "";
  if (pageId === "studio" && (segment === "" || segment === "studio")) return "studio";
  if (pageId === "handoff" && (segment === "" || segment === "handoff")) return "handoff";
  return "not-found";
}

function message(error: unknown): string { return error instanceof Error ? error.message : String(error); }
function isAbort(error: unknown): boolean { return error instanceof DOMException && error.name === "AbortError"; }
function formatValue(value: SqlValue): string {
  if (value === null) return "NULL";
  if (typeof value === "object") return `[BLOB · ${value.blobBytes} bytes]`;
  return String(value);
}

function Header({ view, navigate, ready }: { view: View; navigate: (path: string) => void; ready: boolean }) {
  return <header className="bss-header">
    <button className="bss-brand" type="button" onClick={() => navigate(STUDIO_ROUTE)}>
      <span className="bss-mark" aria-hidden="true"><i /><i /><i /></span>
      <span><small>AGENT SERVER DATA</small><strong>SQLite Studio</strong></span>
    </button>
    <nav aria-label="Backend SQLite Studio pages">
      <button type="button" aria-current={view === "studio" ? "page" : undefined} onClick={() => navigate(STUDIO_ROUTE)}>Studio</button>
      <button type="button" aria-current={view === "handoff" ? "page" : undefined} onClick={() => navigate(HANDOFF_ROUTE)}>Agent handoff</button>
    </nav>
    <div className={`bss-status ${ready ? "is-ready" : ""}`}><span />{ready ? "Backend ready" : "Setup needed"}</div>
  </header>;
}

function Setup({ home, probe, busy, onInstall, onRecheck, onRepair, onCopy, copyNotice, audit }: {
  home: string; probe: ProbeStatus; busy: string; onInstall: () => void; onRecheck: () => void; onRepair: () => void; onCopy: () => void; copyNotice: string; audit: AuditEntry[];
}) {
  const [confirmed, setConfirmed] = useState(false);
  const directory = dataDirectory(home);
  const partial = probe.wrapperPresent || probe.databasePresent || probe.runtimeVersion !== null;
  return <main className="bss-setup">
    <div className="bss-setup-hero">
      <span className="bss-eyebrow">FIRST-RUN CHECK</span>
      <h1>Give this database a durable home.</h1>
      <p>The probe only inspected installed commands and file presence. It did not create directories, download software, or open a database.</p>
    </div>
    <section className="bss-setup-grid">
      <article><span className={probe.pythonReady ? "ok" : "warn"}>{probe.pythonReady ? "READY" : "MISSING"}</span><h2>Python SQLite runtime</h2><p>{probe.pythonVersion ?? "python3 was not detected"}</p><code>{probe.sqliteModuleVersion ? `SQLite ${probe.sqliteModuleVersion}` : "sqlite3 module unavailable"}</code></article>
      <article><span className={probe.sqliteCliVersion ? "ok" : "neutral"}>{probe.sqliteCliVersion ? "DETECTED" : "OPTIONAL"}</span><h2>sqlite3 CLI</h2><p>{probe.sqliteCliVersion ?? "Not installed; the App does not require it."}</p><small>The App uses Python’s standard sqlite3 module so no database engine is downloaded.</small></article>
      <article><span className={partial ? "warn" : "neutral"}>{partial ? "PARTIAL" : "PROPOSED"}</span><h2>App-owned directory</h2><code>{directory}</code><p>Install writes <strong>wrapper.py</strong>, a runtime marker, and <strong>{DATABASE_FILENAME}</strong> only here.</p></article>
    </section>
    {!probe.pythonReady ? <section className="bss-callout is-warning" role="alert"><strong>A compatible runtime is required.</strong><p>Copy the setup prompt and ask an OpenHands agent to inspect the operating system, explain any package changes, obtain approval, and install Python 3 with SQLite support. Then recheck.</p></section> : null}
    <section className="bss-consent">
      <div><span className="bss-eyebrow">DELIBERATE SETUP</span><h2>{partial ? "Repair the App-owned runtime" : "Initialize Backend SQLite Studio"}</h2><p>This creates or replaces the App’s wrapper and migration marker, creates the database if absent, and applies versioned migrations. Repair preserves existing database rows.</p></div>
      <label><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /> I understand the files and target shown above.</label>
      <div className="bss-actions">
        <button type="button" className="bss-button primary" disabled={!confirmed || !probe.pythonReady || Boolean(busy)} onClick={partial ? onRepair : onInstall}>{busy || (partial ? "Repair" : "Install")}</button>
        <button type="button" className="bss-button" disabled={Boolean(busy)} onClick={onRecheck}>Recheck</button>
        <button type="button" className="bss-button" onClick={onCopy}>Copy agent setup prompt</button>
      </div>
      <small aria-live="polite">{copyNotice}</small>
    </section>
    <Audit entries={audit} />
  </main>;
}

function Sidebar({ snapshot, restore }: { snapshot: DatabaseSnapshot; restore: (sql: string) => void }) {
  return <aside className="bss-sidebar">
    <section><div className="bss-side-title"><h2>Schema</h2><span>{snapshot.tables.length}</span></div>
      {snapshot.tables.map((table) => <details open key={table.name}><summary>▦ {table.name}<span>{table.columns.length}</span></summary><ul>{table.columns.map((column) => <li key={column.name}><code>{column.name}</code><small>{column.type}{column.primaryKey ? " · PK" : ""}{column.nullable ? "" : " · required"}</small></li>)}</ul></details>)}
    </section>
    <section><div className="bss-side-title"><h2>Migrations</h2><span>{snapshot.migrations.length}</span></div>{snapshot.migrations.map((item) => <div className="bss-migration" key={item.id}><i /><div><strong>{item.id}</strong><small>{new Date(item.appliedAt).toLocaleString()}</small></div></div>)}</section>
    <section className="bss-history"><div className="bss-side-title"><h2>Query history</h2><span>{snapshot.history.length}</span></div>{snapshot.history.map((item) => <button type="button" key={item.id} onClick={() => restore(item.sql)} title={item.message || item.sql}><i className={item.status} /><span><code>{item.sql.replace(/\s+/g, " ")}</code><small>{item.status} · {new Date(item.executedAt).toLocaleTimeString()}</small></span></button>)}</section>
  </aside>;
}

function Results({ response }: { response: QueryResponse | null }) {
  if (!response) return <div className="bss-empty"><strong>Results land here</strong><p>Run the starter query or create your own tables inside this database.</p></div>;
  if (!response.results.length) return <div className="bss-summary">Completed in {response.durationMs.toFixed(1)} ms · {response.rowsAffected} row{response.rowsAffected === 1 ? "" : "s"} changed</div>;
  return <div>{response.results.map((result, index) => <section className="bss-result" key={index}><div className="bss-result-meta"><span>Result {index + 1}</span><span>{result.values.length}{result.truncated ? "+" : ""} rows · {response.durationMs.toFixed(1)} ms</span></div><div className="bss-table-wrap"><table><thead><tr>{result.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{result.values.map((row, rowIndex) => <tr key={rowIndex}>{row.map((value, columnIndex) => <td key={columnIndex} className={value === null ? "is-null" : undefined}>{formatValue(value)}</td>)}</tr>)}</tbody></table></div>{result.truncated ? <p className="bss-limit">Showing the first 250 rows.</p> : null}</section>)}</div>;
}

function Audit({ entries }: { entries: AuditEntry[] }) {
  return <section className="bss-audit"><div className="bss-panel-heading"><div><span className="bss-eyebrow">THIS BROWSER · THIS BACKEND</span><h2>Action record</h2></div><span>{entries.length}</span></div>{entries.length ? <ol>{entries.map((entry) => <li key={entry.id}><i className={entry.status} /><div><strong>{entry.action}</strong><p>{entry.detail}</p></div><time>{new Date(entry.at).toLocaleString()}</time></li>)}</ol> : <p className="bss-empty-line">No mutating setup or data actions recorded in this browser yet.</p>}</section>;
}

function Workbench({ host, home, snapshot, setSnapshot, audit, setAudit, signal, recheck, onRepair }: {
  host: CanvasHost; home: string; snapshot: DatabaseSnapshot; setSnapshot: (value: DatabaseSnapshot) => void; audit: AuditEntry[]; setAudit: (value: AuditEntry[]) => void; signal: AbortSignal; recheck: () => void; onRepair: () => void;
}) {
  const [sql, setSql] = useState(DEFAULT_SQL);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [confirmReset, setConfirmReset] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [confirmImport, setConfirmImport] = useState(false);
  const [confirmRepair, setConfirmRepair] = useState(false);
  const urls = useRef(new Set<string>());
  const directory = dataDirectory(home);
  const databasePath = `${directory}/${DATABASE_FILENAME}`;

  useEffect(() => () => { for (const url of urls.current) URL.revokeObjectURL(url); urls.current.clear(); }, []);
  const record = useCallback((action: string, detail: string, status: "success" | "error" = "success") => setAudit(addAudit(host.backend, { action, detail, status })), [host.backend, setAudit]);
  const perform = useCallback(async (name: string, task: () => Promise<void>) => {
    setBusy(name); setError(""); setNotice("");
    try { await task(); }
    catch (caught) { if (!isAbort(caught)) { const detail = message(caught); setError(detail); record(name, detail, "error"); } }
    finally { setBusy(""); }
  }, [record]);

  const query = () => void perform("Run SQL", async () => {
    const next = await runQuery(host, home, sql, signal); setSnapshot(next); setResponse(next); setNotice("SQL completed on the Agent Server database."); record("Run SQL", `${next.rowsAffected} rows changed · ${sql.replace(/\s+/g, " ").slice(0, 180)}`);
  });
  const download = () => void perform("Export database", async () => {
    const result = await exportDatabase(host, home, signal); const url = URL.createObjectURL(new Blob([result.bytes as BlobPart], { type: "application/vnd.sqlite3" })); urls.current.add(url); const link = document.createElement("a"); link.href = url; link.download = `backend-sqlite-studio-${Date.now()}.sqlite3`; link.click(); window.setTimeout(() => { URL.revokeObjectURL(url); urls.current.delete(url); }, 0); setNotice(`Exported ${result.sizeBytes.toLocaleString()} bytes.`);
  });
  const replaceDatabase = () => void perform("Import database", async () => {
    if (!importFile) throw new Error("Choose a SQLite file first.");
    if (importFile.size > MAX_IMPORT_BYTES) throw new Error("Import is limited to 16 MiB.");
    const bytes = new Uint8Array(await importFile.arrayBuffer()); const next = await importDatabase(host, home, bytes, signal); setSnapshot(next); setResponse(null); setConfirmImport(false); setImportFile(null); setNotice("Imported database, verified integrity, and applied migrations."); record("Import database", `Replaced ${databasePath} with ${bytes.byteLength.toLocaleString()} validated bytes.`);
  });
  const reset = () => void perform("Reset data", async () => {
    await resetData(host, home, signal); record("Reset data", `Deleted only ${directory}.`); setConfirmReset(false); setResponse(null); recheck();
  });

  return <main className="bss-workspace"><Sidebar snapshot={snapshot} restore={setSql} /><div className="bss-main">
    <section className="bss-boundary"><span>◎</span><div><strong>Agent Server persistence boundary</strong><p>Shared database data lives on the backend. Editor text and this action record stay in this browser.</p></div><code title={databasePath}>{databasePath}</code></section>
    <section className="bss-status-grid"><article><small>DATABASE</small><strong>{(snapshot.sizeBytes / 1024).toFixed(1)} KiB</strong><span>{snapshot.journalMode} journal</span></article><article><small>TABLES</small><strong>{snapshot.tables.length}</strong><span>user-visible</span></article><article><small>MIGRATIONS</small><strong>{snapshot.migrations.length}</strong><span>applied</span></article></section>
    <section className="bss-panel"><div className="bss-panel-heading"><div><span className="bss-eyebrow">STRUCTURED WRAPPER</span><h1>SQL editor</h1></div><div className="bss-actions"><button className="bss-button" type="button" disabled={Boolean(busy)} onClick={recheck}>Recheck &amp; refresh</button><button className="bss-button" type="button" disabled={Boolean(busy)} onClick={() => setConfirmRepair(true)}>Repair</button><button className="bss-button" type="button" disabled={Boolean(busy)} onClick={download}>Export</button><label className="bss-button file">Import<input type="file" accept=".sqlite,.sqlite3,.db,application/vnd.sqlite3" onChange={(event) => { setImportFile(event.target.files?.[0] ?? null); setConfirmImport(Boolean(event.target.files?.[0])); }} /></label><button className="bss-button danger" type="button" onClick={() => setConfirmReset(true)}>Reset data</button></div></div>
      <textarea aria-label="SQL editor" value={sql} onChange={(event) => setSql(event.target.value)} onKeyDown={(event) => { if ((event.metaKey || event.ctrlKey) && event.key === "Enter") { event.preventDefault(); query(); } }} spellCheck={false} />
      <div className="bss-editor-footer"><span>SQL becomes base64 JSON—not shell source. External-file and transaction-control statements are blocked.</span><button className="bss-button primary" type="button" disabled={Boolean(busy)} onClick={query}>{busy === "Run SQL" ? "Running…" : "Run SQL"}</button></div>
    </section>
    {confirmImport && importFile ? <section className="bss-confirm" role="alertdialog" aria-labelledby="import-title"><div><strong id="import-title">Replace the database with {importFile.name}?</strong><p>This overwrites <code>{databasePath}</code> after a SQLite integrity check. The existing file cannot be restored by this App.</p></div><div><button className="bss-button" type="button" onClick={() => { setConfirmImport(false); setImportFile(null); }}>Cancel</button><button data-testid="confirm-import" className="bss-button danger-solid" type="button" onClick={replaceDatabase}>Import and replace</button></div></section> : null}
    {confirmRepair ? <section className="bss-confirm is-repair" role="alertdialog" aria-labelledby="repair-title"><div><strong id="repair-title">Repair the structured wrapper?</strong><p>This replaces <code>{directory}/wrapper.py</code> and the runtime marker, then reapplies pending migrations. Existing database rows are preserved.</p></div><div><button className="bss-button" type="button" onClick={() => setConfirmRepair(false)}>Cancel</button><button data-testid="confirm-repair" className="bss-button primary" type="button" onClick={() => { setConfirmRepair(false); onRepair(); }}>Repair wrapper</button></div></section> : null}
    {confirmReset ? <section className="bss-confirm" role="alertdialog" aria-labelledby="reset-title"><div><strong id="reset-title">Delete all Backend SQLite Studio data?</strong><p>The exact deletion target is <code>{directory}</code>. This removes the database, history, migrations, and wrapper; it cannot be undone.</p></div><div><button className="bss-button" type="button" onClick={() => setConfirmReset(false)}>Keep data</button><button data-testid="confirm-reset" className="bss-button danger-solid" type="button" onClick={reset}>Delete exact directory</button></div></section> : null}
    {error ? <div className="bss-message error" role="alert"><strong>Action failed</strong><span>{error}</span></div> : null}{notice ? <div className="bss-message success" role="status">✓ {notice}</div> : null}
    <section className="bss-panel"><div className="bss-panel-heading"><div><span className="bss-eyebrow">OUTPUT</span><h2>Results</h2></div></div><Results response={response} /></section>
    <Audit entries={audit} />
  </div></main>;
}

function Handoff({ home, copy }: { home: string; copy: () => void }) {
  const text = agentHandoffText(home); const path = `${dataDirectory(home)}/${DATABASE_FILENAME}`;
  return <main className="bss-handoff"><span className="bss-eyebrow">ONE DATABASE · MANY CLIENTS</span><h1>Hand durable context to an agent.</h1><p>The database is on the selected Agent Server, so another Canvas client or an OpenHands agent can work with the same rows. Browser editor text and the browser action record are separate and are not shared.</p><section><small>EXACT DATABASE PATH</small><code>{path}</code><h2>Safe agent instructions</h2><pre>{text}</pre><button className="bss-button primary" type="button" onClick={copy}>Copy agent handoff</button></section></main>;
}

export function App({ host, pageId, path, navigate, signal }: { host: CanvasHost; pageId: string; path: string; navigate: (path: string) => void; signal: AbortSignal }) {
  const view = normalizeRoute(pageId, path);
  const [home, setHome] = useState(""); const [probe, setProbe] = useState<ProbeStatus | null>(null); const [snapshot, setSnapshot] = useState<DatabaseSnapshot | null>(null);
  const [startupError, setStartupError] = useState(""); const [busy, setBusy] = useState(""); const [copyNotice, setCopyNotice] = useState(""); const [attempt, setAttempt] = useState(0); const [audit, setAudit] = useState(() => loadAudit(host.backend));
  const ready = Boolean(probe?.initialized && snapshot);

  useEffect(() => {
    setStartupError(""); setProbe(null); setSnapshot(null);
    discoverHome(host, signal).then(async (nextHome) => { setHome(nextHome); const nextProbe = await probePrerequisites(host, nextHome, signal); setProbe(nextProbe); if (nextProbe.initialized) setSnapshot(await loadDatabase(host, nextHome, signal)); }).catch((error: unknown) => { if (!isAbort(error)) setStartupError(message(error)); });
  }, [attempt, host, signal]);

  const recheck = useCallback(() => setAttempt((value) => value + 1), []);
  const copyHandoff = useCallback(async () => { if (!home) return; await navigator.clipboard.writeText(agentHandoffText(home)); setCopyNotice("Prompt copied."); }, [home]);
  const copySetup = useCallback(async () => { if (!home) return; await navigator.clipboard.writeText(agentSetupText(home)); setCopyNotice("Setup prompt copied."); }, [home]);
  const setup = useCallback(async (action: "Install" | "Repair") => {
    setBusy(`${action}ing…`); setStartupError("");
    try { const next = await installOrRepair(host, home, signal); setSnapshot(next); setProbe(await probePrerequisites(host, home, signal)); setAudit(addAudit(host.backend, { action, detail: `${action} completed in ${dataDirectory(home)}.`, status: "success" })); }
    catch (error) { if (!isAbort(error)) { const detail = message(error); setStartupError(detail); setAudit(addAudit(host.backend, { action, detail, status: "error" })); } }
    finally { setBusy(""); }
  }, [home, host, signal]);

  const content = useMemo(() => {
    if (view === "not-found") return <main className="bss-state"><span className="bss-eyebrow">UNKNOWN ROUTE</span><h1>This view is not part of Backend SQLite Studio.</h1><button className="bss-button primary" onClick={() => navigate(STUDIO_ROUTE)}>Open Studio</button></main>;
    if (startupError && !probe) return <main className="bss-state error-state" role="alert"><span>!</span><h1>Backend discovery failed.</h1><p>{startupError}</p><button className="bss-button primary" onClick={recheck}>Try again</button></main>;
    if (!home || !probe) return <main className="bss-state"><div className="bss-loader"><i /><i /><i /></div><span className="bss-eyebrow">NON-MUTATING PROBE</span><h1>Inspecting the Agent Server…</h1></main>;
    if (view === "handoff") return <Handoff home={home} copy={copyHandoff} />;
    if (!probe.initialized || !snapshot) return <><Setup home={home} probe={probe} busy={busy} onInstall={() => void setup("Install")} onRepair={() => void setup("Repair")} onRecheck={recheck} onCopy={() => void copySetup()} copyNotice={copyNotice} audit={audit} />{startupError ? <div className="bss-message error setup-error" role="alert">{startupError}</div> : null}</>;
    return <Workbench host={host} home={home} snapshot={snapshot} setSnapshot={setSnapshot} audit={audit} setAudit={setAudit} signal={signal} recheck={recheck} onRepair={() => void setup("Repair")} />;
  }, [audit, busy, copyHandoff, copySetup, copyNotice, home, host, navigate, probe, recheck, setup, signal, snapshot, startupError, view]);

  return <section className="backend-sqlite-studio" aria-label="Backend SQLite Studio App"><Header view={view} navigate={navigate} ready={ready} />{content}<footer><span>Backend data · {host.backend.kind ?? "unknown"} / {host.backend.id ?? "unavailable"}</span><span>Browser preferences remain client-local</span></footer></section>;
}
