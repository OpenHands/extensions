const REFRESH_INTERVAL_MS = 30_000;

const STYLE = `
  .canvas-pulse {
    min-height: 100%;
    box-sizing: border-box;
    padding: clamp(1.25rem, 3vw, 2.5rem);
    color: var(--oh-foreground, #f4f4f5);
    background:
      radial-gradient(circle at 82% 4%, color-mix(in srgb, var(--oh-accent, #c9b974) 12%, transparent), transparent 24rem),
      var(--oh-background, #0c0d0f);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }
  .canvas-pulse * { box-sizing: border-box; }
  .canvas-pulse__shell { width: min(1120px, 100%); margin: 0 auto; }
  .canvas-pulse__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 1.5rem; margin-bottom: 1.5rem; }
  .canvas-pulse__eyebrow { margin: 0 0 .4rem; color: var(--oh-accent, #c9b974); font-size: .7rem; font-weight: 750; letter-spacing: .14em; text-transform: uppercase; }
  .canvas-pulse__title { margin: 0; font-size: clamp(1.75rem, 4vw, 2.75rem); line-height: 1; letter-spacing: -.035em; }
  .canvas-pulse__subtitle { max-width: 44rem; margin: .75rem 0 0; color: var(--oh-text-secondary, #b6bac3); font-size: .9rem; line-height: 1.55; }
  .canvas-pulse__actions { display: flex; align-items: center; gap: .65rem; flex-wrap: wrap; justify-content: flex-end; }
  .canvas-pulse__button { appearance: none; border: 1px solid var(--oh-border, #4b505c); border-radius: var(--oh-radius, 8px); padding: .62rem .85rem; color: var(--oh-foreground, #f4f4f5); background: var(--oh-surface, #1b1d22); font: inherit; font-size: .78rem; font-weight: 650; cursor: pointer; transition: border-color 150ms, background 150ms, transform 150ms; }
  .canvas-pulse__button:hover { border-color: color-mix(in srgb, var(--oh-accent, #c9b974) 65%, var(--oh-border, #4b505c)); background: var(--oh-surface-raised, #262930); }
  .canvas-pulse__button:focus-visible { outline: 2px solid var(--oh-focus, #fff); outline-offset: 2px; }
  .canvas-pulse__button:active { transform: translateY(1px); }
  .canvas-pulse__button:disabled { opacity: .55; cursor: wait; }
  .canvas-pulse__status { display: inline-flex; align-items: center; gap: .45rem; padding: .4rem .62rem; border: 1px solid var(--oh-border-subtle, #343842); border-radius: 999px; color: var(--oh-text-secondary, #b6bac3); background: color-mix(in srgb, var(--oh-surface, #1b1d22) 82%, transparent); font-size: .72rem; white-space: nowrap; }
  .canvas-pulse__status-dot { width: .5rem; height: .5rem; border-radius: 50%; background: var(--oh-muted, #777c88); box-shadow: 0 0 0 .2rem color-mix(in srgb, var(--oh-muted, #777c88) 14%, transparent); }
  .canvas-pulse__status--ok .canvas-pulse__status-dot { background: var(--oh-success, #a5e75e); box-shadow: 0 0 0 .2rem color-mix(in srgb, var(--oh-success, #a5e75e) 14%, transparent); }
  .canvas-pulse__status--error .canvas-pulse__status-dot { background: var(--oh-danger, #e76a5e); box-shadow: 0 0 0 .2rem color-mix(in srgb, var(--oh-danger, #e76a5e) 14%, transparent); }
  .canvas-pulse__metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .8rem; margin-bottom: 1.5rem; }
  .canvas-pulse__metric, .canvas-pulse__panel, .canvas-pulse__service { border: 1px solid var(--oh-border-subtle, #343842); background: color-mix(in srgb, var(--oh-surface, #1b1d22) 92%, transparent); box-shadow: var(--oh-surface-shadow, none); }
  .canvas-pulse__metric { min-height: 7rem; padding: 1rem; border-radius: calc(var(--oh-radius, 8px) + 2px); }
  .canvas-pulse__metric-label { margin: 0; color: var(--oh-text-dim, #777c88); font-size: .68rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
  .canvas-pulse__metric-value { margin: .65rem 0 .25rem; overflow: hidden; color: var(--oh-surface-foreground, #f4f4f5); font-size: clamp(1.2rem, 2.8vw, 1.65rem); font-weight: 720; line-height: 1.1; text-overflow: ellipsis; white-space: nowrap; }
  .canvas-pulse__metric-detail { margin: 0; color: var(--oh-text-secondary, #b6bac3); font-size: .72rem; line-height: 1.4; }
  .canvas-pulse__grid { display: grid; grid-template-columns: minmax(0, 1.45fr) minmax(16rem, .75fr); gap: 1rem; align-items: start; }
  .canvas-pulse__panel { min-width: 0; padding: 1rem; border-radius: calc(var(--oh-radius, 8px) + 4px); }
  .canvas-pulse__panel + .canvas-pulse__panel { margin-top: 1rem; }
  .canvas-pulse__panel-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; margin-bottom: .9rem; }
  .canvas-pulse__panel-title { margin: 0; font-size: .95rem; font-weight: 700; }
  .canvas-pulse__panel-copy { margin: .28rem 0 0; color: var(--oh-text-dim, #777c88); font-size: .72rem; line-height: 1.45; }
  .canvas-pulse__services { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .65rem; }
  .canvas-pulse__service { width: 100%; padding: .85rem; border-radius: var(--oh-radius, 8px); color: inherit; text-align: left; cursor: pointer; transition: border-color 150ms, transform 150ms, background 150ms; }
  .canvas-pulse__service:hover { border-color: color-mix(in srgb, var(--oh-accent, #c9b974) 58%, var(--oh-border, #4b505c)); background: var(--oh-surface-raised, #262930); transform: translateY(-1px); }
  .canvas-pulse__service:focus-visible { outline: 2px solid var(--oh-focus, #fff); outline-offset: 2px; }
  .canvas-pulse__service-topline { display: flex; align-items: center; justify-content: space-between; gap: .75rem; }
  .canvas-pulse__service-name { font-size: .8rem; font-weight: 680; }
  .canvas-pulse__service-kind { color: var(--oh-accent, #c9b974); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .63rem; }
  .canvas-pulse__service-url { display: block; margin-top: .5rem; overflow: hidden; color: var(--oh-text-dim, #777c88); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .65rem; text-overflow: ellipsis; white-space: nowrap; }
  .canvas-pulse__chips { display: flex; flex-wrap: wrap; gap: .45rem; }
  .canvas-pulse__chip { display: inline-flex; align-items: center; min-height: 1.7rem; padding: .25rem .55rem; border: 1px solid var(--oh-border-subtle, #343842); border-radius: 999px; color: var(--oh-text-secondary, #b6bac3); background: var(--oh-surface-deep, #111216); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .66rem; }
  .canvas-pulse__definition { display: grid; grid-template-columns: minmax(7rem, .35fr) minmax(0, 1fr); margin: 0; }
  .canvas-pulse__definition dt, .canvas-pulse__definition dd { min-width: 0; margin: 0; padding: .65rem 0; border-bottom: 1px solid var(--oh-border-subtle, #343842); font-size: .76rem; line-height: 1.45; }
  .canvas-pulse__definition dt { color: var(--oh-text-dim, #777c88); }
  .canvas-pulse__definition dd { overflow-wrap: anywhere; color: var(--oh-text-secondary, #b6bac3); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  .canvas-pulse__empty, .canvas-pulse__error { padding: 1.1rem; border: 1px dashed var(--oh-border, #4b505c); border-radius: var(--oh-radius, 8px); color: var(--oh-text-secondary, #b6bac3); background: var(--oh-surface-deep, #111216); font-size: .78rem; line-height: 1.55; }
  .canvas-pulse__error { border-style: solid; border-color: color-mix(in srgb, var(--oh-danger, #e76a5e) 46%, var(--oh-border, #4b505c)); }
  .canvas-pulse__footer { display: flex; justify-content: space-between; gap: 1rem; margin-top: 1.25rem; color: var(--oh-text-dim, #777c88); font-size: .67rem; }
  @media (max-width: 850px) { .canvas-pulse__metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); } .canvas-pulse__grid { grid-template-columns: 1fr; } }
  @media (max-width: 560px) { .canvas-pulse__header { flex-direction: column; } .canvas-pulse__actions { justify-content: flex-start; } .canvas-pulse__metrics, .canvas-pulse__services { grid-template-columns: 1fr; } .canvas-pulse__footer { flex-direction: column; } }
  @media (prefers-reduced-motion: reduce) { .canvas-pulse__button, .canvas-pulse__service { transition: none; } }
`;

function element(tagName, className, text) {
  const node = document.createElement(tagName);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function asRecord(value) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value
    : null;
}

function stringList(value) {
  return Array.isArray(value)
    ? value.filter((item) => typeof item === "string")
    : [];
}

function titleCase(value) {
  return value
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
    .replace(/\bApi\b/g, "API")
    .replace(/\bId\b/g, "ID")
    .replace(/\bUrl\b/g, "URL");
}

function formatDuration(value) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
    return "Unknown";
  }
  const seconds = Math.floor(value);
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);
  if (days) return `${days}d ${hours}h`;
  if (hours) return `${hours}h ${minutes}m`;
  if (minutes) return `${minutes}m ${seconds % 60}s`;
  return `${seconds}s`;
}

function readRuntimeServices(serverInfo) {
  const runtime = asRecord(serverInfo.runtime_services);
  const services = asRecord(runtime?.services) ?? {};
  return { runtime, services };
}

function metric(label, value, detail) {
  const card = element("article", "canvas-pulse__metric");
  card.append(
    element("p", "canvas-pulse__metric-label", label),
    element("p", "canvas-pulse__metric-value", value),
    element("p", "canvas-pulse__metric-detail", detail),
  );
  return card;
}

function chipList(values, emptyText) {
  if (!values.length) return element("div", "canvas-pulse__empty", emptyText);
  const list = element("div", "canvas-pulse__chips");
  for (const value of values)
    list.append(element("span", "canvas-pulse__chip", value));
  return list;
}

function panel(title, copy) {
  const card = element("section", "canvas-pulse__panel");
  const heading = element("header", "canvas-pulse__panel-heading");
  const text = element("div");
  text.append(
    element("h2", "canvas-pulse__panel-title", title),
    element("p", "canvas-pulse__panel-copy", copy),
  );
  heading.append(text);
  card.append(heading);
  return card;
}

function statusBadge(serverInfo, error, loading) {
  const modifier = error
    ? " canvas-pulse__status--error"
    : serverInfo
      ? " canvas-pulse__status--ok"
      : "";
  const label = error
    ? "Unavailable"
    : serverInfo
      ? "Connected"
      : loading
        ? "Connecting"
        : "Waiting";
  const badge = element("span", `canvas-pulse__status${modifier}`);
  badge.setAttribute("role", "status");
  badge.append(
    element("span", "canvas-pulse__status-dot"),
    document.createTextNode(label),
  );
  return badge;
}

function addDefinition(list, label, value) {
  if (value === undefined || value === null || value === "") return;
  list.append(element("dt", "", label), element("dd", "", String(value)));
}

function renderServiceDetail(
  content,
  serviceName,
  service,
  navigate,
  rootPath,
) {
  const back = element("button", "canvas-pulse__button", "← Runtime topology");
  back.type = "button";
  back.addEventListener("click", () => navigate(rootPath));

  const card = panel(
    titleCase(serviceName),
    "Runtime service details are advertised by the active Agent Server stack.",
  );
  card.querySelector(".canvas-pulse__panel-heading")?.append(back);
  if (!service) {
    card.append(
      element(
        "div",
        "canvas-pulse__error",
        "This runtime service is no longer available.",
      ),
    );
    content.append(card);
    return;
  }

  const definition = element("dl", "canvas-pulse__definition");
  for (const [key, value] of Object.entries(service)) {
    if (["string", "number", "boolean"].includes(typeof value)) {
      addDefinition(definition, titleCase(key), value);
    }
  }
  card.append(definition);
  content.append(card);
}

function renderOverview(content, serverInfo, host, navigate, rootPath) {
  const tools = stringList(serverInfo.usable_tools);
  const agents = stringList(serverInfo.agents);
  const { runtime, services } = readRuntimeServices(serverInfo);
  const serviceEntries = Object.entries(services).filter(([, value]) =>
    asRecord(value),
  );
  const metrics = element("div", "canvas-pulse__metrics");
  metrics.append(
    metric(
      "Agent Server",
      String(serverInfo.sdk_version ?? serverInfo.version ?? "Unknown"),
      "Reported SDK/server version",
    ),
    metric(
      "Uptime",
      formatDuration(serverInfo.uptime),
      `Idle for ${formatDuration(serverInfo.idle_time)}`,
    ),
    metric(
      "Tools",
      String(tools.length),
      tools.length ? "Advertised capabilities" : "No tool list advertised",
    ),
    metric(
      "Services",
      String(serviceEntries.length),
      runtime?.mode ? `Stack: ${runtime.mode}` : "No stack mode advertised",
    ),
  );
  content.append(metrics);

  const grid = element("div", "canvas-pulse__grid");
  const primary = element("div");
  const topology = panel(
    "Runtime topology",
    "URLs are shown from the agent sandbox's point of view.",
  );
  if (serviceEntries.length) {
    const serviceGrid = element("div", "canvas-pulse__services");
    for (const [name, rawService] of serviceEntries) {
      const service = asRecord(rawService);
      const button = element("button", "canvas-pulse__service");
      button.type = "button";
      const topline = element("span", "canvas-pulse__service-topline");
      topline.append(
        element("span", "canvas-pulse__service-name", titleCase(name)),
        element(
          "span",
          "canvas-pulse__service-kind",
          String(service?.kind ?? "service"),
        ),
      );
      button.append(
        topline,
        element(
          "span",
          "canvas-pulse__service-url",
          String(service?.url_from_agent ?? "URL not advertised"),
        ),
      );
      button.addEventListener("click", () =>
        navigate(`${rootPath}/services/${encodeURIComponent(name)}`),
      );
      serviceGrid.append(button);
    }
    topology.append(serviceGrid);
  } else {
    topology.append(
      element(
        "div",
        "canvas-pulse__empty",
        "This stack does not advertise runtime service topology.",
      ),
    );
  }
  primary.append(topology);

  const toolsPanel = panel(
    "Usable tools",
    "Capabilities this Agent Server currently advertises to Canvas.",
  );
  toolsPanel.append(
    chipList(tools, "No usable tools were included in /server_info."),
  );
  primary.append(toolsPanel);

  const secondary = element("div");
  const backendPanel = panel(
    "Backend context",
    "This extension follows the active backend and unloads when it changes.",
  );
  const backendDefinition = element("dl", "canvas-pulse__definition");
  addDefinition(backendDefinition, "Backend", host.backend.id);
  addDefinition(backendDefinition, "Kind", host.backend.kind);
  addDefinition(
    backendDefinition,
    "Organization",
    host.backend.orgId ?? "Local",
  );
  addDefinition(backendDefinition, "Host API", host.apiVersion);
  addDefinition(
    backendDefinition,
    "Extension",
    `${host.extension.name} ${host.extension.version}`,
  );
  backendPanel.append(backendDefinition);
  secondary.append(backendPanel);

  const agentsPanel = panel(
    "Agents",
    "Agent implementations advertised by this backend.",
  );
  agentsPanel.append(
    chipList(agents, "No agent list was included in /server_info."),
  );
  secondary.append(agentsPanel);

  grid.append(primary, secondary);
  content.append(grid);
}

function render(root, state, host, path, navigate, refresh) {
  root.replaceChildren();
  const shell = element("div", "canvas-pulse__shell");
  const header = element("header", "canvas-pulse__header");
  const heading = element("div");
  heading.append(
    element("p", "canvas-pulse__eyebrow", "Live backend telemetry"),
    element("h1", "canvas-pulse__title", "Canvas Pulse"),
    element(
      "p",
      "canvas-pulse__subtitle",
      "A lightweight view of the Agent Server powering this Canvas session.",
    ),
  );
  const actions = element("div", "canvas-pulse__actions");
  actions.append(statusBadge(state.serverInfo, state.error, state.loading));
  const refreshButton = element(
    "button",
    "canvas-pulse__button",
    state.loading ? "Refreshing…" : "Refresh now",
  );
  refreshButton.type = "button";
  refreshButton.disabled = state.loading;
  refreshButton.addEventListener("click", refresh);
  actions.append(refreshButton);
  header.append(heading, actions);
  shell.append(header);

  const content = element("div");
  if (state.error && !state.serverInfo) {
    content.append(element("div", "canvas-pulse__error", state.error));
  } else if (!state.serverInfo) {
    content.append(
      element(
        "div",
        "canvas-pulse__empty",
        "Connecting to the active Agent Server…",
      ),
    );
  } else {
    const rootPath = `/extensions/${encodeURIComponent(host.extension.name)}/pulse`;
    const serviceMatch = path.match(/^services\/([^/]+)$/);
    if (serviceMatch) {
      const serviceName = decodeURIComponent(serviceMatch[1]);
      const { services } = readRuntimeServices(state.serverInfo);
      renderServiceDetail(
        content,
        serviceName,
        asRecord(services[serviceName]),
        navigate,
        rootPath,
      );
    } else {
      renderOverview(content, state.serverInfo, host, navigate, rootPath);
    }
  }
  shell.append(content);

  const footer = element("footer", "canvas-pulse__footer");
  footer.append(
    element(
      "span",
      "",
      state.lastUpdated
        ? `Last checked ${state.lastUpdated.toLocaleTimeString()}`
        : "Awaiting first response",
    ),
    element("span", "", `Auto-refreshes every ${REFRESH_INTERVAL_MS / 1000}s`),
  );
  shell.append(footer);
  root.append(shell);
}

function errorMessage(error) {
  return error instanceof Error
    ? error.message
    : "Canvas Pulse could not reach the Agent Server.";
}

export function activate(host) {
  if (host.apiVersion !== "1") {
    throw new Error(
      `Canvas Pulse requires host API 1, received ${host.apiVersion}.`,
    );
  }

  return host.registerPage("pulse", ({ container, path, navigate }) => {
    const style = element("style");
    style.textContent = STYLE;
    const root = element("section", "canvas-pulse");
    root.setAttribute("aria-label", "Canvas Pulse dashboard");
    container.append(style, root);

    let disposed = false;
    const state = {
      serverInfo: null,
      error: null,
      loading: false,
      lastUpdated: null,
    };

    const refresh = async () => {
      if (disposed || state.loading) return;
      state.loading = true;
      state.error = null;
      render(root, state, host, path, navigate, () => void refresh());
      try {
        const response = await host.agentServer.request({
          path: "/server_info",
        });
        if (!asRecord(response))
          throw new Error(
            "Agent Server returned an invalid /server_info response.",
          );
        if (disposed) return;
        state.serverInfo = response;
        state.lastUpdated = new Date();
      } catch (error) {
        if (disposed) return;
        state.error = errorMessage(error);
      } finally {
        if (!disposed) {
          state.loading = false;
          render(root, state, host, path, navigate, () => void refresh());
        }
      }
    };

    render(root, state, host, path, navigate, () => void refresh());
    void refresh();
    const interval = window.setInterval(
      () => void refresh(),
      REFRESH_INTERVAL_MS,
    );

    return () => {
      disposed = true;
      window.clearInterval(interval);
      root.remove();
      style.remove();
    };
  });
}
