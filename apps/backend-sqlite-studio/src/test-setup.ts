import { vi } from "vitest";

Object.defineProperty(globalThis, "IS_REACT_ACT_ENVIRONMENT", { configurable: true, value: true });
Object.defineProperty(navigator, "clipboard", {
  configurable: true,
  value: { writeText: vi.fn().mockResolvedValue(undefined) },
});
Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:export") });
Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
