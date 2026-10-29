import { beforeEach, describe, expect, it } from "vitest";
import { loadPreferences, preferenceKey, savePreferences } from "./preferences";

beforeEach(() => localStorage.clear());

describe("backend-scoped harmless preferences", () => {
  it("isolates workspace and view state by backend identity", () => {
    const local = { kind: "local", id: "alpha", orgId: null };
    const remote = { kind: "remote", id: "alpha", orgId: "org" };
    expect(preferenceKey(local)).not.toBe(preferenceKey(remote));
    savePreferences(local, { workspaceToken: "L3dvcmtzcGFjZS9kZW1v", tab: "history" });
    expect(loadPreferences(local)).toEqual({ workspaceToken: "L3dvcmtzcGFjZS9kZW1v", tab: "history" });
    expect(loadPreferences(remote)).toEqual({ workspaceToken: null, tab: "changes" });
  });

  it("discards malformed or unsafe persisted values", () => {
    const backend = { kind: "local", id: "alpha" };
    localStorage.setItem(preferenceKey(backend), JSON.stringify({ workspaceToken: "bad/token", tab: "writes" }));
    expect(loadPreferences(backend)).toEqual({ workspaceToken: null, tab: "changes" });
  });
});
