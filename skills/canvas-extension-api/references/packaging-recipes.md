# Packaging recipes

The observable requirement is exactly one Blob-importable `extension.js`, not a particular framework or starter. When using Vite, configure library mode with one ES input, `assetsInlineLimit: Number.MAX_SAFE_INTEGER`, `cssCodeSplit: false`, code splitting disabled, and source maps disabled.

For Vite versions that use Rollup, set `output.inlineDynamicImports: true`. Do not pass `codeSplitting` to Rollup; it is not a Rollup output option. Vite 8 uses Rolldown instead: use `build.rolldownOptions.output.codeSplitting: false` there. Both forms require exactly one input and inline dynamic imports, which can change a dynamically imported module's execution timing.

```ts
import { resolve } from "node:path";
import { defineConfig } from "vite";

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
    rollupOptions: { output: { inlineDynamicImports: true } },
    sourcemap: false,
  },
});
```

Add the framework's Vite plugin when applicable. For Vite 8, replace the `rollupOptions` block above with:

```ts
rolldownOptions: { output: { codeSplitting: false } },
```

The required outcome remains one output file.

- CSS: import `./styles.css?inline`, inject one App-marked `<style>` node per mount, and remove it during cleanup. `cssCodeSplit: false` alone can emit a sibling stylesheet.
- Text fixtures, SQL, templates, helper source: import with `?raw`.
- JSON, SVG, small assets: use ordinary imports and audit the output.
- Dynamic source modules: allow `import()` only when output remains one file; validator and Blob smoke must prove it.
- Workers: import with `?worker&inline`; terminate, remove listeners, and reject pending RPC calls in cleanup.
- WASM: import inside an inline Worker and confirm the built file has no unresolved `.wasm` URL. Build tools are contributor prerequisites; checked-in bundled artifacts are runtime requirements.

Never use `public/` for required runtime files, externalize React, use CDNs, leave a sibling CSS/Worker/WASM asset, use CommonJS, or rely on normal `import.meta.url` deployment semantics.
