import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  build: {
    assetsInlineLimit: Number.MAX_SAFE_INTEGER,
    cssCodeSplit: false,
    emptyOutDir: true,
    lib: {
      entry: resolve(import.meta.dirname, "src/extension.tsx"),
      formats: ["es"],
      fileName: () => "extension.js",
    },
    outDir: "dist",
    rollupOptions: {
      output: {
        codeSplitting: false,
      },
    },
    sourcemap: false,
  },
});
