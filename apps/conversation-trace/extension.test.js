import { afterEach, describe, expect, it, vi } from "vitest";
import { activate } from "./extension.js";

function conversation(overrides = {}) {
  return {
    id: "conversation-1",
    title: "Trace the failing build",
    execution_status: "finished",
    created_at: "2026-08-28T08:00:00Z",
    updated_at: "2026-08-28T08:01:00Z",
    agent: { llm: { model: "openai/example" } },
    ...overrides,
  };
}

function statsEvent(overrides = {}) {
  return {
    kind: "ConversationStateUpdateEvent",
    id: "stats-1",
    timestamp: "2026-08-28T08:00:06Z",
    source: "environment",
    key: "stats",
    value: {
      usage_to_metrics: {
        default: {
          model_name: "openai/gpt-4",
          accumulated_cost: 0.0834,
          max_budget_per_task: 5.0,
          accumulated_token_usage: {
            model: "openai/gpt-4",
            prompt_tokens: 15200,
            completion_tokens: 3400,
            cache_read_tokens: 8100,
            cache_write_tokens: 2100,
            reasoning_tokens: 1200,
            context_window: 128000,
            per_turn_token: 42000,
            response_id: "resp-1",
          },
          costs: [{ model: "openai/gpt-4", cost: 0.0834, timestamp: 1693209606 }],
          response_latencies: [{ model: "openai/gpt-4", latency: 1200, response_id: "resp-1" }],
          token_usages: [],
        },
        condenser: {
          model_name: "openai/gpt-4-mini",
          accumulated_cost: 0.0042,
          max_budget_per_task: null,
          accumulated_token_usage: {
            model: "openai/gpt-4-mini",
            prompt_tokens: 3200,
            completion_tokens: 800,
            cache_read_tokens: 1500,
            cache_write_tokens: 400,
            reasoning_tokens: 0,
            context_window: 64000,
            per_turn_token: 12000,
            response_id: "resp-2",
          },
          costs: [{ model: "openai/gpt-4-mini", cost: 0.0042, timestamp: 1693209606 }],
          response_latencies: [],
          token_usages: [],
        },
      },
    },
    ...overrides,
  };
}

function events() {
  return [
    {
      kind: "MessageEvent",
      id: "message-1",
      timestamp: "2026-08-28T08:00:00Z",
      source: "user",
      llm_message: { content: [{ type: "text", text: "Find the broken test" }] },
    },
    {
      kind: "ActionEvent",
      id: "action-1",
      timestamp: "2026-08-28T08:00:01Z",
      source: "agent",
      tool_name: "terminal",
      tool_call_id: "call-1",
      summary: "Run the focused test suite",
      security_risk: "LOW",
      action: { kind: "TerminalAction", command: "npm test" },
    },
    {
      kind: "ObservationEvent",
      id: "observation-1",
      timestamp: "2026-08-28T08:00:03Z",
      source: "environment",
      tool_name: "terminal",
      tool_call_id: "call-1",
      action_id: "action-1",
      observation: {
        kind: "TerminalObservation",
        command: "npm test",
        exit_code: 1,
        is_error: true,
        timeout: false,
        content: [{ type: "text", text: "1 test failed" }],
      },
    },
    {
      kind: "ObservationEvent",
      id: "file-1",
      timestamp: "2026-08-28T08:00:04Z",
      source: "environment",
      tool_name: "file_editor",
      tool_call_id: "call-2",
      action_id: "action-2",
      observation: {
        kind: "FileEditorObservation",
        command: "str_replace",
        path: "/workspace/example.js",
        output: "Updated example.js",
        old_content: "broken",
        new_content: "fixed",
        error: null,
      },
    },
    {
      kind: "UserRejectObservation",
      id: "reject-1",
      timestamp: "2026-08-28T08:00:05Z",
      source: "environment",
      tool_name: "terminal",
      tool_call_id: "call-3",
      action_id: "action-3",
      rejection_reason: "Command was not approved",
      rejection_source: "user",
    },
    statsEvent(),
  ];
}

function setup({ conversationPages, eventPages } = {}) {
  let mountPage;
  const unregister = vi.fn();
  const navigate = vi.fn();
  const request = vi.fn(async ({ path }) => {
    if (path.startsWith("/api/conversations/search")) {
      return conversationPages?.shift() ?? { items: [conversation()], next_page_id: null };
    }
    if (path.includes("/events/search")) {
      return eventPages?.shift() ?? { items: events(), next_page_id: null };
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  const host = {
    apiVersion: "1",
    extension: { name: "conversation-trace", version: "0.1.0", resolvedRef: "test" },
    backend: { id: "local-test", kind: "local", orgId: null },
    registerPage: vi.fn((id, mount) => {
      mountPage = mount;
      return unregister;
    }),
    navigate,
    agentServer: { request },
  };
  const deactivate = activate(host);
  return { host, mountPage, unregister, deactivate, navigate, request };
}

afterEach(() => vi.restoreAllMocks());

describe("Conversation Trace extension", () => {
  it("registers its page, lists conversations, and navigates to a selected trace", async () => {
    const { host, mountPage, unregister, deactivate, navigate, request } = setup();
    expect(host.registerPage).toHaveBeenCalledOnce();
    expect(host.registerPage).toHaveBeenCalledWith("trace", expect.any(Function));
    expect(deactivate).toBe(unregister);

    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate });
    await vi.waitFor(() => expect(container.textContent).toContain("Trace the failing build"));
    expect(request).toHaveBeenCalledWith({ path: "/api/conversations/search?limit=100" });
    expect(container.textContent).toContain("Choose a conversation");

    container.querySelector(".conversation-trace__conversation").click();
    expect(navigate).toHaveBeenCalledWith(
      "/extensions/conversation-trace/trace/conversations/conversation-1",
    );

    cleanup();
    expect(container.childElementCount).toBe(0);
  });

  it("renders a chronological categorized trace and detailed event inspector", async () => {
    const { mountPage, navigate, request } = setup();
    const container = document.createElement("div");
    const cleanup = mountPage({
      container,
      path: "conversations/conversation-1",
      navigate,
    });

    await vi.waitFor(() => expect(container.textContent).toContain("Run the focused test suite"));
    expect(request).toHaveBeenCalledWith({
      path: "/api/conversations/conversation-1/events/search?limit=100",
    });
    expect(container.textContent).toContain("Tool calls");
    expect(container.textContent).toContain("File events");
    expect(container.textContent).toContain("Approval 1");
    expect(container.textContent).toContain("2.0 s");

    // Token usage panel
    expect(container.textContent).toContain("Total cost");
    expect(container.textContent).toContain("$0.0876");
    expect(container.textContent).toContain("18.4k");
    expect(container.textContent).toContain("4.2k");
    expect(container.textContent).toContain("$5.0000 budget");
    expect(container.textContent).toContain("openai/gpt-4");
    expect(container.textContent).toContain("openai/gpt-4-mini");

    // Stats event shows cost badge in timeline
    const statsEntry = Array.from(container.querySelectorAll(".conversation-trace__event"))
      .find((node) => node.textContent.includes("Usage stats"));
    expect(statsEntry).toBeDefined();
    expect(statsEntry.textContent).toContain("$0.0876");

    // Clicking the stats event shows token usage in inspector
    statsEntry.click();
    expect(container.querySelector(".conversation-trace__inspector").textContent)
      .toContain("Token usage");
    expect(container.querySelector(".conversation-trace__inspector").textContent)
      .toContain("Prompt: 18.4k");

    const fileEvent = Array.from(container.querySelectorAll(".conversation-trace__event"))
      .find((node) => node.textContent.includes("/workspace/example.js"));
    expect(fileEvent).toBeDefined();
    fileEvent.click();
    expect(container.querySelector(".conversation-trace__inspector").textContent)
      .toContain("/workspace/example.js");
    expect(container.querySelector(".conversation-trace__inspector").textContent)
      .toContain('"kind": "ObservationEvent"');

    // Token usage is always shown in the inspector, even for non-stats events
    expect(container.querySelector(".conversation-trace__inspector").textContent)
      .toContain("Token usage");
    expect(container.querySelector(".conversation-trace__inspector").textContent)
      .toContain("Cost: $0.0876");

    // Events before any stats event still show usage (falls back to latest)
    const messageEvent = Array.from(container.querySelectorAll(".conversation-trace__event"))
      .find((node) => node.textContent.includes("User message"));
    expect(messageEvent).toBeDefined();
    messageEvent.click();
    expect(container.querySelector(".conversation-trace__inspector").textContent)
      .toContain("Token usage");
    expect(container.querySelector(".conversation-trace__inspector").textContent)
      .toContain("Prompt: 18.4k");

    const search = container.querySelector('[aria-label="Search trace"]');
    search.value = "not approved";
    search.dispatchEvent(new Event("input", { bubbles: true }));
    expect(container.querySelectorAll(".conversation-trace__event")).toHaveLength(1);
    expect(container.textContent).toContain("Command was not approved");

    cleanup();
  });

  it("walks pagination and renders malformed-response errors safely", async () => {
    const paginated = setup({
      conversationPages: [
        { items: [conversation()], next_page_id: "next" },
        { items: [conversation({ id: "conversation-2", title: "Second run" })], next_page_id: null },
      ],
    });
    const container = document.createElement("div");
    const cleanup = paginated.mountPage({ container, path: "", navigate: paginated.navigate });
    await vi.waitFor(() => expect(container.textContent).toContain("Second run"));
    expect(paginated.request).toHaveBeenCalledWith({
      path: "/api/conversations/search?limit=100&page_id=next",
    });
    cleanup();

    const malformed = setup({ conversationPages: [{ unexpected: true }] });
    const malformedContainer = document.createElement("div");
    const malformedCleanup = malformed.mountPage({
      container: malformedContainer,
      path: "",
      navigate: malformed.navigate,
    });
    await vi.waitFor(() => expect(malformedContainer.textContent).toContain("unexpected response"));
    expect(malformedContainer.querySelector(".conversation-trace__notice--error")).not.toBeNull();
    malformedCleanup();
  });

  it("shows token usage placeholder when no stats events exist", async () => {
    const noStatsEvents = [
      {
        kind: "MessageEvent",
        id: "msg-no-stats",
        timestamp: "2026-08-28T08:00:00Z",
        source: "user",
        llm_message: { content: [{ type: "text", text: "Hello" }] },
      },
    ];
    const { mountPage, navigate } = setup({
      eventPages: [{ items: noStatsEvents, next_page_id: null }],
    });
    const container = document.createElement("div");
    const cleanup = mountPage({
      container,
      path: "conversations/conversation-1",
      navigate,
    });
    await vi.waitFor(() => expect(container.textContent).toContain("Hello"));

    // No usage panel rendered
    expect(container.querySelector(".conversation-trace__usage")).toBeNull();

    // Inspector still shows a Token usage section with placeholder text
    const event = container.querySelector(".conversation-trace__event");
    expect(event).toBeDefined();
    event.click();
    expect(container.querySelector(".conversation-trace__inspector").textContent)
      .toContain("No usage data available");

    cleanup();
  });

  it("fails clearly on unsupported host versions", () => {
    expect(() => activate({ apiVersion: "2" })).toThrow(
      "Conversation Trace requires Canvas host API 1.",
    );
  });
});
