import type { AuditEntry, BackendMetadata } from "./types";

export function auditKey(backend: BackendMetadata): string {
  return `backend-sqlite-studio:audit:${backend.id ?? "unknown"}`;
}

export function loadAudit(backend: BackendMetadata): AuditEntry[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(auditKey(backend)) ?? "[]") as unknown;
    return Array.isArray(parsed) ? parsed.slice(0, 30) as AuditEntry[] : [];
  } catch { return []; }
}

export function addAudit(backend: BackendMetadata, entry: Omit<AuditEntry, "id" | "at">): AuditEntry[] {
  const next: AuditEntry[] = [{ ...entry, id: crypto.randomUUID(), at: new Date().toISOString() }, ...loadAudit(backend)].slice(0, 30);
  localStorage.setItem(auditKey(backend), JSON.stringify(next));
  return next;
}
