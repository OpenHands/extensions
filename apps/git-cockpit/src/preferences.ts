import type { BackendMetadata } from "./types";

export type CockpitTab = "changes" | "history" | "branches";

export interface CockpitPreferences {
  workspaceToken: string | null;
  tab: CockpitTab;
}

const DEFAULTS: CockpitPreferences = { workspaceToken: null, tab: "changes" };

export function preferenceKey(backend: BackendMetadata): string {
  const scope = [backend.kind ?? "unknown", backend.orgId ?? "none", backend.id ?? "anonymous"].join(":");
  return `git-cockpit:preferences:v1:${encodeURIComponent(scope)}`;
}

export function loadPreferences(backend: BackendMetadata): CockpitPreferences {
  try {
    const raw = localStorage.getItem(preferenceKey(backend));
    if (!raw) return { ...DEFAULTS };
    const parsed = JSON.parse(raw) as Partial<CockpitPreferences>;
    return {
      workspaceToken: typeof parsed.workspaceToken === "string" && /^[A-Za-z0-9_-]+$/.test(parsed.workspaceToken)
        ? parsed.workspaceToken
        : null,
      tab: parsed.tab === "history" || parsed.tab === "branches" ? parsed.tab : "changes",
    };
  } catch {
    return { ...DEFAULTS };
  }
}

export function savePreferences(backend: BackendMetadata, preferences: CockpitPreferences): void {
  try {
    localStorage.setItem(preferenceKey(backend), JSON.stringify(preferences));
  } catch {
    // The App remains usable when browser storage is unavailable.
  }
}
