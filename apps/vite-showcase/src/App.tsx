import { useEffect, useState } from "react";
import architectureNotes from "./architecture.md?raw";
import featureInventory from "./feature-inventory.json";
import markUrl from "./mark.svg";
import DiagnosticsWorker from "./diagnostics.worker?worker&inline";
import type { CanvasHost, WorkerResult } from "./types";

export const ROOT_ROUTE = "/extensions/vite-showcase/showcase";
export const ROUTES = ["overview", "architecture", "diagnostics"] as const;
type Route = (typeof ROUTES)[number] | "not-found";

interface AppProps {
  host: CanvasHost;
  path: string;
  navigate: (path: string) => void;
  signal: AbortSignal;
}

export function normalizeRoute(path: string): Route {
  const route = path.replace(/^\/+|\/+$/g, "").split("/")[0];
  if (route === "" || route === "overview") return "overview";
  return ROUTES.includes(route as (typeof ROUTES)[number])
    ? (route as Route)
    : "not-found";
}

function Nav({ route, go }: { route: Route; go: (route: string) => void }) {
  return (
    <nav className="vs-nav" aria-label="Showcase pages">
      {ROUTES.map((item) => (
        <button
          key={item}
          type="button"
          aria-current={route === item ? "page" : undefined}
          onClick={() => go(item)}
        >
          {item[0].toUpperCase() + item.slice(1)}
        </button>
      ))}
    </nav>
  );
}

function Overview({ go }: { go: (route: string) => void }) {
  return (
    <main>
      <section className="vs-hero">
        <div>
          <p className="vs-eyebrow">One installable artifact</p>
          <h1>
            Modern source.
            <br />
            <span className="vs-gradient">Zero loose ends.</span>
          </h1>
          <p className="vs-lede">
            A conventional {featureInventory.framework} App—TypeScript, modular CSS, assets,
            lazy code, and background work—compressed into one authenticated Canvas bundle.
          </p>
          <div className="vs-actions">
            <button className="vs-cta vs-cta--primary" type="button" onClick={() => go("architecture")}>
              See the bundle map
            </button>
            <button className="vs-cta" type="button" onClick={() => go("diagnostics")}>
              Inspect runtime
            </button>
          </div>
        </div>
        <div className="vs-orbit" aria-label="Bundled technologies">
          <img src={markUrl} alt="" />
          <span className="vs-pill">React 19</span>
          <span className="vs-pill">Vite 8</span>
          <span className="vs-pill">TypeScript</span>
          <span className="vs-pill">Worker</span>
        </div>
      </section>
      <section className="vs-section" aria-labelledby="inventory-title">
        <p className="vs-eyebrow">Included in extension.js</p>
        <h2 id="inventory-title" className="vs-page-title">A full toolchain, folded flat.</h2>
        <p className="vs-section-lede">Every card below began as a separate source concern. None requires a sibling file at runtime.</p>
        <div className="vs-grid">
          {featureInventory.features.map((feature, index) => (
            <article className="vs-card" key={feature}>
              <p className="vs-card-label">Layer {String(index + 1).padStart(2, "0")}</p>
              <h3>{feature}</h3>
              <p>{index < 3 ? "Loaded through Vite's asset pipeline." : "Bundled as executable module code."}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

function Architecture({ insight }: { insight: string }) {
  const sourceFiles = ["extension.tsx", "App.tsx", "styles.css", "mark.svg", "architecture.md", "feature-inventory.json", "lazy-insight.ts", "diagnostics.worker.ts"];
  return (
    <main className="vs-section">
      <p className="vs-eyebrow">Build anatomy</p>
      <h1 className="vs-page-title">Many inputs. One output.</h1>
      <p className="vs-section-lede">Vite keeps authoring pleasant, then deliberately removes runtime resolution from the equation.</p>
      <div className="vs-architecture">
        <article className="vs-card">
          <p className="vs-card-label">Source graph</p>
          <div className="vs-stack">
            {sourceFiles.map((file) => <code key={file}>src/{file}</code>)}
          </div>
        </article>
        <article className="vs-card">
          <p className="vs-card-label">Production flow</p>
          <div className="vs-flow">
            <div className="vs-flow-step"><div><h3>Transform</h3><p>JSX, TypeScript, CSS, Markdown, JSON, SVG, and Worker source enter Vite.</p></div></div>
            <div className="vs-flow-step"><div><h3>Inline</h3><p>Dynamic modules and assets become part of the ESM artifact.</p></div></div>
            <div className="vs-flow-step"><div><h3>Validate</h3><p>The artifact check rejects chunks, bare imports, and relative runtime assets.</p></div></div>
            <div className="vs-flow-step"><div><h3>Activate</h3><p>Canvas imports <code>extension.js</code> from a Blob URL.</p></div></div>
          </div>
        </article>
        <article className="vs-card">
          <p className="vs-card-label">Raw Markdown import</p>
          <p className="vs-raw">{architectureNotes}</p>
        </article>
        <article className="vs-card">
          <p className="vs-card-label">Source-level dynamic import</p>
          <h3>{insight || "Loading the lazy module…"}</h3>
          <p><code>import("./lazy-insight")</code> remains modular in source and local in production.</p>
        </article>
      </div>
    </main>
  );
}

function Diagnostic({ label, children }: { label: string; children: React.ReactNode }) {
  return <article className="vs-card"><p className="vs-card-label">{label}</p><div className="vs-value">{children}</div></article>;
}

function Diagnostics({ host, path, workerResult }: { host: CanvasHost; path: string; workerResult: WorkerResult | null }) {
  const backend = host.backend ?? {};
  const extension = host.extension ?? { name: "vite-showcase", version: "unknown" };
  return (
    <main className="vs-section">
      <p className="vs-eyebrow">Live mount context</p>
      <h1 className="vs-page-title">Runtime diagnostics.</h1>
      <p className="vs-section-lede">Values below come from the authenticated host and this App's inline Worker.</p>
      <div className="vs-diagnostics">
        <Diagnostic label="Host API"><span className="vs-status">Version {host.apiVersion}</span></Diagnostic>
        <Diagnostic label="App metadata">{extension.name} · {extension.version}<br />ref: {extension.resolvedRef ?? "local"}</Diagnostic>
        <Diagnostic label="Active backend">{backend.kind ?? "unknown"} · {backend.id ?? "unavailable"}<br />org: {backend.orgId ?? "none"}</Diagnostic>
        <Diagnostic label="Nested route">{path || "(root)"}</Diagnostic>
        <Diagnostic label="Worker result">
          {workerResult ? `fibonacci(${workerResult.input}) = ${workerResult.value} · ${workerResult.durationMs}ms` : "Calculating off the main thread…"}
        </Diagnostic>
        <Diagnostic label="Artifact contract">one ESM file · Blob-safe · self-contained</Diagnostic>
      </div>
    </main>
  );
}

function NotFound({ go }: { go: (route: string) => void }) {
  return <main className="vs-not-found"><div><strong>404</strong><h1>That nested route is not in this bundle.</h1><button className="vs-cta vs-cta--primary" type="button" onClick={() => go("overview")}>Return to showcase root</button></div></main>;
}

export function App({ host, path, navigate, signal }: AppProps) {
  const route = normalizeRoute(path);
  const [workerResult, setWorkerResult] = useState<WorkerResult | null>(null);
  const [insight, setInsight] = useState("");
  const go = (next: string) => navigate(next === "overview" ? ROOT_ROUTE : `${ROOT_ROUTE}/${next}`);

  useEffect(() => {
    const worker = new DiagnosticsWorker();
    const onMessage = (event: MessageEvent<WorkerResult>) => setWorkerResult(event.data);
    worker.addEventListener("message", onMessage);
    worker.postMessage({ input: 32 });

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.altKey && event.key >= "1" && event.key <= "3") {
        go(ROUTES[Number(event.key) - 1]);
      }
    };
    window.addEventListener("keydown", onKeyDown);

    void import("./lazy-insight")
      .then(({ loadBuildInsight }) => loadBuildInsight(signal))
      .then(setInsight)
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) throw error;
      });

    return () => {
      worker.removeEventListener("message", onMessage);
      worker.terminate();
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [signal]);

  return (
    <section className="vite-showcase" aria-label="Vite Showcase App">
      <div className="vs-shell">
        <header className="vs-header">
          <button className="vs-brand" type="button" onClick={() => go("overview")} aria-label="Return to Vite Showcase root">
            <img className="vs-mark" src={markUrl} alt="" />
            <span className="vs-brand-copy"><span className="vs-kicker">Canvas App</span><span className="vs-brand-name">Vite Showcase</span></span>
          </button>
          <Nav route={route} go={go} />
        </header>
        {route === "overview" ? <Overview go={go} /> : null}
        {route === "architecture" ? <Architecture insight={insight} /> : null}
        {route === "diagnostics" ? <Diagnostics host={host} path={path} workerResult={workerResult} /> : null}
        {route === "not-found" ? <NotFound go={go} /> : null}
        <footer className="vs-footer"><span>Built with {featureInventory.bundler} · {featureInventory.language}</span><span>Alt+1 / 2 / 3 to navigate</span></footer>
      </div>
    </section>
  );
}
