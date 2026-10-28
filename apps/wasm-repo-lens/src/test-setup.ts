import { vi } from "vitest";

Object.defineProperty(navigator, "clipboard", {
  configurable: true,
  value: { writeText: vi.fn().mockResolvedValue(undefined) },
});

if (!URL.createObjectURL) URL.createObjectURL = vi.fn(() => "blob:test");
if (!URL.revokeObjectURL) URL.revokeObjectURL = vi.fn();
