import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnalysisClient } from "./analysis-client";
import {
  gatherRepositorySnapshot,
  listWorkspaces,
  probePrerequisites,
  SETUP_PROMPT,
} from "./repository-service";
import type {
  CanvasHost,
  DependencyMetric,
  FileMetric,
  PrerequisiteStatus,
  RankedMetric,
  RepositoryAnalysis,
  WorkspaceCandidate,
} from "./types";

export const ROOT_ROUTE = "/extensions/wasm-repo-lens/repo-lens";

type Route =
  | { view: "lens"; token: string | null }
  | { view: "about" }
  | { view: "not-found" };

interface AppProps {
  host: CanvasHost;
  path: string;
  navigate: (path: string) => void;
  signal: AbortSignal;
  client: AnalysisClient;
}

export function normalizeRoute(path: string): Route {
  const segments = path.replace(/^\/+|\/+$/g, "").split("/").filter(Boolean);
  if (segments.length === 0 || segments[0] === "lens") return { view: "lens", token: null };
  if (segments[0] === "workspace" && segments.length === 2 && /^[A-Za-z0-9_-]+$/.test(segments[1])) {
    return { view: "lens", token: segments[1] };
  }
  if (segments[0] === "about" && segments.length === 1) return { view: "about" };
  return { view: "not-found" };
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
}

function Nav({ route, navigate }: { route: Route; navigate: (path: string) => void }) {
  return (
    <nav className="lens-nav" aria-label="Repo Lens sections">
      <button className={route.view === "lens" ? "is-active" : ""} type="button" onClick={() => navigate(ROOT_ROUTE)}>
        Analysis
      </button>
      <button className={route.view === "about" ? "is-active" : ""} type="button" onClick={() => navigate(`${ROOT_ROUTE}/about`)}>
        Data boundary
      </button>
    </nav>
  );
}

const RankedBars = memo(function RankedBars({ items, empty }: { items: RankedMetric[]; empty: string }) {
  if (items.length === 0) return <p className="lens-empty-copy">{empty}</p>;
  return (
    <div className="lens-ranked-bars">
      {items.slice(0, 12).map((item, index) => (
        <div className="lens-ranked-row" key={item.name}>
          <span className="lens-rank">{String(index + 1).padStart(2, "0")}</span>
          <div className="lens-rank-main">
            <div><strong>{item.name}</strong><span>{item.files.toLocaleString()} files · {formatBytes(item.bytes)}</span></div>
            <div className="lens-bar"><span style={{ width: `${Math.max(1.5, item.percent)}%` }} /></div>
          </div>
          <span className="lens-percent">{item.percent.toFixed(1)}%</span>
        </div>
      ))}
    </div>
  );
});

function FileTable({ files, mode }: { files: FileMetric[]; mode: "size" | "churn" }) {
  if (files.length === 0) {
    return <p className="lens-empty-copy">{mode === "size" ? "No files were returned." : "No commit history was available."}</p>;
  }
  return (
    <div className="lens-file-list">
      {files.map((file, index) => (
        <div className="lens-file-row" key={file.path}>
          <span>{String(index + 1).padStart(2, "0")}</span>
          <div><code title={file.path}>{file.path}</code><small>{file.language ?? "Other"} · {formatBytes(file.bytes)}</small></div>
          <strong>{mode === "churn" ? `${file.changes ?? 0} touches` : formatBytes(file.bytes)}</strong>
        </div>
      ))}
    </div>
  );
}

function ReferenceList({ items, empty }: { items: DependencyMetric[]; empty: string }) {
  if (items.length === 0) return <p className="lens-empty-copy">{empty}</p>;
  return (
    <div className="lens-reference-grid">
      {items.slice(0, 20).map((item) => (
        <div key={`${item.kind}-${item.name}`}>
          <strong>{item.name}</strong>
          <span>{item.references} {item.references === 1 ? "reference" : "references"}</span>
          <code title={item.source}>{item.source}</code>
        </div>
      ))}
    </div>
  );
}

function AnalysisDashboard({ analysis, workspace }: { analysis: RepositoryAnalysis; workspace: WorkspaceCandidate }) {
  const downloadUrls = useRef(new Set<string>());
  useEffect(() => () => {
    for (const url of downloadUrls.current) URL.revokeObjectURL(url);
    downloadUrls.current.clear();
  }, []);

  const exportAnalysis = useCallback(() => {
    const blob = new Blob([JSON.stringify({ workspace: workspace.name, analyzedAt: new Date().toISOString(), ...analysis }, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    downloadUrls.current.add(url);
    const link = document.createElement("a");
    link.href = url;
    link.download = `repo-lens-${workspace.name.replace(/[^A-Za-z0-9._-]+/g, "-")}.json`;
    link.click();
    window.setTimeout(() => {
      URL.revokeObjectURL(url);
      downloadUrls.current.delete(url);
    }, 0);
  }, [analysis, workspace.name]);

  return (
    <div className="lens-results" data-testid="analysis-dashboard">
      <div className="lens-result-heading">
        <div>
          <p className="lens-eyebrow">Browser analysis complete</p>
          <h2>{workspace.name}</h2>
          <p><code>{analysis.branch ?? "no branch"}</code> · {analysis.sourceSamples.toLocaleString()} bounded source samples · {analysis.historyEntries.toLocaleString()} history entries</p>
        </div>
        <button className="lens-button lens-button--quiet" type="button" onClick={exportAnalysis}>Export analysis JSON</button>
      </div>
      {analysis.truncated ? <div className="lens-warning">The repository exceeded the 5,000-file collection limit. Results describe the bounded snapshot.</div> : null}
      <div className="lens-metrics">
        <div><span>Files mapped</span><strong>{analysis.files.toLocaleString()}</strong></div>
        <div><span>Bytes measured</span><strong>{formatBytes(analysis.bytes)}</strong></div>
        <div><span>Languages</span><strong>{analysis.languages.length}</strong></div>
        <div><span>Dependencies</span><strong>{analysis.dependencies.length}</strong></div>
      </div>
      <div className="lens-panel-grid">
        <section className="lens-panel lens-panel--wide">
          <div className="lens-panel-title"><div><span>01</span><h3>Language distribution</h3></div><p>Measured by bytes across the repository inventory.</p></div>
          <RankedBars items={analysis.languages} empty="No language data was found." />
        </section>
        <section className="lens-panel">
          <div className="lens-panel-title"><div><span>02</span><h3>Directory map</h3></div><p>Top-level ownership by footprint.</p></div>
          <RankedBars items={analysis.directories} empty="No directories were found." />
        </section>
        <section className="lens-panel">
          <div className="lens-panel-title"><div><span>03</span><h3>Large-file hotspots</h3></div><p>Files most likely to affect clone and review cost.</p></div>
          <FileTable files={analysis.largeFiles} mode="size" />
        </section>
        <section className="lens-panel">
          <div className="lens-panel-title"><div><span>04</span><h3>Churn hotspots</h3></div><p>Most-touched paths across the latest 200 commits.</p></div>
          <FileTable files={analysis.churnHotspots} mode="churn" />
        </section>
        <section className="lens-panel">
          <div className="lens-panel-title"><div><span>05</span><h3>Declared dependencies</h3></div><p>Bounded manifest extraction by the Rust engine.</p></div>
          <ReferenceList items={analysis.dependencies} empty="No supported dependency manifests were sampled." />
        </section>
        <section className="lens-panel lens-panel--wide">
          <div className="lens-panel-title"><div><span>06</span><h3>Import summary</h3></div><p>External import roots observed in sampled source.</p></div>
          <ReferenceList items={analysis.imports} empty="No external imports were detected in sampled source." />
        </section>
      </div>
    </div>
  );
}

function About({ navigate }: { navigate: (path: string) => void }) {
  return (
    <main className="lens-about">
      <p className="lens-eyebrow">Explicit data boundary</p>
      <h1>Source crosses one boundary, once.</h1>
      <p className="lens-about-lede">WASM Repo Lens requests a bounded, read-only snapshot from the selected Agent Server workspace. That snapshot moves into your browser, where an inline Worker and embedded Rust/WASM engine perform every aggregation.</p>
      <div className="lens-boundary">
        <div><span>01</span><strong>Agent Server workspace</strong><p>Two fixed commands probe tools and read paths, sizes, bounded source samples, and recent Git path history.</p></div>
        <b aria-hidden="true">→</b>
        <div><span>02</span><strong>Inline browser Worker</strong><p>The self-contained bundle starts a Worker and its embedded WASM without a CDN or sibling assets.</p></div>
        <b aria-hidden="true">→</b>
        <div><span>03</span><strong>Rendered analysis</strong><p>Only in-memory metrics remain. The App uses no IndexedDB, localStorage, server index, or background process.</p></div>
      </div>
      <section className="lens-policy">
        <h2>What the App will not do</h2>
        <ul>
          <li>It never accepts or constructs an arbitrary shell command.</li>
          <li>It never writes to the selected repository or installs tools by itself.</li>
          <li>It never sends source to a third-party service or persists a source snapshot.</li>
          <li>Export is explicit and contains aggregate JSON, not sampled source content.</li>
        </ul>
      </section>
      <button className="lens-button lens-button--primary" type="button" onClick={() => navigate(ROOT_ROUTE)}>Choose a workspace</button>
    </main>
  );
}

export function App({ host, path, navigate, signal, client }: AppProps) {
  const route = useMemo(() => normalizeRoute(path), [path]);
  const routeKey = route.view === "lens" ? `${route.view}:${route.token ?? ""}` : route.view;
  const [workspaces, setWorkspaces] = useState<WorkspaceCandidate[]>([]);
  const [workspaceState, setWorkspaceState] = useState<"loading" | "ready" | "error">("loading");
  const [workspaceError, setWorkspaceError] = useState("");
  const [prerequisites, setPrerequisites] = useState<PrerequisiteStatus | null>(null);
  const [probeState, setProbeState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [probeError, setProbeError] = useState("");
  const [analysis, setAnalysis] = useState<RepositoryAnalysis | null>(null);
  const [analysisState, setAnalysisState] = useState<"idle" | "snapshot" | "worker" | "error">("idle");
  const [analysisError, setAnalysisError] = useState("");
  const [copyNotice, setCopyNotice] = useState("");
  const operation = useRef<AbortController | null>(null);

  const selected = route.view === "lens" && route.token
    ? workspaces.find((workspace) => workspace.token === route.token) ?? null
    : null;

  const startOperation = useCallback(() => {
    operation.current?.abort();
    const controller = new AbortController();
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", () => controller.abort(), { once: true, signal: controller.signal });
    operation.current = controller;
    return controller;
  }, [signal]);

  useEffect(() => {
    const controller = new AbortController();
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", () => controller.abort(), { once: true, signal: controller.signal });
    setWorkspaceState("loading");
    listWorkspaces(host, controller.signal).then((next) => {
      setWorkspaces(next);
      setWorkspaceState("ready");
    }).catch((error: unknown) => {
      if (!isAbort(error)) {
        setWorkspaceError(errorMessage(error));
        setWorkspaceState("error");
      }
    });
    return () => controller.abort();
  }, [host, signal]);

  useEffect(() => () => operation.current?.abort(), [routeKey]);

  const recheck = useCallback(async () => {
    if (!selected) return;
    const controller = startOperation();
    setProbeState("loading");
    setProbeError("");
    setPrerequisites(null);
    setAnalysis(null);
    setAnalysisState("idle");
    try {
      const result = await probePrerequisites(host, selected, controller.signal);
      setPrerequisites(result);
      setProbeState("ready");
    } catch (error) {
      if (!isAbort(error)) {
        setProbeError(errorMessage(error));
        setProbeState("error");
      }
    }
  }, [host, selected, startOperation]);

  useEffect(() => {
    if (selected) void recheck();
    else {
      setProbeState("idle");
      setPrerequisites(null);
      setAnalysis(null);
      setAnalysisState("idle");
    }
  }, [recheck, selected]);

  const runAnalysis = useCallback(async () => {
    if (!selected || !prerequisites?.git || !prerequisites.rg) return;
    const controller = startOperation();
    setAnalysis(null);
    setAnalysisError("");
    setAnalysisState("snapshot");
    try {
      const snapshot = await gatherRepositorySnapshot(host, selected, controller.signal);
      setAnalysisState("worker");
      const result = await client.analyze(snapshot, controller.signal);
      setAnalysis(result);
      setAnalysisState("idle");
    } catch (error) {
      if (!isAbort(error)) {
        setAnalysisError(errorMessage(error));
        setAnalysisState("error");
      }
    }
  }, [client, host, prerequisites, selected, startOperation]);

  const copySetupPrompt = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(SETUP_PROMPT);
      setCopyNotice("Setup prompt copied.");
    } catch {
      setCopyNotice("Copy unavailable. Select the prompt in the README instead.");
    }
  }, []);

  if (route.view === "about") {
    return <div className="lens-shell"><header className="lens-header"><a className="lens-brand" href="#" onClick={(event) => { event.preventDefault(); navigate(ROOT_ROUTE); }}><span>RL</span><strong>WASM Repo Lens</strong></a><Nav route={route} navigate={navigate} /></header><About navigate={navigate} /></div>;
  }

  if (route.view === "not-found") {
    return <div className="lens-shell"><main className="lens-state"><span className="lens-state-code">404</span><p className="lens-eyebrow">Unknown Repo Lens route</p><h1>This view is outside the map.</h1><button className="lens-button lens-button--primary" type="button" onClick={() => navigate(ROOT_ROUTE)}>Return to analysis</button></main></div>;
  }

  const missing = prerequisites ? [!prerequisites.git ? "git" : "", !prerequisites.rg ? "ripgrep (rg)" : ""].filter(Boolean) : [];
  const ready = prerequisites?.git && prerequisites.rg;
  const busy = analysisState === "snapshot" || analysisState === "worker";

  return (
    <div className="lens-shell">
      <header className="lens-header">
        <a className="lens-brand" href="#" onClick={(event) => { event.preventDefault(); navigate(ROOT_ROUTE); }}><span>RL</span><strong>WASM Repo Lens</strong></a>
        <Nav route={route} navigate={navigate} />
        <div className="lens-runtime"><i /> Rust/WASM · Worker</div>
      </header>
      <main>
        <section className="lens-hero">
          <div>
            <p className="lens-eyebrow">Repository intelligence, locally computed</p>
            <h1>See the shape of a codebase.</h1>
            <p>Collect a bounded read-only snapshot from your Agent Server, then map it inside the browser with a real Rust/WASM engine.</p>
          </div>
          <div className="lens-scan-mark" aria-hidden="true"><span /><span /><b>WASM</b></div>
        </section>

        <section className="lens-picker" aria-labelledby="workspace-title">
          <div><span className="lens-step">01</span><div><h2 id="workspace-title">Select an Agent Server workspace</h2><p>Only server-discovered, validated absolute paths can be selected.</p></div></div>
          {workspaceState === "loading" ? <div className="lens-inline-loading"><i /> Discovering workspaces…</div> : null}
          {workspaceState === "error" ? <div className="lens-error" role="alert"><strong>Workspace discovery failed</strong><span>{workspaceError}</span></div> : null}
          {workspaceState === "ready" ? (
            <select
              aria-label="Agent Server workspace"
              value={selected?.token ?? ""}
              onChange={(event) => navigate(event.target.value ? `${ROOT_ROUTE}/workspace/${event.target.value}` : ROOT_ROUTE)}
            >
              <option value="">Choose a workspace…</option>
              {workspaces.map((workspace) => <option value={workspace.token} key={workspace.path}>{workspace.name} — {workspace.path}</option>)}
            </select>
          ) : null}
          {workspaceState === "ready" && workspaces.length === 0 ? <p className="lens-empty-copy">No workspace directories were reported by this Agent Server.</p> : null}
        </section>

        {route.token && workspaceState === "ready" && !selected ? (
          <div className="lens-error" role="alert"><strong>Workspace is no longer available</strong><span>The route does not match the current Agent Server discovery results. Choose a workspace again.</span></div>
        ) : null}

        {selected ? (
          <section className="lens-readiness" aria-live="polite">
            <div className="lens-readiness-head"><span className="lens-step">02</span><div><h2>Read-only readiness check</h2><p><code>{selected.path}</code></p></div></div>
            {probeState === "loading" ? <div className="lens-inline-loading"><i /> Checking git and ripgrep without changing the workspace…</div> : null}
            {probeState === "error" ? <div className="lens-error" role="alert"><strong>Prerequisite probe failed</strong><span>{probeError}</span><button type="button" onClick={recheck}>Try again</button></div> : null}
            {probeState === "ready" ? (
              <>
                <div className="lens-checks">
                  <div className={prerequisites?.git ? "is-ready" : "is-missing"}><span>{prerequisites?.git ? "✓" : "!"}</span><div><strong>git</strong><small>{prerequisites?.git ? "Available for branch and churn data" : "Missing on the Agent Server"}</small></div></div>
                  <div className={prerequisites?.rg ? "is-ready" : "is-missing"}><span>{prerequisites?.rg ? "✓" : "!"}</span><div><strong>ripgrep</strong><small>{prerequisites?.rg ? "Available for bounded file discovery" : "Missing on the Agent Server"}</small></div></div>
                </div>
                {missing.length > 0 ? (
                  <div className="lens-onboarding">
                    <div><p className="lens-eyebrow">Setup is deliberate</p><h3>Install {missing.join(" and ")} through an OpenHands agent.</h3><p>This App stays read-only and will not guess your operating system or run an installer. Copy the fixed setup prompt, ask an agent to perform the install, then recheck here.</p></div>
                    <div><button className="lens-button lens-button--primary" type="button" onClick={copySetupPrompt}>Copy agent setup prompt</button><button className="lens-button lens-button--quiet" type="button" onClick={recheck}>Recheck prerequisites</button><small aria-live="polite">{copyNotice}</small></div>
                  </div>
                ) : null}
                {ready ? (
                  <div className="lens-run">
                    <div><span className="lens-step">03</span><div><h2>Analyze in the browser</h2><p>Inventory ≤5,000 files · source samples ≤250 × 4 KB · history ≤200 commits · response ≤800 KB</p></div></div>
                    <button className="lens-button lens-button--primary" data-testid="analyze" type="button" disabled={busy} onClick={runAnalysis}>{busy ? "Analysis running…" : analysis ? "Analyze again" : "Analyze repository"}</button>
                  </div>
                ) : null}
              </>
            ) : null}
          </section>
        ) : null}

        {busy ? <section className="lens-progress"><div className="lens-progress-orbit"><span /><b>W</b></div><div><p className="lens-eyebrow">{analysisState === "snapshot" ? "Reading bounded snapshot" : "Rust engine active"}</p><h2>{analysisState === "snapshot" ? "Gathering repository signals…" : "Mapping the codebase off the main thread…"}</h2><p>Changing workspace or route cancels this operation.</p></div></section> : null}
        {analysisState === "error" ? <div className="lens-error" role="alert"><strong>Analysis failed</strong><span>{analysisError}</span><button type="button" onClick={runAnalysis}>Try again</button></div> : null}
        {analysis && selected ? <AnalysisDashboard analysis={analysis} workspace={selected} /> : null}

        <aside className="lens-boundary-note">
          <span>DATA BOUNDARY</span>
          <p>Source is read from <strong>the selected Agent Server workspace</strong>. Analysis runs <strong>inside this browser</strong>. No source snapshot is persisted; explicit export contains aggregate metrics only.</p>
          <button type="button" onClick={() => navigate(`${ROOT_ROUTE}/about`)}>Inspect the boundary →</button>
        </aside>
      </main>
    </div>
  );
}
