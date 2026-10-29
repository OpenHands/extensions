import { useCallback, useEffect, useMemo, useState } from "react";
import {
  INSTALL_COMMANDS,
  SETUP_PROMPT,
  installGit,
  installerExplanation,
  listWorkspaces,
  loadCommitDetail,
  loadFileDiff,
  loadRepository,
  pathToken,
  probePrerequisites,
} from "./git-service";
import { loadPreferences, savePreferences, type CockpitTab } from "./preferences";
import type {
  CanvasHost,
  ChangedFile,
  CommitInfo,
  PrerequisiteStatus,
  RepositorySnapshot,
  WorkspaceCandidate,
} from "./types";

export const ROOT_ROUTE = "/extensions/git-cockpit/cockpit";

type Route =
  | { view: "picker" }
  | { view: "workspace"; token: string; detail: null }
  | { view: "workspace"; token: string; detail: { kind: "file"; value: string } | { kind: "commit"; value: string } }
  | { view: "about" }
  | { view: "not-found" };

interface AppProps {
  host: CanvasHost;
  path: string;
  navigate: (path: string) => void;
  signal: AbortSignal;
}

const PLANNED_OPERATIONS = [
  ["Stage / unstage", "Choose individual paths and review the exact index change before confirming."],
  ["Create / switch branch", "Validate ref names and protect worktrees before any branch transition."],
  ["Commit", "Preview the staged patch and commit message, then require explicit confirmation."],
  ["Stash", "Show included changes and untracked-file policy before creating or applying a stash."],
  ["Fetch / pull / push", "Display remotes, refs, and divergence before any network or credential action."],
  ["Revert / reset recovery", "Explain affected commits and files, offer recoverable choices, and add high-friction confirmation."],
] as const;

export function normalizeRoute(path: string): Route {
  const segments = path.replace(/^\/+|\/+$/g, "").split("/").filter(Boolean);
  if (segments.length === 0 || (segments.length === 1 && segments[0] === "cockpit")) return { view: "picker" };
  if (segments.length === 1 && segments[0] === "about") return { view: "about" };
  if (segments[0] === "workspace" && /^[A-Za-z0-9_-]+$/.test(segments[1] ?? "")) {
    if (segments.length === 2) return { view: "workspace", token: segments[1], detail: null };
    if (segments.length === 4 && segments[2] === "file" && /^[A-Za-z0-9_-]+$/.test(segments[3])) {
      return { view: "workspace", token: segments[1], detail: { kind: "file", value: segments[3] } };
    }
    if (segments.length === 4 && segments[2] === "commit" && /^[0-9a-f]{40}$/.test(segments[3])) {
      return { view: "workspace", token: segments[1], detail: { kind: "commit", value: segments[3] } };
    }
  }
  return { view: "not-found" };
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function linkedController(parent: AbortSignal): AbortController {
  const controller = new AbortController();
  if (parent.aborted) controller.abort();
  else parent.addEventListener("abort", () => controller.abort(), { once: true, signal: controller.signal });
  return controller;
}

function shortHash(hash: string | null): string {
  return hash?.slice(0, 8) ?? "unborn";
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value || "Unknown date" : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function statusLabel(file: ChangedFile): string {
  if (file.kind === "untracked") return "untracked";
  const labels: string[] = [];
  if (file.index !== ".") labels.push(`index ${file.index}`);
  if (file.worktree !== ".") labels.push(`worktree ${file.worktree}`);
  return labels.join(" · ") || "clean";
}

function Nav({ route, navigate }: { route: Route; navigate: (path: string) => void }) {
  return (
    <nav className="gc-nav" aria-label="Git Cockpit sections">
      <button type="button" className={route.view !== "about" ? "is-active" : ""} onClick={() => navigate(ROOT_ROUTE)}>Cockpit</button>
      <button type="button" className={route.view === "about" ? "is-active" : ""} onClick={() => navigate(`${ROOT_ROUTE}/about`)}>Safety model</button>
    </nav>
  );
}

function Shell({ route, navigate, children }: { route: Route; navigate: (path: string) => void; children: React.ReactNode }) {
  return (
    <div className="gc-shell">
      <header className="gc-header">
        <button className="gc-wordmark" type="button" onClick={() => navigate(ROOT_ROUTE)} aria-label="Git Cockpit home">
          <span aria-hidden="true">⌁</span><strong>GIT</strong><b>/</b>COCKPIT
        </button>
        <Nav route={route} navigate={navigate} />
        <span className="gc-readonly"><i /> Read-only</span>
      </header>
      {children}
    </div>
  );
}

function PlannedOperations() {
  return (
    <section className="gc-planned" aria-labelledby="planned-title">
      <div className="gc-planned-heading">
        <div><p className="gc-eyebrow">Roadmap preview · unavailable</p><h2 id="planned-title">Planned write operations</h2></div>
        <span>0 commands enabled</span>
      </div>
      <p className="gc-planned-intro">These controls are intentionally disabled and non-functional in this read-only release. A later App revision must add explicit confirmation and carefully scoped safety checks before any of them can reach the Agent Server.</p>
      <div className="gc-planned-grid">
        {PLANNED_OPERATIONS.map(([label, explanation], index) => (
          <div className="gc-planned-item" key={label}>
            <button type="button" disabled data-testid="planned-write-operation" aria-describedby={`planned-${index}`}>{label}<span>Planned</span></button>
            <p id={`planned-${index}`}>{explanation} <strong>Not available yet.</strong></p>
          </div>
        ))}
      </div>
    </section>
  );
}

function WorkspacePicker({
  workspaces,
  state,
  error,
  remembered,
  onSelect,
}: {
  workspaces: WorkspaceCandidate[];
  state: "loading" | "ready" | "error";
  error: string;
  remembered: string | null;
  onSelect: (token: string) => void;
}) {
  const initial = workspaces.some((workspace) => workspace.token === remembered) ? remembered ?? "" : "";
  return (
    <main className="gc-picker">
      <div className="gc-hero-grid">
        <section className="gc-hero-copy">
          <p className="gc-eyebrow">Repository instruments · Agent Server</p>
          <h1>See the whole worktree.<br /><em>Touch nothing.</em></h1>
          <p>Git Cockpit turns fixed, read-only Git commands into a focused view of changes, branches, history, file diffs, and commit detail.</p>
          <div className="gc-boundary-note"><span>!</span><p>Commands execute on the active Agent Server machine, inside the workspace you select. No repository data is sent to a third party.</p></div>
        </section>
        <section className="gc-picker-card" aria-labelledby="workspace-heading">
          <span className="gc-card-index">01 / CONNECT</span>
          <h2 id="workspace-heading">Select a workspace</h2>
          <p>Only directories reported by the active Agent Server are eligible.</p>
          {state === "loading" ? <div className="gc-loading"><i /> Discovering workspaces…</div> : null}
          {state === "error" ? <div className="gc-error"><strong>Workspace discovery failed</strong><span>{error}</span></div> : null}
          {state === "ready" ? (
            <>
              <label htmlFor="gc-workspace">Agent Server workspace</label>
              <select id="gc-workspace" value={initial} onChange={(event) => event.target.value && onSelect(event.target.value)}>
                <option value="">Choose a repository…</option>
                {workspaces.map((workspace) => <option value={workspace.token} key={workspace.path}>{workspace.name} — {workspace.path}</option>)}
              </select>
              {workspaces.length === 0 ? <p className="gc-empty">No workspace directories were reported by this backend.</p> : null}
            </>
          ) : null}
          <div className="gc-probe-list"><span>Next, Git Cockpit will:</span><ol><li>Probe for Git</li><li>Validate the worktree</li><li>Load read-only signals</li></ol></div>
        </section>
      </div>
      <PlannedOperations />
    </main>
  );
}

function PrerequisitePanel({
  workspace,
  status,
  state,
  error,
  acknowledged,
  setAcknowledged,
  installState,
  installError,
  onInstall,
  onRecheck,
  onCopy,
  copyNotice,
}: {
  workspace: WorkspaceCandidate;
  status: PrerequisiteStatus | null;
  state: "loading" | "ready" | "error";
  error: string;
  acknowledged: boolean;
  setAcknowledged: (value: boolean) => void;
  installState: "idle" | "installing";
  installError: string;
  onInstall: () => void;
  onRecheck: () => void;
  onCopy: () => void;
  copyNotice: string;
}) {
  return (
    <main className="gc-onboarding">
      <p className="gc-eyebrow">Prerequisite gate</p>
      <h1>Checking the flight deck.</h1>
      <p className="gc-onboarding-lede">The probe is non-mutating and runs in <code>{workspace.path}</code> on the Agent Server.</p>
      {state === "loading" ? <div className="gc-loading gc-loading--large"><i /> Probing Git and worktree capabilities…</div> : null}
      {state === "error" ? <div className="gc-error"><strong>Prerequisite probe failed</strong><span>{error}</span><button type="button" onClick={onRecheck}>Recheck</button></div> : null}
      {state === "ready" && status ? (
        <section className="gc-gate-card">
          <div className={`gc-gate-status ${status.git ? "is-ready" : "is-missing"}`}><span>Git CLI</span><strong>{status.git ? status.gitVersion : "Missing"}</strong></div>
          <div className={`gc-gate-status ${status.worktree ? "is-ready" : "is-missing"}`}><span>Selected directory</span><strong>{status.worktree ? "Git worktree" : status.git ? "Not a Git worktree" : "Pending Git"}</strong></div>
          {!status.git ? (
            <div className="gc-install-panel">
              <p className="gc-eyebrow">Setup required</p>
              <h2>Install Git deliberately</h2>
              {status.installer ? <p>Detected package manager: <strong>{status.installer}</strong>. {installerExplanation(status.installer)}</p> : <p>No supported package manager was detected. Use the fixed OpenHands-agent prompt below.</p>}
              {status.installer ? <pre>{INSTALL_COMMANDS[status.installer]}</pre> : null}
              {status.installer && status.installSupported ? (
                <>
                  <label className="gc-confirm"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} /> I understand this changes software on the Agent Server machine.</label>
                  <button className="gc-button gc-button--danger" type="button" disabled={!acknowledged || installState === "installing"} onClick={onInstall}>{installState === "installing" ? "Installing Git…" : `Install Git with ${status.installer}`}</button>
                </>
              ) : <p className="gc-not-supported">Automatic install is unavailable because the package manager is unsupported or non-interactive privileges are unavailable.</p>}
              {installError ? <div className="gc-error"><strong>Git installation failed</strong><span>{installError}</span></div> : null}
              <div className="gc-setup-actions"><button className="gc-button" type="button" onClick={onCopy}>Copy agent setup prompt</button><button className="gc-button gc-button--quiet" type="button" onClick={onRecheck}>Recheck Git</button></div>
              {copyNotice ? <p role="status" className="gc-notice">{copyNotice}</p> : null}
            </div>
          ) : !status.worktree ? (
            <div className="gc-error"><strong>This workspace is not a Git worktree</strong><span>Choose a directory with a .git worktree, then run the probe again.</span><button type="button" onClick={onRecheck}>Recheck</button></div>
          ) : <div className="gc-loading"><i /> Git is ready. Loading repository signals…</div>}
        </section>
      ) : null}
    </main>
  );
}

function SummaryStrip({ snapshot }: { snapshot: RepositorySnapshot }) {
  const additions = snapshot.diffStats.reduce((sum, stat) => sum + (stat.additions ?? 0), 0);
  const deletions = snapshot.diffStats.reduce((sum, stat) => sum + (stat.deletions ?? 0), 0);
  return (
    <div className="gc-summary-strip">
      <div><span>HEAD</span><strong>{shortHash(snapshot.status.oid)}</strong></div>
      <div><span>Changed files</span><strong>{snapshot.status.files.length}</strong></div>
      <div><span>Diff</span><strong className="gc-delta"><i>+{additions}</i> <b>−{deletions}</b></strong></div>
      <div><span>Upstream</span><strong>{snapshot.status.upstream ?? "not set"}</strong></div>
    </div>
  );
}

function ChangesView({ snapshot, onFile }: { snapshot: RepositorySnapshot; onFile: (file: ChangedFile) => void }) {
  const statFor = (file: ChangedFile) => snapshot.diffStats.filter((stat) => stat.path === file.path);
  return (
    <section className="gc-panel" aria-labelledby="changes-title">
      <div className="gc-panel-heading"><div><p className="gc-eyebrow">Working tree</p><h2 id="changes-title">Changed files</h2></div><span>{snapshot.status.files.length} visible</span></div>
      {snapshot.status.files.length === 0 ? <div className="gc-empty-state"><strong>Working tree clean</strong><p>No staged, unstaged, or untracked paths were reported.</p></div> : (
        <div className="gc-file-list">
          {snapshot.status.files.map((file) => {
            const stats = statFor(file);
            const additions = stats.reduce((sum, stat) => sum + (stat.additions ?? 0), 0);
            const deletions = stats.reduce((sum, stat) => sum + (stat.deletions ?? 0), 0);
            return (
              <button type="button" key={`${file.kind}-${file.path}`} onClick={() => onFile(file)}>
                <span className={`gc-status-code gc-status-code--${file.kind}`}>{file.kind === "untracked" ? "?" : `${file.index}${file.worktree}`.replaceAll(".", "·")}</span>
                <span className="gc-file-main"><strong>{file.path}</strong><small>{file.originalPath ? `renamed from ${file.originalPath} · ` : ""}{statusLabel(file)}</small></span>
                {stats.length ? <span className="gc-file-stat"><i>+{additions}</i><b>−{deletions}</b></span> : <span className="gc-file-stat gc-file-stat--empty">{file.kind === "untracked" ? "not in diff" : "binary / mode"}</span>}
                <span aria-hidden="true">→</span>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}

function HistoryView({ commits, onCommit }: { commits: CommitInfo[]; onCommit: (commit: CommitInfo) => void }) {
  return (
    <section className="gc-panel" aria-labelledby="history-title">
      <div className="gc-panel-heading"><div><p className="gc-eyebrow">Latest 30</p><h2 id="history-title">Commit history</h2></div><span>{commits.length} commits</span></div>
      {commits.length === 0 ? <div className="gc-empty-state"><strong>No commits yet</strong><p>This may be an unborn repository.</p></div> : (
        <div className="gc-commit-list">{commits.map((commit) => (
          <button type="button" key={commit.hash} onClick={() => onCommit(commit)}>
            <span className="gc-graph-dot" />
            <span className="gc-commit-main"><strong>{commit.subject || "(no subject)"}</strong><small>{commit.author} · {formatDate(commit.authoredAt)}</small></span>
            <code>{shortHash(commit.hash)}</code><span aria-hidden="true">→</span>
          </button>
        ))}</div>
      )}
    </section>
  );
}

function BranchesView({ snapshot }: { snapshot: RepositorySnapshot }) {
  return (
    <section className="gc-panel" aria-labelledby="branches-title">
      <div className="gc-panel-heading"><div><p className="gc-eyebrow">Local + remote</p><h2 id="branches-title">Branches</h2></div><span>{snapshot.branches.length} refs</span></div>
      <div className="gc-branch-list">{snapshot.branches.map((branch) => (
        <div className={branch.current ? "is-current" : ""} key={`${branch.name}-${branch.hash}`}>
          <span className="gc-branch-mark">{branch.current ? "●" : "○"}</span><strong>{branch.name}</strong><code>{shortHash(branch.hash)}</code><small>{formatDate(branch.committedAt)}</small>
        </div>
      ))}</div>
      {snapshot.branches.length === 0 ? <div className="gc-empty-state"><strong>No branches reported</strong></div> : null}
    </section>
  );
}

function DetailPanel({ route, snapshot, state, content, error, onBack }: { route: Extract<Route, { view: "workspace" }>; snapshot: RepositorySnapshot; state: "idle" | "loading" | "ready" | "error"; content: string; error: string; onBack: () => void }) {
  const file = route.detail?.kind === "file" ? snapshot.status.files.find((entry) => pathToken(entry.path) === route.detail?.value) : null;
  const commit = route.detail?.kind === "commit" ? snapshot.commits.find((entry) => entry.hash === route.detail?.value) : null;
  const title = file?.path ?? commit?.subject ?? "Detail unavailable";
  return (
    <section className="gc-detail">
      <button className="gc-back" type="button" onClick={onBack}>← Back to repository</button>
      <div className="gc-detail-heading"><p className="gc-eyebrow">{file ? "Individual file diff" : "Commit detail"}</p><h2>{title}</h2>{commit ? <p>{commit.author} &lt;{commit.email}&gt; · {formatDate(commit.authoredAt)} · <code>{commit.hash}</code></p> : null}</div>
      {state === "loading" ? <div className="gc-loading"><i /> Loading fixed read-only detail…</div> : null}
      {state === "error" ? <div className="gc-error"><strong>Could not load detail</strong><span>{error}</span></div> : null}
      {state === "ready" ? <pre className="gc-diff" data-testid="detail-output">{content || "No textual diff or detail was returned."}</pre> : null}
    </section>
  );
}

function Dashboard({ workspace, snapshot, tab, setTab, route, navigate, onRefresh, refreshState, detailState, detailContent, detailError }: {
  workspace: WorkspaceCandidate;
  snapshot: RepositorySnapshot;
  tab: CockpitTab;
  setTab: (tab: CockpitTab) => void;
  route: Extract<Route, { view: "workspace" }>;
  navigate: (path: string) => void;
  onRefresh: () => void;
  refreshState: "idle" | "loading" | "ready" | "error";
  detailState: "idle" | "loading" | "ready" | "error";
  detailContent: string;
  detailError: string;
}) {
  const base = `${ROOT_ROUTE}/workspace/${workspace.token}`;
  if (route.detail) return <main className="gc-dashboard"><DetailPanel route={route} snapshot={snapshot} state={detailState} content={detailContent} error={detailError} onBack={() => navigate(base)} /></main>;
  return (
    <main className="gc-dashboard">
      <section className="gc-repo-heading">
        <div><p className="gc-eyebrow">Connected worktree</p><h1>{workspace.name}</h1><p><code>{workspace.path}</code></p></div>
        <div className="gc-repo-actions"><span className="gc-branch-chip">⑂ {snapshot.status.branch ?? "detached HEAD"}</span><button className="gc-button gc-button--quiet" type="button" disabled={refreshState === "loading"} onClick={onRefresh}>{refreshState === "loading" ? "Refreshing…" : "Refresh signals"}</button></div>
      </section>
      <SummaryStrip snapshot={snapshot} />
      <div className="gc-tab-bar" role="tablist" aria-label="Repository views">
        {(["changes", "history", "branches"] as CockpitTab[]).map((next) => <button role="tab" aria-selected={tab === next} className={tab === next ? "is-active" : ""} type="button" key={next} onClick={() => setTab(next)}>{next}</button>)}
      </div>
      {tab === "changes" ? <ChangesView snapshot={snapshot} onFile={(file) => navigate(`${base}/file/${pathToken(file.path)}`)} /> : null}
      {tab === "history" ? <HistoryView commits={snapshot.commits} onCommit={(commit) => navigate(`${base}/commit/${commit.hash}`)} /> : null}
      {tab === "branches" ? <BranchesView snapshot={snapshot} /> : null}
      <PlannedOperations />
    </main>
  );
}

function About({ navigate }: { navigate: (path: string) => void }) {
  return (
    <main className="gc-about">
      <p className="gc-eyebrow">Safety model</p><h1>A glass cockpit, not a terminal.</h1>
      <p className="gc-about-lede">Git Cockpit exposes a narrow instrument panel over the active Agent Server. Every active repository operation maps to a reviewed, read-only Git command template.</p>
      <div className="gc-safety-grid">
        <article><span>01</span><h2>Controlled commands</h2><p>No arbitrary command field exists. Workspaces stay in the structured <code>cwd</code> field; file paths are validated, base64 encoded, decoded into a quoted variable, and passed after <code>--</code>; commit IDs must be full hexadecimal hashes already returned by the log.</p></article>
        <article><span>02</span><h2>Machine boundary</h2><p>Commands execute on the Agent Server machine. Only harmless view preferences are stored in the browser, scoped to that backend. The App creates no repository files, service, or backend data directory.</p></article>
        <article><span>03</span><h2>Future writes</h2><p>Write-capable controls are visual roadmap placeholders only. A later revision must add command-specific validation, previews, recoverability, and explicit confirmation.</p></article>
      </div>
      <button className="gc-button" type="button" onClick={() => navigate(ROOT_ROUTE)}>Choose a workspace</button>
    </main>
  );
}

export function App({ host, path, navigate, signal }: AppProps) {
  const route = useMemo(() => normalizeRoute(path), [path]);
  const [preferences, setPreferences] = useState(() => loadPreferences(host.backend));
  const [workspaces, setWorkspaces] = useState<WorkspaceCandidate[]>([]);
  const [workspaceState, setWorkspaceState] = useState<"loading" | "ready" | "error">("loading");
  const [workspaceError, setWorkspaceError] = useState("");
  const [probe, setProbe] = useState<PrerequisiteStatus | null>(null);
  const [probeState, setProbeState] = useState<"loading" | "ready" | "error">("loading");
  const [probeError, setProbeError] = useState("");
  const [snapshot, setSnapshot] = useState<RepositorySnapshot | null>(null);
  const [repositoryState, setRepositoryState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [repositoryError, setRepositoryError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [installAcknowledged, setInstallAcknowledged] = useState(false);
  const [installState, setInstallState] = useState<"idle" | "installing">("idle");
  const [installError, setInstallError] = useState("");
  const [copyNotice, setCopyNotice] = useState("");
  const [detailState, setDetailState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [detailContent, setDetailContent] = useState("");
  const [detailError, setDetailError] = useState("");

  const selected = route.view === "workspace" ? workspaces.find((workspace) => workspace.token === route.token) ?? null : null;

  const remember = useCallback((next: Partial<{ workspaceToken: string | null; tab: CockpitTab }>) => {
    setPreferences((current) => {
      const value = { ...current, ...next };
      savePreferences(host.backend, value);
      return value;
    });
  }, [host.backend]);

  useEffect(() => {
    const controller = linkedController(signal);
    setWorkspaceState("loading");
    listWorkspaces(host, controller.signal).then((next) => {
      setWorkspaces(next); setWorkspaceState("ready");
    }).catch((error: unknown) => {
      if (!isAbort(error)) { setWorkspaceError(errorMessage(error)); setWorkspaceState("error"); }
    });
    return () => controller.abort();
  }, [host, signal]);

  useEffect(() => {
    if (!selected) return;
    const controller = linkedController(signal);
    setProbe(null); setProbeError(""); setProbeState("loading"); setSnapshot(null); setRepositoryState("idle");
    probePrerequisites(host, selected, controller.signal).then((next) => {
      setProbe(next); setProbeState("ready");
    }).catch((error: unknown) => {
      if (!isAbort(error)) { setProbeError(errorMessage(error)); setProbeState("error"); }
    });
    return () => controller.abort();
  }, [host, refreshKey, selected, signal]);

  useEffect(() => {
    if (!selected || !probe?.git || !probe.worktree) return;
    const controller = linkedController(signal);
    setRepositoryState("loading"); setRepositoryError(""); setSnapshot(null);
    loadRepository(host, selected, controller.signal).then((next) => {
      setSnapshot(next); setRepositoryState("ready");
    }).catch((error: unknown) => {
      if (!isAbort(error)) { setRepositoryError(errorMessage(error)); setRepositoryState("error"); }
    });
    return () => controller.abort();
  }, [host, probe, selected, signal]);

  useEffect(() => {
    if (route.view !== "workspace" || !route.detail || !selected || !snapshot) { setDetailState("idle"); setDetailContent(""); return; }
    const controller = linkedController(signal);
    const run = async () => {
      setDetailState("loading"); setDetailContent(""); setDetailError("");
      try {
        if (route.detail?.kind === "file") {
          const file = snapshot.status.files.find((entry) => pathToken(entry.path) === route.detail?.value);
          if (!file) throw new Error("That changed file is not present in the current repository status.");
          if (file.kind === "untracked") {
            setDetailContent("Untracked files have no Git diff until they are staged. Staging is not available in this read-only release.");
          } else setDetailContent(await loadFileDiff(host, selected, file.path, controller.signal));
        } else {
          const commit = snapshot.commits.find((entry) => entry.hash === route.detail?.value);
          if (!commit) throw new Error("That commit is not present in the bounded recent history.");
          setDetailContent(await loadCommitDetail(host, selected, commit.hash, controller.signal));
        }
        setDetailState("ready");
      } catch (error) {
        if (!isAbort(error)) { setDetailError(errorMessage(error)); setDetailState("error"); }
      }
    };
    void run();
    return () => controller.abort();
  }, [host, route, selected, signal, snapshot]);

  const doInstall = useCallback(async () => {
    if (!selected || !probe || !installAcknowledged) return;
    const controller = linkedController(signal);
    setInstallState("installing"); setInstallError("");
    try {
      await installGit(host, selected, probe, controller.signal);
      setInstallAcknowledged(false); setRefreshKey((value) => value + 1);
    } catch (error) {
      if (!isAbort(error)) setInstallError(errorMessage(error));
    } finally {
      setInstallState("idle"); controller.abort();
    }
  }, [host, installAcknowledged, probe, selected, signal]);

  const copySetup = useCallback(async () => {
    try { await navigator.clipboard.writeText(SETUP_PROMPT); setCopyNotice("Setup prompt copied."); }
    catch { setCopyNotice("Clipboard access was unavailable. Copy the prompt from the README instead."); }
  }, []);

  let content: React.ReactNode;
  if (route.view === "about") content = <About navigate={navigate} />;
  else if (route.view === "not-found") content = <main className="gc-not-found"><p className="gc-eyebrow">404 / route</p><h1>Instrument not found.</h1><button className="gc-button" type="button" onClick={() => navigate(ROOT_ROUTE)}>Return to cockpit</button></main>;
  else if (route.view === "picker") content = <WorkspacePicker workspaces={workspaces} state={workspaceState} error={workspaceError} remembered={preferences.workspaceToken} onSelect={(token) => { remember({ workspaceToken: token }); navigate(`${ROOT_ROUTE}/workspace/${token}`); }} />;
  else if (workspaceState === "ready" && !selected) content = <main className="gc-not-found"><p className="gc-eyebrow">Workspace unavailable</p><h1>This backend did not report that workspace.</h1><button className="gc-button" type="button" onClick={() => navigate(ROOT_ROUTE)}>Choose another workspace</button></main>;
  else if (!selected) content = <main className="gc-onboarding"><div className="gc-loading gc-loading--large"><i /> Resolving selected workspace…</div></main>;
  else if (!probe?.git || !probe.worktree || probeState !== "ready") content = <PrerequisitePanel workspace={selected} status={probe} state={probeState} error={probeError} acknowledged={installAcknowledged} setAcknowledged={setInstallAcknowledged} installState={installState} installError={installError} onInstall={() => void doInstall()} onRecheck={() => setRefreshKey((value) => value + 1)} onCopy={() => void copySetup()} copyNotice={copyNotice} />;
  else if (repositoryState === "error") content = <main className="gc-onboarding"><div className="gc-error"><strong>Repository signals failed</strong><span>{repositoryError}</span><button type="button" onClick={() => setRefreshKey((value) => value + 1)}>Retry</button></div></main>;
  else if (!snapshot || repositoryState === "loading") content = <main className="gc-onboarding"><div className="gc-loading gc-loading--large"><i /> Reading status, branches, commits, and diff summary…</div></main>;
  else content = <Dashboard workspace={selected} snapshot={snapshot} tab={preferences.tab} setTab={(tab) => remember({ tab })} route={route} navigate={navigate} onRefresh={() => setRefreshKey((value) => value + 1)} refreshState={repositoryState} detailState={detailState} detailContent={detailContent} detailError={detailError} />;

  return <Shell route={route} navigate={navigate}>{content}</Shell>;
}
