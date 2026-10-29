// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { __testing, activate } from "./extension.js";

function canvasContext() {
  return {
    beginPath: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
    fillRect: vi.fn(),
    rect: vi.fn(),
    roundRect: vi.fn(),
    setTransform: vi.fn(),
    fillStyle: "",
    shadowBlur: 0,
    shadowColor: "",
  };
}

function createHost(overrides = {}) {
  let mount;
  const unregister = vi.fn();
  const request = vi.fn();
  const host = {
    apiVersion: "1",
    extension: { name: "snake-arcade", version: "0.1.0", resolvedRef: "test-ref" },
    backend: { id: "local-test", kind: "local", orgId: null },
    registerPage: vi.fn((id, pageMount) => {
      mount = pageMount;
      return unregister;
    }),
    navigate: vi.fn(),
    agentServer: { request },
    ...overrides,
  };
  return { host, getMount: () => mount, unregister, request };
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  localStorage.clear();
  document.body.replaceChildren();
});

describe("Snake Arcade game engine", () => {
  it("moves, eats, grows, and scores deterministically", () => {
    const game = {
      snake: [{ x: 5, y: 5 }, { x: 4, y: 5 }],
      snack: { x: 6, y: 5 },
      direction: "right",
      queuedDirection: "right",
      score: 0,
      status: "playing",
    };
    const next = __testing.advanceGame(game, () => 0);
    expect(next.snake).toHaveLength(3);
    expect(next.snake[0]).toEqual({ x: 6, y: 5 });
    expect(next.score).toBe(10);
    expect(next.snack).not.toEqual(next.snake[0]);
  });

  it("rejects a reverse turn and detects wall collisions", () => {
    const initial = __testing.createInitialGame(() => 0);
    expect(__testing.queueDirection(initial, "left")).toBe(initial);
    const doomed = {
      ...initial,
      snake: [{ x: 21, y: 3 }, { x: 20, y: 3 }],
      status: "playing",
    };
    expect(__testing.advanceGame(doomed).status).toBe("over");
  });

  it("never places a snack on the snake", () => {
    const snake = [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 2, y: 0 }];
    expect(snake).not.toContainEqual(__testing.placeSnack(snake, () => 0));
  });
});

describe("Snake Arcade Canvas lifecycle", () => {
  it("registers exactly one declared page and activation cleanup unregisters it", () => {
    const { host, unregister } = createHost();
    expect(activate(host)).toBe(unregister);
    expect(host.registerPage).toHaveBeenCalledTimes(1);
    expect(host.registerPage).toHaveBeenCalledWith("arcade", expect.any(Function));
  });

  it("mounts the game, persists a backend-scoped high score, and cleans up", () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(canvasContext());
    const { host, getMount, request } = createHost();
    activate(host);
    localStorage.setItem(__testing.storageKey(host), "70");
    const container = document.createElement("div");
    const navigate = vi.fn();
    const cleanup = getMount()({ container, path: "", navigate });

    expect(container.textContent).toContain("Snake Arcade");
    expect(container.textContent).toContain("Feed the neon noodle");
    const stats = container.querySelectorAll(".snake-arcade__stat-value");
    expect(stats[1].textContent).toBe("70");
    expect(request).not.toHaveBeenCalled();

    container.querySelector(".snake-arcade__header-action").click();
    expect(navigate).toHaveBeenCalledWith("/extensions/snake-arcade/snake/how-to-play");
    cleanup();
    expect(container.childElementCount).toBe(0);
  });

  it("stops the game timer when an active page unmounts", () => {
    vi.useFakeTimers();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(canvasContext());
    const { host, getMount } = createHost();
    activate(host);
    const container = document.createElement("div");
    const cleanup = getMount()({ container, path: "", navigate: vi.fn() });
    container.querySelector(".snake-arcade__button--primary").click();
    expect(vi.getTimerCount()).toBe(1);
    cleanup();
    expect(vi.getTimerCount()).toBe(0);
    expect(container.childElementCount).toBe(0);
  });

  it("renders the nested rules route and navigates back", () => {
    const { host, getMount } = createHost();
    activate(host);
    const container = document.createElement("div");
    const navigate = vi.fn();
    const cleanup = getMount()({ container, path: "how-to-play", navigate });
    expect(container.textContent).toContain("How to be a tiny legend");
    const back = Array.from(container.querySelectorAll("button")).find((button) => button.textContent.includes("Back to the game"));
    back.click();
    expect(navigate).toHaveBeenCalledWith("/extensions/snake-arcade/snake");
    cleanup();
    expect(container.childElementCount).toBe(0);
  });

  it("fails clearly on an unsupported host API", () => {
    const { host } = createHost({ apiVersion: "2" });
    expect(() => activate(host)).toThrow("requires Canvas host API 1");
  });

  it("survives unavailable local storage", () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(canvasContext());
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
    const { host, getMount } = createHost();
    activate(host);
    const container = document.createElement("div");
    const cleanup = getMount()({ container, path: "", navigate: vi.fn() });
    const stats = container.querySelectorAll(".snake-arcade__stat-value");
    expect(stats[1].textContent).toBe("0");
    cleanup();
  });
});
