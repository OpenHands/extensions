import { describe, expect, it, vi, beforeEach } from "vitest";
import { activate } from "./extension.js";

function makeHost(overrides = {}) {
  let mountPage;
  const unregister = vi.fn();
  const navigate = vi.fn();
  const request = vi.fn().mockResolvedValue({ items: [], next_page_id: null });
  const host = {
    apiVersion: "1",
    extension: { name: "personal-profile", version: "0.1.0", resolvedRef: "test" },
    backend: { id: "local-test", kind: "local", orgId: null },
    registerPage: vi.fn((id, mount) => {
      expect(id).toBe("profile");
      mountPage = mount;
      return unregister;
    }),
    navigate,
    agentServer: { request },
    ...overrides,
  };
  return { host, getMount: () => mountPage, navigate, request, unregister };
}

function makeConversation(id, updatedAt) {
  return {
    id,
    title: `Conversation ${id}`,
    created_at: updatedAt,
    updated_at: updatedAt,
  };
}

describe("Personal Profile extension", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("rejects unsupported host API versions", () => {
    const host = { apiVersion: "2", registerPage: vi.fn() };
    expect(() => activate(host)).toThrow(/host API 1/);
  });

  it("registers the profile page and returns cleanup", () => {
    const { host, unregister } = makeHost();
    const deactivate = activate(host);
    expect(deactivate).toBe(unregister);
    deactivate();
    expect(unregister).toHaveBeenCalled();
  });

  it("renders loading state then conversation heatmap from fetched data", async () => {
    const today = new Date();
    today.setHours(12, 0, 0, 0);
    const iso = today.toISOString();

    const request = vi.fn().mockResolvedValue({
      items: [makeConversation("conv-1", iso)],
      next_page_id: null,
    });
    const { host, getMount } = makeHost({
      agentServer: { request },
    });

    activate(host);
    const container = document.createElement("div");
    const cleanup = getMount()({ container, path: "", navigate: vi.fn() });

    await vi.waitFor(() => {
      expect(container.textContent).toContain("OpenHands Conversations");
    });

    expect(request).toHaveBeenCalledWith(
      expect.objectContaining({ path: expect.stringContaining("/api/conversations/search") }),
    );
    expect(container.textContent).toContain("1 contribution");

    cleanup();
    expect(container.childElementCount).toBe(0);
  });

  it("aggregates LLM usage from conversation events", async () => {
    const { host, getMount } = makeHost({
      agentServer: {
        request: vi.fn().mockImplementation((req) => {
          if (req.path.includes("/api/conversations/search")) {
            return Promise.resolve({
              items: [makeConversation("conv-1", new Date().toISOString())],
              next_page_id: null,
            });
          }
          if (req.path.includes("/events/search")) {
            return Promise.resolve({
              items: [
                {
                  id: "evt-1",
                  kind: "ObservationEvent",
                  timestamp: new Date().toISOString(),
                  llm_metrics: {
                    model: "gpt-4",
                    usage: { prompt_tokens: 100, completion_tokens: 50, total_tokens: 150 },
                  },
                },
                {
                  id: "evt-2",
                  kind: "ObservationEvent",
                  timestamp: new Date().toISOString(),
                  llm_metrics: {
                    model: "claude-3",
                    usage: { prompt_tokens: 200, completion_tokens: 80, total_tokens: 280 },
                  },
                },
              ],
              next_page_id: null,
            });
          }
          return Promise.resolve({ items: [], next_page_id: null });
        }),
      },
    });

    activate(host);
    const container = document.createElement("div");
    const cleanup = getMount()({ container, path: "", navigate: vi.fn() });

    await vi.waitFor(() => {
      expect(container.textContent).toContain("LLM Usage");
    });

    // 150 + 280 = 430 total tokens
    expect(container.textContent).toContain("430");
    expect(container.textContent).toContain("gpt-4");
    expect(container.textContent).toContain("claude-3");

    cleanup();
  });

  it("saves and loads GitHub username from localStorage", async () => {
    localStorage.setItem("personal-profile:github-username", "octocat");
    vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
      if (url.includes("/users/octocat")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              login: "octocat",
              name: "The Octocat",
              avatar_url: "https://github.com/octocat.png",
              public_repos: 8,
              followers: 5000,
              following: 9,
              created_at: "2011-01-25T18:44:36Z",
            }),
        });
      }
      if (url.includes("/users/octocat/events")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve([
              { id: "e1", type: "PushEvent", created_at: new Date().toISOString() },
            ]),
        });
      }
      return Promise.reject(new Error("Unexpected fetch"));
    });

    const { host, getMount } = makeHost();
    activate(host);
    const container = document.createElement("div");
    const cleanup = getMount()({ container, path: "", navigate: vi.fn() });

    await vi.waitFor(() => {
      expect(container.textContent).toContain("GitHub Activity");
    });

    expect(container.textContent).toContain("The Octocat");
    expect(container.textContent).toContain("@octocat");
    expect(container.textContent).toContain("GitHub Contributions");

    cleanup();
    vi.restoreAllMocks();
  });

  it("handles GitHub API errors gracefully", async () => {
    localStorage.setItem("personal-profile:github-username", "baduser");
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: () => Promise.resolve({ message: "Not Found" }),
    });

    const { host, getMount } = makeHost();
    activate(host);
    const container = document.createElement("div");
    const cleanup = getMount()({ container, path: "", navigate: vi.fn() });

    await vi.waitFor(() => {
      expect(container.textContent).toContain("not found");
    });

    cleanup();
    vi.restoreAllMocks();
  });

  it("allows saving and clearing GitHub username via settings form", async () => {
    const { host, getMount } = makeHost();
    activate(host);
    const container = document.createElement("div");
    const cleanup = getMount()({ container, path: "", navigate: vi.fn() });

    await vi.waitFor(() => {
      expect(container.textContent).toContain("GitHub Settings");
    });

    const input = container.querySelector(".pp-input");
    expect(input).toBeTruthy();
    expect(input.value).toBe("");

    input.value = "myuser";
    const form = container.querySelector(".pp-settings-form");
    form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));

    await vi.waitFor(() => {
      expect(localStorage.getItem("personal-profile:github-username")).toBe("myuser");
    });

    const clearButton = Array.from(container.querySelectorAll("button")).find(
      (b) => b.textContent === "Clear",
    );
    clearButton.click();

    await vi.waitFor(() => {
      expect(localStorage.getItem("personal-profile:github-username")).toBeNull();
    });

    cleanup();
  });

  it("renders error state when conversation fetch fails", async () => {
    const { host, getMount } = makeHost({
      agentServer: {
        request: vi.fn().mockRejectedValue(new Error("Network failure")),
      },
    });

    activate(host);
    const container = document.createElement("div");
    const cleanup = getMount()({ container, path: "", navigate: vi.fn() });

    await vi.waitFor(() => {
      expect(container.textContent).toContain("Network failure");
    });

    cleanup();
  });

  it("renders empty state when no conversations exist", async () => {
    const { host, getMount } = makeHost();
    activate(host);
    const container = document.createElement("div");
    const cleanup = getMount()({ container, path: "", navigate: vi.fn() });

    await vi.waitFor(() => {
      expect(container.textContent).toContain("0 contributions");
    });

    cleanup();
  });

  it("clears interval on unmount", async () => {
    const clearIntervalSpy = vi.spyOn(window, "clearInterval");
    const { host, getMount } = makeHost();
    activate(host);
    const container = document.createElement("div");
    const cleanup = getMount()({ container, path: "", navigate: vi.fn() });

    await vi.waitFor(() => {
      expect(container.textContent).toContain("OpenHands Conversations");
    });

    cleanup();
    expect(clearIntervalSpy).toHaveBeenCalled();
    clearIntervalSpy.mockRestore();
  });
});
