import { describe, expect, it } from "vitest";
import { makeDatabaseNamespace, openDatabaseStorage } from "./storage";

describe("browser-local database storage", () => {
  it("namespaces data by App name and encoded backend id", () => {
    expect(makeDatabaseNamespace("backend/a")).toBe("browser-sql-lab::backend%2Fa");
    expect(makeDatabaseNamespace(null)).toBe("browser-sql-lab::unavailable-backend");
  });

  it("persists bytes per backend without crossing namespaces", async () => {
    const backendA = await openDatabaseStorage(makeDatabaseNamespace("backend-a"));
    const backendB = await openDatabaseStorage(makeDatabaseNamespace("backend-b"));
    await backendA.save(new Uint8Array([1, 2, 3]));
    await backendB.save(new Uint8Array([9, 8]));
    await expect(backendA.load()).resolves.toEqual(new Uint8Array([1, 2, 3]));
    await expect(backendB.load()).resolves.toEqual(new Uint8Array([9, 8]));
    await backendA.clear();
    await expect(backendA.load()).resolves.toBeNull();
    await expect(backendB.load()).resolves.toEqual(new Uint8Array([9, 8]));
    backendA.close();
    backendB.close();
  });
});
