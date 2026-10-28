// Personal Profile — a Canvas Extension showing contribution graphs and usage stats.
// Dependency-free, self-contained browser ESM. Targets Canvas host API 1.

const STORAGE_KEY = "personal-profile:github-username";
const WEEKS = 53;
const POLL_INTERVAL_MS = 60_000;

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function record(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : null;
}

function parseTime(value) {
  const time = typeof value === "string" ? Date.parse(value) : NaN;
  return Number.isFinite(time) ? time : 0;
}

function dayKey(timestamp) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return null;
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function startOfDay(timestamp) {
  const date = new Date(timestamp);
  date.setHours(0, 0, 0, 0);
  return date.getTime();
}

function formatDate(timestamp) {
  if (!timestamp) return "Unknown";
  return new Date(timestamp).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatNumber(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "0";
  return value.toLocaleString();
}

// ---------------------------------------------------------------------------
// Heatmap grid builder
// ---------------------------------------------------------------------------

/**
 * Build a 53-week × 7-day grid of activity counts.
 * @param {Record<string, number>} counts — map of "YYYY-MM-DD" → count
 * @returns {{ weeks: Array<Array<{date: string, count: number, level: number}>>, max: number, total: number, activeDays: number }}
 */
function buildHeatmap(counts) {
  const today = startOfDay(Date.now());
  const end = today;
  // Move back to the Saturday of the last column so the grid ends today's column
  const endDay = new Date(end).getDay(); // 0=Sun..6=Sat
  const gridEnd = end + (6 - endDay) * 86_400_000; // align to week end (Saturday)
  const gridStart = gridEnd - (WEEKS - 1) * 7 * 86_400_000;

  const weeks = [];
  let max = 0;
  let total = 0;
  let activeDays = 0;

  for (let w = 0; w < WEEKS; w++) {
    const week = [];
    for (let d = 0; d < 7; d++) {
      const dayTimestamp = gridStart + (w * 7 + d) * 86_400_000;
      const date = new Date(dayTimestamp);
      if (date.getTime() > today + 86_400_000) {
        // Future day — leave empty
        week.push({ date: dayKey(dayTimestamp), count: 0, level: 0, future: true });
        continue;
      }
      const key = dayKey(dayTimestamp);
      const count = counts[key] || 0;
      total += count;
      if (count > 0) activeDays++;
      if (count > max) max = count;
      week.push({ date: key, count, level: 0, future: false });
    }
    weeks.push(week);
  }

  // Assign levels (0-4) based on max
  for (const week of weeks) {
    for (const cell of week) {
      if (cell.count === 0 || cell.future) {
        cell.level = 0;
      } else if (max <= 0) {
        cell.level = 0;
      } else {
        const ratio = cell.count / max;
        cell.level = ratio > 0.75 ? 4 : ratio > 0.5 ? 3 : ratio > 0.25 ? 2 : 1;
      }
    }
  }

  return { weeks, max, total, activeDays };
}

// ---------------------------------------------------------------------------
// Agent Server data fetching
// ---------------------------------------------------------------------------

function normalizePage(response, label) {
  const page = record(response);
  if (!page || !Array.isArray(page.items)) {
    throw new Error(`${label} returned an unexpected response.`);
  }
  return {
    items: page.items.filter((item) => record(item)),
    nextPageId: typeof page.next_page_id === "string" ? page.next_page_id : null,
  };
}

async function fetchAllConversations(host, disposed) {
  const items = [];
  let pageId = null;
  do {
    const params = new URLSearchParams({ limit: "100" });
    if (pageId) params.set("page_id", pageId);
    const response = await host.agentServer.request({
      path: `/api/conversations/search?${params}`,
    });
    if (disposed()) return items;
    const page = normalizePage(response, "Conversation search");
    items.push(...page.items);
    pageId = page.nextPageId;
  } while (pageId);
  return items;
}

/**
 * Extract LLM usage metrics from conversation events.
 * Events may contain llm_metrics, token_usage, or usage fields with
 * prompt_tokens / completion_tokens / total_tokens.
 */
function extractLlmUsage(event) {
  const metrics = record(event?.llm_metrics);
  const candidates = [
    record(metrics?.usage),
    metrics,
    record(event?.token_usage),
    record(event?.usage),
    record(event?.llm_message?.usage),
    record(event?.metrics),
  ];
  const usage = candidates.find((c) => c && typeof c === "object" && !Array.isArray(c));
  if (!usage) return null;

  const prompt = Number(usage.prompt_tokens ?? usage.input_tokens ?? usage.input ?? 0);
  const completion = Number(
    usage.completion_tokens ?? usage.output_tokens ?? usage.output ?? 0,
  );
  const total =
    Number(usage.total_tokens ?? usage.total ?? 0) || prompt + completion;

  if (prompt === 0 && completion === 0 && total === 0) return null;

  return {
    prompt_tokens: Number.isFinite(prompt) ? prompt : 0,
    completion_tokens: Number.isFinite(completion) ? completion : 0,
    total_tokens: Number.isFinite(total) ? total : 0,
    timestamp: parseTime(event.timestamp),
  };
}

async function fetchConversationEvents(host, conversationId, disposed) {
  const items = [];
  let pageId = null;
  let pageCount = 0;
  do {
    const params = new URLSearchParams({ limit: "100" });
    if (pageId) params.set("page_id", pageId);
    const response = await host.agentServer.request({
      path: `/api/conversations/${encodeURIComponent(conversationId)}/events/search?${params}`,
    });
    if (disposed()) return items;
    const page = normalizePage(response, "Event search");
    items.push(...page.items);
    pageId = page.nextPageId;
    pageCount++;
    // Safety limit: don't fetch more than 50 pages per conversation
    if (pageCount >= 50) break;
  } while (pageId);
  return items;
}

// ---------------------------------------------------------------------------
// GitHub data fetching (public API, unauthenticated)
// ---------------------------------------------------------------------------

async function fetchGitHubProfile(username) {
  const response = await fetch(`https://api.github.com/users/${encodeURIComponent(username)}`);
  if (response.status === 404) {
    throw new Error(`GitHub user "${username}" not found.`);
  }
  if (!response.ok) {
    throw new Error(`GitHub API returned ${response.status} ${response.statusText}.`);
  }
  const data = await response.json();
  return record(data) ? data : null;
}

async function fetchGitHubEvents(username) {
  const allEvents = [];
  // GitHub returns up to 10 pages of 30 events (300 total) for public events
  for (let page = 1; page <= 10; page++) {
    const response = await fetch(
      `https://api.github.com/users/${encodeURIComponent(username)}/events?per_page=100&page=${page}`,
    );
    if (!response.ok) {
      if (page === 1) {
        throw new Error(
          `GitHub events API returned ${response.status} ${response.statusText}.`,
        );
      }
      break; // subsequent page failure — use what we have
    }
    const events = await response.json();
    if (!Array.isArray(events) || events.length === 0) break;
    allEvents.push(...events);
    if (events.length < 100) break; // last page
  }
  return allEvents;
}

// ---------------------------------------------------------------------------
// Rendering: Heatmap
// ---------------------------------------------------------------------------

const HEATMAP_COLORS = [
  "var(--oh-surface-deep, #161b22)",
  "var(--pp-green-1, #0e4429)",
  "var(--pp-green-2, #006d32)",
  "var(--pp-green-3, #26a641)",
  "var(--pp-green-4, #39d353)",
];

function renderHeatmap(container, heatmap, label, colorPrefix) {
  const wrapper = element("div", "pp-heatmap-wrapper");
  wrapper.style.setProperty("--pp-heatmap-color", colorPrefix);

  const header = element("div", "pp-heatmap-header");
  header.append(
    element("h3", "pp-heatmap-title", label),
    element(
      "p",
      "pp-heatmap-stats",
      `${formatNumber(heatmap.total)} contributions in the last year`,
    ),
  );
  wrapper.append(header);

  const scrollContainer = element("div", "pp-heatmap-scroll");
  const grid = element("div", "pp-heatmap-grid");
  grid.setAttribute("role", "img");
  grid.setAttribute(
    "aria-label",
    `${label}: ${formatNumber(heatmap.total)} contributions, ${formatNumber(heatmap.activeDays)} active days`,
  );

  // Month labels
  const monthRow = element("div", "pp-heatmap-months");
  const monthLabels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  let lastMonth = -1;
  for (let w = 0; w < heatmap.weeks.length; w++) {
    const firstCell = heatmap.weeks[w][0];
    const month = firstCell.date ? new Date(firstCell.date).getMonth() : -1;
    const cell = element("span", "pp-heatmap-month-cell");
    if (month !== lastMonth && month >= 0) {
      cell.textContent = monthLabels[month];
      lastMonth = month;
    }
    monthRow.append(cell);
  }
  grid.append(monthRow);

  // Day labels + cells
  const body = element("div", "pp-heatmap-body");
  const dayLabelCol = element("div", "pp-heatmap-day-labels");
  const dayLabels = ["Sun", "", "Tue", "", "Thu", "", "Sat"];
  for (const dl of dayLabels) {
    dayLabelCol.append(element("span", "pp-heatmap-day-label", dl));
  }
  body.append(dayLabelCol);

  const weeksContainer = element("div", "pp-heatmap-weeks");
  for (const week of heatmap.weeks) {
    const weekCol = element("div", "pp-heatmap-week");
    for (const cell of week) {
      const cellEl = element("div", `pp-heatmap-cell pp-heatmap-cell--level-${cell.level}`);
      if (cell.future) {
        cellEl.classList.add("pp-heatmap-cell--future");
      }
      cellEl.title = `${cell.date}: ${formatNumber(cell.count)} contribution${cell.count === 1 ? "" : "s"}`;
      weekCol.append(cellEl);
    }
    weeksContainer.append(weekCol);
  }
  body.append(weeksContainer);
  grid.append(body);

  // Legend
  const legend = element("div", "pp-heatmap-legend");
  legend.append(
    element("span", "pp-heatmap-legend-label", "Less"),
    element("div", `pp-heatmap-cell pp-heatmap-cell--level-0`),
    element("div", `pp-heatmap-cell pp-heatmap-cell--level-1`),
    element("div", `pp-heatmap-cell pp-heatmap-cell--level-2`),
    element("div", `pp-heatmap-cell pp-heatmap-cell--level-3`),
    element("div", `pp-heatmap-cell pp-heatmap-cell--level-4`),
    element("span", "pp-heatmap-legend-label", "More"),
  );
  grid.append(legend);

  scrollContainer.append(grid);
  wrapper.append(scrollContainer);
  container.append(wrapper);
}

// ---------------------------------------------------------------------------
// Rendering: LLM Usage stats
// ---------------------------------------------------------------------------

function renderLlmStats(container, usage) {
  const panel = element("div", "pp-panel");
  panel.append(
    element("h3", "pp-panel-title", "LLM Usage"),
    element("p", "pp-panel-copy", "Token consumption aggregated from conversation events."),
  );

  const grid = element("div", "pp-stats-grid");
  grid.append(
    statCard("Total tokens", formatNumber(usage.totalTokens), "Across all conversations"),
    statCard("Prompt tokens", formatNumber(usage.promptTokens), "Input sent to models"),
    statCard("Completion tokens", formatNumber(usage.completionTokens), "Output from models"),
    statCard("Usage events", formatNumber(usage.eventCount), "Events with token data"),
  );
  panel.append(grid);

  if (usage.byModel.size > 0) {
    const modelList = element("div", "pp-model-list");
    modelList.append(element("h4", "pp-model-list-title", "By model"));
    const sorted = [...usage.byModel.entries()].sort((a, b) => b[1] - a[1]);
    for (const [model, tokens] of sorted) {
      const row = element("div", "pp-model-row");
      row.append(
        element("span", "pp-model-name", model),
        element("span", "pp-model-tokens", formatNumber(tokens)),
      );
      modelList.append(row);
    }
    panel.append(modelList);
  }

  container.append(panel);
}

function statCard(label, value, detail) {
  const card = element("div", "pp-stat-card");
  card.append(
    element("p", "pp-stat-label", label),
    element("p", "pp-stat-value", value),
    element("p", "pp-stat-detail", detail),
  );
  return card;
}

// ---------------------------------------------------------------------------
// Rendering: GitHub Profile card
// ---------------------------------------------------------------------------

function renderGitHubProfile(container, profile) {
  const card = element("div", "pp-gh-profile");
  const avatar = element("img", "pp-gh-avatar");
  avatar.src = profile.avatar_url;
  avatar.alt = `${profile.login} avatar`;
  avatar.width = 64;
  avatar.height = 64;

  const info = element("div", "pp-gh-info");
  const name = element("h3", "pp-gh-name", profile.name || profile.login);
  const login = element("p", "pp-gh-login", `@${profile.login}`);
  info.append(name, login);

  if (profile.bio) {
    info.append(element("p", "pp-gh-bio", String(profile.bio)));
  }

  const stats = element("div", "pp-gh-stats");
  stats.append(
    element("span", "pp-gh-stat", `Repos: ${formatNumber(profile.public_repos ?? 0)}`),
    element("span", "pp-gh-stat", `Followers: ${formatNumber(profile.followers ?? 0)}`),
    element("span", "pp-gh-stat", `Following: ${formatNumber(profile.following ?? 0)}`),
  );
  info.append(stats);

  if (profile.created_at) {
    info.append(
      element("p", "pp-gh-joined", `Joined ${formatDate(parseTime(profile.created_at))}`),
    );
  }

  card.append(avatar, info);
  container.append(card);
}

// ---------------------------------------------------------------------------
// Rendering: Settings
// ---------------------------------------------------------------------------

function renderSettings(container, state, onSave) {
  const panel = element("div", "pp-panel pp-settings");
  panel.append(
    element("h3", "pp-panel-title", "GitHub Settings"),
    element("p", "pp-panel-copy", "Enter your GitHub username to fetch public activity and profile data."),
  );

  const form = element("form", "pp-settings-form");
  const input = element("input", "pp-input");
  input.type = "text";
  input.value = state.githubUsername || "";
  input.placeholder = "e.g. octocat";
  input.setAttribute("aria-label", "GitHub username");
  input.spellcheck = false;
  input.autocomplete = "off";

  const saveButton = element("button", "pp-button", "Save");
  saveButton.type = "submit";

  const clearButton = element("button", "pp-button pp-button--ghost", "Clear");
  clearButton.type = "button";
  clearButton.addEventListener("click", () => {
    input.value = "";
    onSave("");
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    onSave(input.value.trim());
  });

  form.append(input, saveButton, clearButton);
  panel.append(form);

  if (state.githubError) {
    panel.append(element("div", "pp-error", state.githubError));
  }

  container.append(panel);
}

// ---------------------------------------------------------------------------
// Main render
// ---------------------------------------------------------------------------

function render(root, state, host, refresh) {
  root.replaceChildren();

  const shell = element("div", "pp-shell");

  // Header
  const header = element("header", "pp-header");
  const heading = element("div");
  heading.append(
    element("p", "pp-eyebrow", "Activity dashboard"),
    element("h1", "pp-title", "Personal Profile"),
    element(
      "p",
      "pp-subtitle",
      "Contribution graphs and usage stats across your OpenHands conversations, GitHub activity, and LLM usage.",
    ),
  );
  const actions = element("div", "pp-actions");
  const refreshButton = element(
    "button",
    "pp-button",
    state.loading ? "Refreshing…" : "Refresh",
  );
  refreshButton.type = "button";
  refreshButton.disabled = state.loading;
  refreshButton.addEventListener("click", refresh);
  actions.append(refreshButton);
  header.append(heading, actions);
  shell.append(header);

  // Settings
  renderSettings(shell, state, (username) => {
    if (username) {
      try {
        localStorage.setItem(STORAGE_KEY, username);
      } catch {
        // localStorage may be unavailable
      }
    } else {
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch {
        // noop
      }
    }
    state.githubUsername = username;
    refresh();
  });

  // Loading / error / content
  if (state.loading && !state.loaded) {
    shell.append(element("div", "pp-loading", "Loading your activity data…"));
  } else if (state.error && !state.loaded) {
    shell.append(element("div", "pp-error", state.error));
  } else {
    // OpenHands conversation heatmap
    if (state.conversationHeatmap) {
      renderHeatmap(
        shell,
        state.conversationHeatmap,
        "OpenHands Conversations",
        "var(--oh-accent, #c9b974)",
      );
    }

    // GitHub section
    if (state.githubUsername) {
      const ghSection = element("div", "pp-section");
      ghSection.append(element("h2", "pp-section-title", "GitHub Activity"));

      if (state.githubLoading) {
        ghSection.append(element("div", "pp-loading", "Fetching GitHub data…"));
      } else if (state.githubError) {
        ghSection.append(element("div", "pp-error", state.githubError));
      } else if (state.githubProfile) {
        renderGitHubProfile(ghSection, state.githubProfile);
        if (state.githubHeatmap) {
          renderHeatmap(
            ghSection,
            state.githubHeatmap,
            "GitHub Contributions",
            "var(--pp-green-4, #39d353)",
          );
        }
      }
      shell.append(ghSection);
    }

    // LLM usage
    if (state.llmUsage) {
      renderLlmStats(shell, state.llmUsage);
    }

    // Footer
    const footer = element("footer", "pp-footer");
    footer.append(
      element(
        "span",
        "",
        state.lastUpdated
          ? `Last updated ${state.lastUpdated.toLocaleTimeString()}`
          : "",
      ),
      element("span", "", `Backend: ${host.backend.id} (${host.backend.kind})`),
    );
    shell.append(footer);
  }

  root.append(shell);
}

// ---------------------------------------------------------------------------
// Activation
// ---------------------------------------------------------------------------

export function activate(host) {
  if (host.apiVersion !== "1") {
    throw new Error(
      `Personal Profile requires host API 1, received ${host.apiVersion}.`,
    );
  }

  return host.registerPage("profile", ({ container }) => {
    const style = element("style");
    style.textContent = STYLE;
    const root = element("section", "personal-profile");
    root.setAttribute("aria-label", "Personal Profile dashboard");
    container.append(style, root);

    let disposed = false;
    const isDisposed = () => disposed;

    // Load saved GitHub username
    let savedUsername = "";
    try {
      savedUsername = localStorage.getItem(STORAGE_KEY) || "";
    } catch {
      // localStorage unavailable
    }

    const state = {
      loading: false,
      loaded: false,
      error: null,
      lastUpdated: null,
      githubUsername: savedUsername,
      githubProfile: null,
      githubHeatmap: null,
      githubLoading: false,
      githubError: null,
      conversationHeatmap: null,
      llmUsage: null,
    };

    const refresh = async () => {
      if (disposed || state.loading) return;
      state.loading = true;
      state.error = null;
      render(root, state, host, () => void refresh());

      try {
        // Fetch conversations
        const conversations = await fetchAllConversations(host, isDisposed);
        if (disposed) return;

        // Build conversation activity counts by day
        const convCounts = {};
        for (const conv of conversations) {
          const timestamps = [
            parseTime(conv.created_at),
            parseTime(conv.updated_at),
            parseTime(conv.last_updated_at),
          ].filter((t) => t > 0);
          if (timestamps.length === 0) continue;
          // Count the most recent activity day
          const latest = Math.max(...timestamps);
          const key = dayKey(latest);
          if (key) convCounts[key] = (convCounts[key] || 0) + 1;
        }
        state.conversationHeatmap = buildHeatmap(convCounts);

        // Fetch events from up to 30 conversations for LLM usage
        const llmUsage = {
          totalTokens: 0,
          promptTokens: 0,
          completionTokens: 0,
          eventCount: 0,
          byModel: new Map(),
        };

        // Sort by updated_at desc, take most recent 30
        const sorted = [...conversations].sort(
          (a, b) => parseTime(b.updated_at) - parseTime(a.updated_at),
        );
        const sample = sorted.slice(0, 30);

        for (const conv of sample) {
          if (disposed) return;
          const events = await fetchConversationEvents(host, String(conv.id), isDisposed);
          if (disposed) return;
          for (const event of events) {
            const usage = extractLlmUsage(event);
            if (usage) {
              llmUsage.totalTokens += usage.total_tokens;
              llmUsage.promptTokens += usage.prompt_tokens;
              llmUsage.completionTokens += usage.completion_tokens;
              llmUsage.eventCount++;
              const model =
                event.llm_metrics?.model ??
                event.llm_message?.model ??
                event.model ??
                "unknown";
              const modelKey = String(model);
              llmUsage.byModel.set(
                modelKey,
                (llmUsage.byModel.get(modelKey) || 0) + usage.total_tokens,
              );
            }
          }
        }
        state.llmUsage = llmUsage;

        // Fetch GitHub data if username is set
        if (state.githubUsername) {
          state.githubLoading = true;
          state.githubError = null;
          render(root, state, host, () => void refresh());

          try {
            const [profile, events] = await Promise.all([
              fetchGitHubProfile(state.githubUsername),
              fetchGitHubEvents(state.githubUsername),
            ]);
            if (disposed) return;
            state.githubProfile = profile;

            // Build GitHub event counts by day
            const ghCounts = {};
            for (const event of events) {
              const timestamp = parseTime(event.created_at);
              if (timestamp <= 0) continue;
              const key = dayKey(timestamp);
              if (key) ghCounts[key] = (ghCounts[key] || 0) + 1;
            }
            state.githubHeatmap = buildHeatmap(ghCounts);
          } catch (error) {
            if (disposed) return;
            state.githubError =
              error instanceof Error ? error.message : "Failed to fetch GitHub data.";
          } finally {
            if (!disposed) state.githubLoading = false;
          }
        } else {
          state.githubProfile = null;
          state.githubHeatmap = null;
        }

        state.loaded = true;
        state.lastUpdated = new Date();
      } catch (error) {
        if (disposed) return;
        state.error =
          error instanceof Error
            ? error.message
            : "Failed to load activity data.";
      } finally {
        if (!disposed) {
          state.loading = false;
          render(root, state, host, () => void refresh());
        }
      }
    };

    render(root, state, host, () => void refresh());
    void refresh();
    const interval = window.setInterval(() => void refresh(), POLL_INTERVAL_MS);

    return () => {
      disposed = true;
      window.clearInterval(interval);
      root.remove();
      style.remove();
    };
  });
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const STYLE = `
  .personal-profile {
    --pp-bg: var(--oh-background, #0c0d0f);
    --pp-surface: var(--oh-surface, #1b1d22);
    --pp-surface-raised: var(--oh-surface-raised, #262930);
    --pp-surface-deep: var(--oh-surface-deep, #111216);
    --pp-text: var(--oh-foreground, #f4f4f5);
    --pp-text-secondary: var(--oh-text-secondary, #b6bac3);
    --pp-text-dim: var(--oh-text-dim, #777c88);
    --pp-border: var(--oh-border, #4b505c);
    --pp-border-subtle: var(--oh-border-subtle, #343842);
    --pp-accent: var(--oh-accent, #c9b974);
    --pp-radius: var(--oh-radius, 8px);
    --pp-green-1: #0e4429;
    --pp-green-2: #006d32;
    --pp-green-3: #26a641;
    --pp-green-4: #39d353;
    min-height: 100%; box-sizing: border-box;
    padding: clamp(1.25rem, 3vw, 2.5rem);
    color: var(--pp-text); background: var(--pp-bg);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }
  .personal-profile * { box-sizing: border-box; }
  .personal-profile button, .personal-profile input { font: inherit; }
  .pp-shell { width: min(1120px, 100%); margin: 0 auto; }
  .pp-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 1.5rem; margin-bottom: 1.5rem; }
  .pp-eyebrow { margin: 0 0 .4rem; color: var(--pp-accent); font-size: .7rem; font-weight: 750; letter-spacing: .14em; text-transform: uppercase; }
  .pp-title { margin: 0; font-size: clamp(1.75rem, 4vw, 2.75rem); line-height: 1; letter-spacing: -.035em; }
  .pp-subtitle { max-width: 44rem; margin: .75rem 0 0; color: var(--pp-text-secondary); font-size: .9rem; line-height: 1.55; }
  .pp-actions { display: flex; align-items: center; gap: .65rem; flex-wrap: wrap; justify-content: flex-end; }
  .pp-button { appearance: none; border: 1px solid var(--pp-border); border-radius: var(--pp-radius); padding: .55rem .8rem; color: var(--pp-text); background: var(--pp-surface); font-size: .78rem; font-weight: 650; cursor: pointer; transition: border-color 150ms, background 150ms, transform 150ms; }
  .pp-button:hover { border-color: color-mix(in srgb, var(--pp-accent) 65%, var(--pp-border)); background: var(--pp-surface-raised); }
  .pp-button:focus-visible { outline: 2px solid var(--oh-focus, #fff); outline-offset: 2px; }
  .pp-button:active { transform: translateY(1px); }
  .pp-button:disabled { opacity: .55; cursor: wait; }
  .pp-button--ghost { background: transparent; border-color: var(--pp-border-subtle); }
  .pp-loading { padding: 1.5rem; text-align: center; color: var(--pp-text-secondary); font-size: .85rem; }
  .pp-error { padding: 1rem; border: 1px solid color-mix(in srgb, #e76a5e 46%, var(--pp-border)); border-radius: var(--pp-radius); color: var(--pp-text-secondary); background: var(--pp-surface-deep); font-size: .8rem; margin: .5rem 0; }
  .pp-panel { border: 1px solid var(--pp-border-subtle); background: color-mix(in srgb, var(--pp-surface) 92%, transparent); border-radius: calc(var(--pp-radius) + 4px); padding: 1.1rem; margin-bottom: 1.25rem; }
  .pp-panel-title { margin: 0 0 .25rem; font-size: .95rem; font-weight: 700; }
  .pp-panel-copy { margin: 0 0 .85rem; color: var(--pp-text-dim); font-size: .74rem; line-height: 1.45; }
  .pp-settings-form { display: flex; gap: .5rem; flex-wrap: wrap; align-items: center; }
  .pp-input { flex: 1; min-width: 12rem; min-height: 2.25rem; border: 1px solid var(--pp-border-subtle); border-radius: var(--pp-radius); padding: .48rem .62rem; color: var(--pp-text); background: var(--pp-surface-deep); font-size: .82rem; }
  .pp-input:focus-visible { outline: 2px solid var(--oh-focus, #fff); outline-offset: 2px; }
  .pp-section { margin-bottom: 1.5rem; }
  .pp-section-title { margin: 0 0 .85rem; font-size: 1.15rem; font-weight: 700; letter-spacing: -.02em; }

  /* Heatmap */
  .pp-heatmap-wrapper { margin-bottom: 1.25rem; }
  .pp-heatmap-header { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; margin-bottom: .65rem; }
  .pp-heatmap-title { margin: 0; font-size: .95rem; font-weight: 700; }
  .pp-heatmap-stats { margin: 0; color: var(--pp-text-dim); font-size: .72rem; }
  .pp-heatmap-scroll { overflow-x: auto; padding-bottom: .3rem; }
  .pp-heatmap-grid { display: inline-flex; flex-direction: column; gap: .25rem; min-width: max-content; }
  .pp-heatmap-months { display: flex; gap: 3px; padding-left: 2.2rem; height: 1rem; }
  .pp-heatmap-month-cell { width: 12px; font-size: .6rem; color: var(--pp-text-dim); white-space: nowrap; }
  .pp-heatmap-body { display: flex; gap: .2rem; }
  .pp-heatmap-day-labels { display: flex; flex-direction: column; gap: 3px; justify-content: flex-start; }
  .pp-heatmap-day-label { height: 12px; font-size: .6rem; line-height: 12px; color: var(--pp-text-dim); white-space: nowrap; }
  .pp-heatmap-weeks { display: flex; gap: 3px; }
  .pp-heatmap-week { display: flex; flex-direction: column; gap: 3px; }
  .pp-heatmap-cell { width: 12px; height: 12px; border-radius: 2px; transition: opacity 120ms; }
  .pp-heatmap-cell:hover { opacity: .75; }
  .pp-heatmap-cell--level-0 { background: var(--pp-surface-deep); border: 1px solid var(--pp-border-subtle); }
  .pp-heatmap-cell--level-1 { background: var(--pp-green-1, #0e4429); }
  .pp-heatmap-cell--level-2 { background: var(--pp-green-2, #006d32); }
  .pp-heatmap-cell--level-3 { background: var(--pp-green-3, #26a641); }
  .pp-heatmap-cell--level-4 { background: var(--pp-green-4, #39d353); }
  .pp-heatmap-cell--future { opacity: .35; }
  .pp-heatmap-legend { display: flex; align-items: center; gap: 4px; justify-content: flex-end; margin-top: .5rem; }
  .pp-heatmap-legend-label { font-size: .6rem; color: var(--pp-text-dim); }

  /* LLM stats */
  .pp-stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .8rem; }
  .pp-stat-card { min-height: 6rem; padding: .85rem; border: 1px solid var(--pp-border-subtle); border-radius: calc(var(--pp-radius) + 2px); background: var(--pp-surface-deep); }
  .pp-stat-label { margin: 0; color: var(--pp-text-dim); font-size: .65rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
  .pp-stat-value { margin: .5rem 0 .2rem; font-size: clamp(1.1rem, 2.5vw, 1.5rem); font-weight: 720; line-height: 1.1; }
  .pp-stat-detail { margin: 0; color: var(--pp-text-secondary); font-size: .7rem; line-height: 1.4; }
  .pp-model-list { margin-top: .85rem; }
  .pp-model-list-title { margin: 0 0 .4rem; font-size: .75rem; font-weight: 700; color: var(--pp-text-secondary); }
  .pp-model-row { display: flex; justify-content: space-between; gap: .5rem; padding: .4rem 0; border-bottom: 1px solid var(--pp-border-subtle); font-size: .76rem; }
  .pp-model-name { color: var(--pp-text); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .72rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pp-model-tokens { color: var(--pp-text-dim); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .72rem; white-space: nowrap; }

  /* GitHub profile */
  .pp-gh-profile { display: flex; gap: 1rem; align-items: flex-start; padding: 1rem; border: 1px solid var(--pp-border-subtle); border-radius: var(--pp-radius); background: var(--pp-surface-deep); margin-bottom: 1rem; }
  .pp-gh-avatar { border-radius: 50%; flex-shrink: 0; border: 2px solid var(--pp-border-subtle); }
  .pp-gh-info { min-width: 0; flex: 1; }
  .pp-gh-name { margin: 0; font-size: 1rem; font-weight: 700; }
  .pp-gh-login { margin: .15rem 0 0; color: var(--pp-text-dim); font-size: .8rem; }
  .pp-gh-bio { margin: .5rem 0 0; color: var(--pp-text-secondary); font-size: .8rem; line-height: 1.45; }
  .pp-gh-stats { display: flex; flex-wrap: wrap; gap: .5rem .8rem; margin-top: .5rem; }
  .pp-gh-stat { font-size: .72rem; color: var(--pp-text-dim); }
  .pp-gh-joined { margin: .4rem 0 0; font-size: .68rem; color: var(--pp-text-dim); }

  /* Footer */
  .pp-footer { display: flex; justify-content: space-between; gap: 1rem; margin-top: 1.25rem; color: var(--pp-text-dim); font-size: .67rem; }

  @media (max-width: 700px) {
    .pp-header { flex-direction: column; }
    .pp-actions { justify-content: flex-start; }
    .pp-stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .pp-gh-profile { flex-direction: column; align-items: center; text-align: center; }
    .pp-gh-stats { justify-content: center; }
  }
  @media (max-width: 480px) {
    .pp-stats-grid { grid-template-columns: 1fr; }
  }
  @media (prefers-reduced-motion: reduce) {
    .pp-button, .pp-heatmap-cell { transition: none; }
  }
`;
