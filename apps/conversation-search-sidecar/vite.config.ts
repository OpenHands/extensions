import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  build: {
    assetsInlineLimit: Number.MAX_SAFE_INTEGER,
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: false,
    cssCodeSplit: false,
    lib: { entry: resolve(import.meta.dirname, "src/extension.tsx"), formats: ["es"], fileName: () => "extension.js" },
    rollupOptions: { output: { codeSplitting: false } },
  },
});
