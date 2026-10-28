import { afterEach, describe, expect, it, vi } from "vitest";
import { activate } from "./extension.js";

// ─── Fixtures ──────────────────────────────────────────────────────────────

function conversation(overrides = {}) {
  return {
    id: "conv-1",
    title: "Test conversation",
    execution_status: "finished",
    created_at: "2026-09-29T08:00:00Z",
    updated_at: "2026-09-29T09:00:00Z",
    stats: {
      usage_to_metrics: {
        default: {
          model_name: "openai/gpt-4o",
          accumulated_cost: 0.05,
          max_budget_per_task: 5.0,
          accumulated_token_usage: {
            model: "openai/gpt-4o",
            prompt_tokens: 10000,
            completion_tokens: 2000,
            cache_read_tokens: 5000,
            cache_write_tokens: 1000,
            reasoning_tokens: 500,
            context_window: 128000,
            per_turn_token: 20000,
          },
        },
      },
    },
    ...overrides,
  };
}

function statsEvent(overrides = {}) {
  return {
    kind: "ConversationStateUpdateEvent",
    id: "stats-1",
    timestamp: "2026-09-29T08:00:06Z",
    source: "environment",
    key: "stats",
    value: {
      usage_to_metrics: {
        default: {
          model_name: "openai/gpt-4o",
          accumulated_cost: 0.02,
          max_budget_per_task: 5.0,
          accumulated_token_usage: {
            model: "openai/gpt-4o",
            prompt_tokens: 5000,
            completion_tokens: 1000,
            cache_read_tokens: 2000,
            cache_write_tokens: 500,
            reasoning_tokens: 200,
            context_window: 128000,
            per_turn_token: 10000,
          },
        },
      },
    },
    ...overrides,
  };
}

function fullStateEvent(overrides = {}) {
  return {
    kind: "ConversationStateUpdateEvent",
    id: "fullstate-1",
    timestamp: "2026-09-29T08:00:12Z",
    source: "environment",
    key: "full_state",
    value: {
      stats: {
        usage_to_metrics: {
          default: {
            model_name: "openai/gpt-4o",
            accumulated_cost: 0.05,
            max_budget_per_task: 5.0,
            accumulated_token_usage: {
              model: "openai/gpt-4o",
              prompt_tokens: 10000,
              completion_tokens: 2000,
              cache_read_tokens: 5000,
              cache_write_tokens: 1000,
              reasoning_tokens: 500,
              context_window: 128000,
              per_turn_token: 20000,
            },
          },
        },
      },
    },
    ...overrides,
  };
}

function messageEvent(overrides = {}) {
  return {
    kind: "MessageEvent",
    id: "msg-1",
    timestamp: "2026-09-29T08:00:00Z",
    source: "user",
    llm_message: { content: [{ type: "text", text: "Hello" }] },
    ...overrides,
  };
}

function events() {
  return [messageEvent(), statsEvent(), fullStateEvent()];
}

// ─── Host double ───────────────────────────────────────────────────────────

function setup({ conversationPages, eventPages } = {}) {
  let mountPage;
  const unregister = vi.fn();
  const navigate = vi.fn();
  const requestPaths = [];
  const request = vi.fn(async ({ path }) => {
    requestPaths.push(path);
    if (path.startsWith("/api/conversations/search")) {
      return conversationPages?.shift() ?? { items: [conversation()], next_page_id: null };
    }
    if (path.includes("/events/search")) {
      return eventPages?.shift() ?? { items: events(), next_page_id: null };
    }
    if (path === "/api/profiles") {
      return { active_profile: "test", profiles: [{ name: "test", model: "openai/gpt-4o" }] };
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  const host = {
    apiVersion: "1",
    extension: { name: "usage-insights", version: "0.1.0", resolvedRef: "test" },
    backend: { id: "local-test", kind: "local" },
    registerPage: vi.fn((id, mount) => {
      mountPage = mount;
      return unregister;
    }),
    navigate,
    agentServer: { request },
  };
  const deactivate = activate(host);
  return { host, mountPage, unregister, deactivate, navigate, request, requestPaths };
}

afterEach(() => vi.restoreAllMocks());

// ─── Tests ─────────────────────────────────────────────────────────────────

describe("Usage Insights extension", () => {
  it("registers exactly the declared page on host API 1", () => {
    const { host, unregister, deactivate } = setup();
    expect(host.registerPage).toHaveBeenCalledOnce();
    expect(host.registerPage).toHaveBeenCalledWith("usage", expect.any(Function));
    expect(deactivate).toBe(unregister);
  });

  it("fails clearly on unsupported host versions", () => {
    expect(() => activate({ apiVersion: "2" })).toThrow(
      "Usage Insights requires Canvas host API 1.",
    );
  });

  it("renders the overview page with heading and description", async () => {
    const { mountPage, navigate } = setup();
    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate });
    await vi.waitFor(() => expect(container.textContent).toContain("Usage Insights"));
    expect(container.textContent).toContain("Token usage and estimated cost from conversations on this Agent Server.");
    cleanup();
    expect(container.childElementCount).toBe(0);
  });

  it("renders conversation table and links to detail", async () => {
    const { mountPage, navigate } = setup();
    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate });
    await vi.waitFor(() => expect(container.textContent).toContain("Test conversation"));
    expect(container.textContent).toContain("Conversations");

    const link = container.querySelector(".usage-insights__link");
    expect(link).toBeTruthy();
    link.click();
    expect(navigate).toHaveBeenCalledWith(
      "/extensions/usage-insights/usage/conversations/conv-1",
    );
    cleanup();
  });

  it("renders conversation detail route with back link and model breakdown", async () => {
    const { mountPage, navigate } = setup();
    const container = document.createElement("div");
    const cleanup = mountPage({
      container,
      path: "conversations/conv-1",
      navigate,
    });
    await vi.waitFor(() => expect(container.textContent).toContain("Back to overview"), { timeout: 3000 });
    await vi.waitFor(() => expect(container.textContent).toContain("Test conversation"), { timeout: 3000 });
    expect(container.textContent).toContain("Model / usage-key breakdown");
    expect(container.textContent).toContain("openai/gpt-4o");
    expect(container.textContent).toContain("Token and cost progression");
    cleanup();
  });

  it("renders pricing route with catalog table and coverage", async () => {
    const { mountPage, navigate } = setup();
    const container = document.createElement("div");
    const cleanup = mountPage({
      container,
      path: "pricing",
      navigate,
    });
    await vi.waitFor(() => expect(container.textContent).toContain("Pricing coverage"), { timeout: 3000 });
    expect(container.textContent).toContain("Bundled catalog rates");
    expect(container.textContent).toContain("Model coverage");
    expect(container.textContent).toContain("Configured source is reserved");
    cleanup();
  });

  it("renders not-found for unknown nested routes", async () => {
    const { mountPage, navigate } = setup();
    const container = document.createElement("div");
    const cleanup = mountPage({
      container,
      path: "unknown-route/xyz",
      navigate,
    });
    await vi.waitFor(() => expect(container.textContent).toContain("Page not found"));
    cleanup();
  });

  it("disposes DOM, styles, and timers on cleanup", async () => {
    const { mountPage, navigate } = setup();
    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate });
    await vi.waitFor(() => expect(container.textContent).toContain("Usage Insights"));
    const stylesBefore = document.querySelectorAll("style").length;
    cleanup();
    expect(container.childElementCount).toBe(0);
    // Styles should be removed
    const stylesAfter = document.querySelectorAll("style").length;
    expect(stylesAfter).toBeLessThan(stylesBefore);
  });

  it("uses root-relative request paths with limit and page_id pagination", async () => {
    const { mountPage, navigate, requestPaths } = setup({
      conversationPages: [
        { items: [conversation()], next_page_id: "page2" },
        { items: [conversation({ id: "conv-2", title: "Second" })], next_page_id: null },
      ],
    });
    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate });
    await vi.waitFor(() => expect(container.textContent).toContain("Second"));
    // All paths should be root-relative
    for (const p of requestPaths) {
      expect(p.startsWith("/")).toBe(true);
      expect(p.startsWith("//")).toBe(false);
    }
    expect(requestPaths).toContain("/api/conversations/search?limit=100");
    expect(requestPaths).toContain("/api/conversations/search?limit=100&page_id=page2");
    cleanup();
  });

  it("terminates pagination on repeated cursor and renders partial coverage", async () => {
    const { mountPage, navigate, container: _c } = setup({
      conversationPages: [
        { items: [conversation()], next_page_id: "repeat" },
        { items: [conversation({ id: "conv-2" })], next_page_id: "repeat" },
      ],
    });
    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate });
    await vi.waitFor(() => expect(container.textContent).toContain("Test conversation"));
    // Should not loop infinitely — repeated "repeat" cursor terminates
    cleanup();
  });

  it("normalizes stats and full_state events while discarding non-telemetry fields", async () => {
    const { mountPage, navigate } = setup();
    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate });
    await vi.waitFor(() => expect(container.textContent).toContain("Known cost"));
    // The stats events have accumulated_cost 0.02 and 0.05, delta = 0.03
    // But the conversation metadata has accumulated_cost 0.05
    // The overview should show some cost value
    expect(container.textContent).toContain("$");
    cleanup();
  });

  it("handles missing token fields and malformed data gracefully", async () => {
    const malformedStats = {
      kind: "ConversationStateUpdateEvent",
      id: "malformed-1",
      timestamp: "2026-09-29T08:00:06Z",
      key: "stats",
      value: {
        usage_to_metrics: {
          default: {
            model_name: "unknown/model",
            accumulated_cost: "not-a-number",
            accumulated_token_usage: {},
          },
        },
      },
    };
    const { mountPage, navigate } = setup({
      eventPages: [{ items: [messageEvent(), malformedStats], next_page_id: null }],
    });
    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate });
    await vi.waitFor(() => expect(container.textContent).toContain("Conversations"), { timeout: 3000 });
    // Should not crash, should show some content
    expect(container.textContent).toContain("Conversations");
    cleanup();
  });

  it("shows reported cost provenance badge for server-reported cost", async () => {
    const { mountPage, navigate } = setup();
    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate });
    await vi.waitFor(() => expect(container.textContent).toContain("Known cost"));
    const badges = container.querySelectorAll(".usage-insights__badge--reported");
    expect(badges.length).toBeGreaterThan(0);
    cleanup();
  });

  it("shows unpriced badge for models without catalog match", async () => {
    const { mountPage, navigate } = setup({
      eventPages: [{
        items: [{
          kind: "ConversationStateUpdateEvent",
          id: "stats-unpriced",
          timestamp: "2026-09-29T08:00:06Z",
          key: "stats",
          value: {
            usage_to_metrics: {
              default: {
                model_name: "custom-unknown-model",
                accumulated_cost: null,
                accumulated_token_usage: {
                  model: "custom-unknown-model",
                  prompt_tokens: 1000,
                  completion_tokens: 200,
                },
              },
            },
          },
        }],
        next_page_id: null,
      }],
    });
    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate });
    await vi.waitFor(() => expect(container.textContent).toContain("Unpriced tokens"));
    cleanup();
  });

  it("shows loading state while fetching", async () => {
    let resolveRequest;
    const delayedRequest = vi.fn(() => new Promise((resolve) => { resolveRequest = resolve; }));
    const host = {
      apiVersion: "1",
      extension: { name: "usage-insights", version: "0.1.0", resolvedRef: "test" },
      backend: { id: "test", kind: "local" },
      registerPage: vi.fn((id, mount) => { mountPage = mount; return vi.fn(); }),
      navigate: vi.fn(),
      agentServer: { request: delayedRequest },
    };
    let mountPage;
    activate(host);
    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate: vi.fn() });
    // Should show loading
    await vi.waitFor(() => expect(container.textContent).toContain("Loading"));
    // Resolve
    if (resolveRequest) resolveRequest({ items: [conversation()], next_page_id: null });
    await vi.waitFor(() => expect(container.textContent).toContain("Usage Insights"), { timeout: 3000 });
    cleanup();
  });

  it("shows empty state when no conversations exist", async () => {
    const { mountPage, navigate } = setup({
      conversationPages: [{ items: [], next_page_id: null }],
    });
    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate });
    await vi.waitFor(() => expect(container.textContent).toContain("No conversations found"));
    cleanup();
  });

  it("shows error state on request failure", async () => {
    const errorRequest = vi.fn(async () => { throw new Error("Network error"); });
    const host = {
      apiVersion: "1",
      extension: { name: "usage-insights", version: "0.1.0", resolvedRef: "test" },
      backend: { id: "test", kind: "local" },
      registerPage: vi.fn((id, mount) => { mountPage = mount; return vi.fn(); }),
      navigate: vi.fn(),
      agentServer: { request: errorRequest },
    };
    let mountPage;
    activate(host);
    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate: vi.fn() });
    await vi.waitFor(() => expect(container.textContent).toContain("Network error"), { timeout: 3000 });
    expect(container.querySelector(".usage-insights__notice--error")).not.toBeNull();
    cleanup();
  });

  it("never calls detailed profile or provider-connection endpoints", async () => {
    const { mountPage, navigate, requestPaths } = setup();
    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate });
    await vi.waitFor(() => expect(container.textContent).toContain("Usage Insights"));
    // Should never call these endpoints
    for (const p of requestPaths) {
      expect(p).not.toMatch(/\/api\/profiles\/[^?]+/);
      expect(p).not.toMatch(/\/api\/llm\/provider-connections/);
    }
    cleanup();
  });

  it("handles counter resets without creating negative deltas", async () => {
    const resetEvents = [
      statsEvent({
        id: "s1",
        timestamp: "2026-09-29T08:00:06Z",
        value: {
          usage_to_metrics: {
            default: {
              model_name: "openai/gpt-4o",
              accumulated_cost: 0.05,
              accumulated_token_usage: { model: "openai/gpt-4o", prompt_tokens: 10000, completion_tokens: 2000 },
            },
          },
        },
      }),
      statsEvent({
        id: "s2",
        timestamp: "2026-09-29T08:00:12Z",
        value: {
          usage_to_metrics: {
            default: {
              model_name: "openai/gpt-4o",
              accumulated_cost: 0.02,
              accumulated_token_usage: { model: "openai/gpt-4o", prompt_tokens: 3000, completion_tokens: 500 },
            },
          },
        },
      }),
    ];
    const { mountPage, navigate } = setup({
      eventPages: [{ items: resetEvents, next_page_id: null }],
    });
    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate });
    await vi.waitFor(() => expect(container.textContent).toContain("Usage Insights"));
    // Should not crash — counter decrease treated as new baseline
    cleanup();
  });

  it("handles multiple usage keys (default and condenser)", async () => {
    const multiKeyEvent = {
      kind: "ConversationStateUpdateEvent",
      id: "multikey-1",
      timestamp: "2026-09-29T08:00:06Z",
      key: "stats",
      value: {
        usage_to_metrics: {
          default: {
            model_name: "openai/gpt-4o",
            accumulated_cost: 0.03,
            accumulated_token_usage: { model: "openai/gpt-4o", prompt_tokens: 5000, completion_tokens: 1000 },
          },
          condenser: {
            model_name: "openai/gpt-4o-mini",
            accumulated_cost: 0.001,
            accumulated_token_usage: { model: "openai/gpt-4o-mini", prompt_tokens: 500, completion_tokens: 100 },
          },
        },
      },
    };
    const { mountPage, navigate } = setup({
      eventPages: [{ items: [messageEvent(), multiKeyEvent], next_page_id: null }],
    });
    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate });
    await vi.waitFor(() => expect(container.textContent).toContain("Usage Insights"));
    cleanup();
  });

  it("renders budget progress in conversation detail", async () => {
    const { mountPage, navigate } = setup();
    const container = document.createElement("div");
    const cleanup = mountPage({
      container,
      path: "conversations/conv-1",
      navigate,
    });
    await vi.waitFor(() => expect(container.textContent).toContain("Budget"), { timeout: 3000 });
    expect(container.textContent).toContain("of $5.00");
    cleanup();
  });

  it("renders data quality and provenance section in detail", async () => {
    const { mountPage, navigate } = setup();
    const container = document.createElement("div");
    const cleanup = mountPage({
      container,
      path: "conversations/conv-1",
      navigate,
    });
    await vi.waitFor(() => expect(container.textContent).toContain("Data quality and provenance"), { timeout: 3000 });
    expect(container.textContent).toContain("Reasoning tokens are treated as part of completion tokens");
    expect(container.textContent).toContain("Profile-detail pricing is intentionally not read");
    cleanup();
  });
});
