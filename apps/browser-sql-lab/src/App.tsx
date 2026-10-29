import { memo, useCallback, useDeferredValue, useEffect, useRef, useState } from "react";
import { DatabaseClient } from "./database-client";
import { makeDatabaseNamespace } from "./storage";
import type {
  CanvasHost,
  DatabaseSnapshot,
  QueryResponse,
  QueryTable,
  SqlValue,
} from "./types";

export const ROOT_ROUTE = "/extensions/browser-sql-lab/sql-lab";
export const DEFAULT_QUERY = `SELECT
  author,
  COUNT(*) AS books,
  ROUND(AVG(rating), 2) AS average_rating
FROM books
GROUP BY author
ORDER BY average_rating DESC;`;

type Route = "lab" | "about" | "not-found";

interface AppProps {
  host: CanvasHost;
  path: string;
  navigate: (path: string) => void;
  signal: AbortSignal;
  client: DatabaseClient;
}

export function normalizeRoute(path: string): Route {
  const route = path.replace(/^\/+|\/+$/g, "").split("/")[0];
  if (route === "" || route === "lab") return "lab";
  if (route === "about") return "about";
  return "not-found";
}

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function formatValue(value: SqlValue): string {
  if (value === null) return "NULL";
  if (value instanceof Uint8Array) return `[BLOB · ${value.byteLength} bytes]`;
  return String(value);
}

const ResultsGrid = memo(function ResultsGrid({ response }: { response: QueryResponse | null }) {
  const deferredResponse = useDeferredValue(response);
  if (!deferredResponse) {
    return (
      <div className="sql-empty sql-empty--results">
        <span className="sql-empty-icon">›_</span>
        <strong>Results will appear here</strong>
        <p>Seed the library, then run the starter query or write your own SQL.</p>
      </div>
    );
  }

  if (deferredResponse.results.length === 0) {
    return (
      <div className="sql-query-summary" data-testid="query-summary">
        Query completed in {deferredResponse.durationMs.toFixed(1)} ms · {deferredResponse.rowsAffected} row
        {deferredResponse.rowsAffected === 1 ? "" : "s"} changed
      </div>
    );
  }

  return (
    <div className="sql-result-stack" data-testid="query-results">
      {deferredResponse.results.map((table: QueryTable, tableIndex) => {
        const visibleRows = table.values.slice(0, 250);
        return (
          <section className="sql-result" key={`${tableIndex}-${table.columns.join("-")}`}>
            <div className="sql-result-meta">
              <span>Result {tableIndex + 1}</span>
              <span>{table.values.length} rows · {deferredResponse.durationMs.toFixed(1)} ms</span>
            </div>
            <div className="sql-table-wrap">
              <table>
                <thead>
                  <tr>{table.columns.map((column) => <th key={column}>{column}</th>)}</tr>
                </thead>
                <tbody>
                  {visibleRows.map((row, rowIndex) => (
                    <tr key={rowIndex}>
                      {row.map((value, columnIndex) => (
                        <td className={value === null ? "sql-null" : undefined} key={columnIndex}>
                          {formatValue(value)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {table.values.length > visibleRows.length ? (
              <p className="sql-limit-note">Showing the first {visibleRows.length} rows to keep Canvas responsive.</p>
            ) : null}
          </section>
        );
      })}
    </div>
  );
});

function SchemaExplorer({ snapshot }: { snapshot: DatabaseSnapshot }) {
  return (
    <section className="sql-side-section" aria-labelledby="schema-title">
      <div className="sql-side-heading">
        <h2 id="schema-title">Schema</h2>
        <span>{snapshot.tables.length}</span>
      </div>
      {snapshot.tables.length === 0 ? <p className="sql-muted">No user tables yet.</p> : null}
      <div className="sql-schema-list">
        {snapshot.tables.map((table) => (
          <details key={table.name} open>
            <summary><span className="sql-table-glyph">▦</span>{table.name}<span>{table.columns.length}</span></summary>
            <ul>
              {table.columns.map((column) => (
                <li key={column.name}>
                  <code>{column.name}</code>
                  <small>{column.type}{column.primaryKey ? " · PK" : ""}{column.nullable ? "" : " · required"}</small>
                </li>
              ))}
            </ul>
          </details>
        ))}
      </div>
    </section>
  );
}

function MigrationList({ snapshot }: { snapshot: DatabaseSnapshot }) {
  return (
    <section className="sql-side-section" aria-labelledby="migration-title">
      <div className="sql-side-heading"><h2 id="migration-title">Migrations</h2><span>{snapshot.migrations.length}</span></div>
      {snapshot.migrations.map((migration) => (
        <div className="sql-migration" key={migration.id}>
          <span className="sql-status-dot" aria-hidden="true" />
          <div><strong>{migration.id}</strong><small>{new Date(migration.appliedAt).toLocaleString()}</small></div>
        </div>
      ))}
    </section>
  );
}

function QueryHistory({ snapshot, restore }: { snapshot: DatabaseSnapshot; restore: (sql: string) => void }) {
  return (
    <section className="sql-side-section sql-history" aria-labelledby="history-title">
      <div className="sql-side-heading"><h2 id="history-title">History</h2><span>{snapshot.history.length}</span></div>
      {snapshot.history.length === 0 ? <p className="sql-muted">Executed queries will be saved here.</p> : null}
      {snapshot.history.map((entry) => (
        <button type="button" key={entry.id} onClick={() => restore(entry.sql)} title={entry.sql}>
          <span className={`sql-history-status sql-history-status--${entry.status}`} aria-label={entry.status} />
          <span><code>{entry.sql.replace(/\s+/g, " ")}</code><small>{new Date(entry.executedAt).toLocaleTimeString()}</small></span>
        </button>
      ))}
    </section>
  );
}

function LoadingState({ namespace }: { namespace: string }) {
  return (
    <main className="sql-state" aria-live="polite">
      <div className="sql-loader" aria-hidden="true"><span /><span /><span /></div>
      <p className="sql-eyebrow">Starting embedded SQLite</p>
      <h1>Preparing your browser-local database…</h1>
      <p>Loading the bundled WASM engine, opening IndexedDB, and applying migrations.</p>
      <code>{namespace}</code>
    </main>
  );
}

function ErrorState({ message, retry }: { message: string; retry: () => void }) {
  return (
    <main className="sql-state sql-state--error" role="alert">
      <span className="sql-error-mark">!</span>
      <p className="sql-eyebrow">Database unavailable</p>
      <h1>Browser SQL Lab could not start.</h1>
      <p>{message}</p>
      <button className="sql-button sql-button--primary" type="button" onClick={retry}>Try initialization again</button>
    </main>
  );
}

function Lab({
  client,
  snapshot,
  setSnapshot,
  signal,
}: {
  client: DatabaseClient;
  snapshot: DatabaseSnapshot;
  setSnapshot: (snapshot: DatabaseSnapshot) => void;
  signal: AbortSignal;
}) {
  const [sql, setSql] = useState(DEFAULT_QUERY);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [busy, setBusy] = useState<"query" | "seed" | "export" | "reset" | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [confirmReset, setConfirmReset] = useState(false);
  const activeRequest = useRef<AbortController | null>(null);
  const exportUrls = useRef(new Set<string>());

  useEffect(() => () => {
    activeRequest.current?.abort();
    for (const url of exportUrls.current) URL.revokeObjectURL(url);
    exportUrls.current.clear();
  }, []);

  const startRequest = useCallback(() => {
    activeRequest.current?.abort();
    const controller = new AbortController();
    signal.addEventListener("abort", () => controller.abort(), { once: true, signal: controller.signal });
    activeRequest.current = controller;
    setError("");
    setNotice("");
    return controller;
  }, [signal]);

  const finishRequest = useCallback((controller: AbortController) => {
    if (activeRequest.current === controller) {
      activeRequest.current = null;
      setBusy(null);
    }
    controller.abort();
  }, []);

  const runQuery = useCallback(async () => {
    const controller = startRequest();
    setBusy("query");
    try {
      const next = await client.query(sql, controller.signal);
      setResponse(next);
      setSnapshot(next);
      setNotice("Query completed and browser-local changes were saved.");
    } catch (requestError) {
      if (!isAbort(requestError)) setError(errorMessage(requestError));
    } finally {
      finishRequest(controller);
    }
  }, [client, finishRequest, setSnapshot, sql, startRequest]);

  const seed = useCallback(async () => {
    const controller = startRequest();
    setBusy("seed");
    try {
      const next = await client.seed(controller.signal);
      setSnapshot(next);
      setNotice("Five embedded library records were upserted and saved.");
    } catch (requestError) {
      if (!isAbort(requestError)) setError(errorMessage(requestError));
    } finally {
      finishRequest(controller);
    }
  }, [client, finishRequest, setSnapshot, startRequest]);

  const exportDatabase = useCallback(async () => {
    const controller = startRequest();
    setBusy("export");
    try {
      const bytes = await client.export(controller.signal);
      const blob = new Blob([bytes as BlobPart], { type: "application/vnd.sqlite3" });
      const url = URL.createObjectURL(blob);
      exportUrls.current.add(url);
      const link = document.createElement("a");
      link.href = url;
      link.download = `browser-sql-lab-${Date.now()}.sqlite3`;
      link.click();
      window.setTimeout(() => {
        URL.revokeObjectURL(url);
        exportUrls.current.delete(url);
      }, 0);
      setNotice(`Exported ${bytes.byteLength.toLocaleString()} bytes as SQLite.`);
    } catch (requestError) {
      if (!isAbort(requestError)) setError(errorMessage(requestError));
    } finally {
      finishRequest(controller);
    }
  }, [client, finishRequest, startRequest]);

  const resetDatabase = useCallback(async () => {
    const controller = startRequest();
    setBusy("reset");
    try {
      const next = await client.reset(controller.signal);
      setSnapshot(next);
      setResponse(null);
      setConfirmReset(false);
      setNotice("Database reset complete. The schema migration was reapplied.");
    } catch (requestError) {
      if (!isAbort(requestError)) setError(errorMessage(requestError));
    } finally {
      finishRequest(controller);
    }
  }, [client, finishRequest, setSnapshot, startRequest]);

  const onEditorKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      void runQuery();
    }
  };

  return (
    <main className="sql-workspace">
      <aside className="sql-sidebar">
        <SchemaExplorer snapshot={snapshot} />
        <MigrationList snapshot={snapshot} />
        <QueryHistory snapshot={snapshot} restore={setSql} />
      </aside>
      <div className="sql-main">
        <section className="sql-local-banner">
          <span className="sql-local-icon">◎</span>
          <div>
            <strong>Browser-local database</strong>
            <p>Saved in IndexedDB for this backend only. Nothing is sent to the Agent Server.</p>
          </div>
          <code data-testid="database-namespace">{snapshot.namespace}</code>
        </section>

        <section className="sql-editor-panel" aria-labelledby="editor-title">
          <div className="sql-panel-heading">
            <div><span className="sql-kicker">QUERY 01</span><h1 id="editor-title">SQL editor</h1></div>
            <div className="sql-toolbar">
              <button className="sql-button" type="button" onClick={() => void seed()} disabled={busy !== null}>Seed data</button>
              <button className="sql-button" type="button" onClick={() => void exportDatabase()} disabled={busy !== null}>Export</button>
              <button className="sql-button sql-button--danger" type="button" onClick={() => setConfirmReset(true)} disabled={busy !== null}>Reset</button>
            </div>
          </div>
          <div className="sql-editor">
            <div className="sql-line-numbers" aria-hidden="true">
              {sql.split("\n").map((_, index) => <span key={index}>{index + 1}</span>)}
            </div>
            <textarea
              aria-label="SQL query"
              spellCheck={false}
              value={sql}
              onChange={(event) => setSql(event.target.value)}
              onKeyDown={onEditorKeyDown}
            />
          </div>
          <div className="sql-editor-footer">
            <span>SQLite · Cmd/Ctrl + Enter to run</span>
            {busy === "query" ? (
              <button className="sql-button sql-button--cancel" type="button" onClick={() => activeRequest.current?.abort()}>Cancel query</button>
            ) : (
              <button className="sql-button sql-button--primary" data-testid="run-query" type="button" onClick={() => void runQuery()} disabled={busy !== null}>
                <span aria-hidden="true">▶</span> Run query
              </button>
            )}
          </div>
        </section>

        {confirmReset ? (
          <section className="sql-reset-confirm" role="alertdialog" aria-labelledby="reset-title">
            <div><strong id="reset-title">Reset this backend’s database?</strong><p>All tables, rows, and query history in this namespace will be deleted.</p></div>
            <div><button className="sql-button" type="button" onClick={() => setConfirmReset(false)}>Keep data</button><button className="sql-button sql-button--danger-solid" data-testid="confirm-reset" type="button" onClick={() => void resetDatabase()}>Reset database</button></div>
          </section>
        ) : null}
        {error ? <div className="sql-message sql-message--error" role="alert"><strong>SQLite error</strong><span>{error}</span></div> : null}
        {notice ? <div className="sql-message sql-message--success" role="status"><span>✓</span>{notice}</div> : null}

        <section className="sql-results-panel" aria-labelledby="results-title">
          <div className="sql-panel-heading"><div><span className="sql-kicker">OUTPUT</span><h2 id="results-title">Results</h2></div></div>
          <ResultsGrid response={response} />
        </section>
      </div>
    </main>
  );
}

function About({ host, namespace }: { host: CanvasHost; namespace: string }) {
  return (
    <main className="sql-about">
      <p className="sql-eyebrow">Under the workbench</p>
      <h1>A real database, folded into one file.</h1>
      <p className="sql-about-lede">Browser SQL Lab bundles React, an inline Worker, the SQL.js engine, SQLite WASM, a SQL migration, and seed JSON into one Blob-safe <code>extension.js</code>.</p>
      <div className="sql-about-grid">
        <article><span>01</span><h2>Off-thread SQL</h2><p>Database initialization and queries execute in a dedicated inline Worker so Canvas stays interactive.</p></article>
        <article><span>02</span><h2>Scoped persistence</h2><p>SQLite bytes are serialized to IndexedDB under <code>{namespace}</code>, derived from backend <code>{host.backend.id ?? "unavailable"}</code>.</p></article>
        <article><span>03</span><h2>Lifecycle-safe</h2><p>RPC errors cross the Worker boundary, aborted requests ignore late results, and App cleanup terminates the Worker.</p></article>
      </div>
      <section className="sql-about-note"><strong>No Agent Server dependency</strong><p>This App makes no backend requests, installs no prerequisites, and loads no CDN or sibling runtime assets.</p></section>
    </main>
  );
}

export function App({ host, path, navigate, signal, client }: AppProps) {
  const route = normalizeRoute(path);
  const namespace = makeDatabaseNamespace(host.backend?.id);
  const [snapshot, setSnapshot] = useState<DatabaseSnapshot | null>(null);
  const [startupError, setStartupError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    setSnapshot(null);
    setStartupError("");
    client.initialize(namespace, signal).then(setSnapshot).catch((error: unknown) => {
      if (!isAbort(error)) setStartupError(errorMessage(error));
    });
  }, [attempt, client, namespace, signal]);

  const go = (next: "lab" | "about") => navigate(next === "lab" ? ROOT_ROUTE : `${ROOT_ROUTE}/${next}`);

  return (
    <section className="browser-sql-lab" aria-label="Browser SQL Lab App">
      <header className="sql-header">
        <button className="sql-brand" type="button" onClick={() => go("lab")} aria-label="Open Browser SQL Lab">
          <span className="sql-logo" aria-hidden="true"><i /><i /><i /></span>
          <span><small>CANVAS APP</small><strong>Browser SQL Lab</strong></span>
        </button>
        <nav aria-label="Browser SQL Lab pages">
          <button type="button" aria-current={route === "lab" ? "page" : undefined} onClick={() => go("lab")}>Workbench</button>
          <button type="button" aria-current={route === "about" ? "page" : undefined} onClick={() => go("about")}>About</button>
        </nav>
        <div className="sql-engine-badge"><span />SQLite WASM</div>
      </header>
      {route === "not-found" ? (
        <main className="sql-state"><p className="sql-eyebrow">Unknown route</p><h1>This view is not part of Browser SQL Lab.</h1><button className="sql-button sql-button--primary" type="button" onClick={() => go("lab")}>Return to workbench</button></main>
      ) : startupError ? (
        <ErrorState message={startupError} retry={() => setAttempt((value) => value + 1)} />
      ) : !snapshot ? (
        <LoadingState namespace={namespace} />
      ) : route === "about" ? (
        <About host={host} namespace={namespace} />
      ) : (
        <Lab client={client} snapshot={snapshot} setSnapshot={setSnapshot} signal={signal} />
      )}
      <footer className="sql-footer"><span>Data stays in this browser</span><span>{host.backend?.kind ?? "unknown"} · {host.backend?.id ?? "backend unavailable"}</span></footer>
    </section>
  );
}
