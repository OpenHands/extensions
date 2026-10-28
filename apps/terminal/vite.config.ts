import { resolve } from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  build: {
    assetsInlineLimit: Number.MAX_SAFE_INTEGER,
    cssCodeSplit: false,
    emptyOutDir: true,
    lib: {
      entry: resolve(import.meta.dirname, "src/extension.ts"),
      formats: ["es"],
      fileName: () => "extension.js",
    },
    outDir: "dist",
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
    sourcemap: false,
  },
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.ts"],
  },
});
