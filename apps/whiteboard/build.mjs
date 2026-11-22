/* Build the Whiteboard App into one self-contained browser ESM file.

   Excalidraw plus React is a few megabytes of JavaScript. Canvas fetches and
   imports every enabled App's entrypoint when it starts, so shipping that as
   ordinary code would make every Canvas load pay for a whiteboard nobody has
   opened yet. The build therefore runs in two stages:

   1. src/board.jsx (React, Excalidraw, its stylesheet and fonts) is bundled
      into one ESM module, gzipped and base64-encoded.
   2. src/extension.js, the small shell that registers the page, is bundled
      with that payload as an inert string constant.

   Activation parses one string literal; nothing is decompressed or evaluated
   until the whiteboard page first mounts, and the evaluated module is then
   reused by later mounts. The output stays a single file: the payload is
   imported from a Blob URL, the same mechanism Canvas uses for the shell.

   Excalidraw's own lazy pieces are resolved at build time so nothing is
   fetched at runtime:
   - fonts referenced as "./fonts/..." become data: URLs, except the 12 MB
     Xiaolai CJK face, which is marked local-only so Excalidraw never falls
     back to its CDN for it;
   - only the English locale is bundled;
   - the Mermaid-to-Excalidraw converter is stubbed out (it would add several
     megabytes for one dialog);
   - font subsetting (1.7 MB of HarfBuzz/WOFF2 WebAssembly, used only when
     exporting SVG) is replaced by a module that embeds the whole font face,
     which is Excalidraw's own fallback when subsetting fails.
*/

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";
import esbuild from "esbuild";

const here = dirname(fileURLToPath(import.meta.url));
const MANIFEST = JSON.parse(readFileSync(join(here, "canvas-extension.json"), "utf8"));
const OUTFILE = join(here, MANIFEST.entrypoint);
const EXCALIDRAW_DIST = join(here, "node_modules/@excalidraw/excalidraw/dist/prod");
const STUBS = {
  locale: "export default {};",
  mermaid: `export async function parseMermaidToExcalidraw() {
    throw new Error("Mermaid import is not available in the Whiteboard App.");
  }`,
  // Mirrors subset-shared.chunk.js / subset-worker.chunk.js exports. With no
  // WorkerUrl Excalidraw stays on the main thread.
  subset: `export const Commands = { Subset: "SUBSET" };
  export const WorkerUrl = undefined;
  export async function toBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i += 0x8000) {
      binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    }
    return "data:font/woff2;base64," + btoa(binary);
  }
  export const subsetToBase64 = (buffer) => toBase64(buffer);
  export const subsetToBinary = async (buffer) => buffer;`,
};
const FONT_REF = /(["'])\.\/fonts\/([A-Za-z]+)\/([\w.-]+\.woff2)\1/g;

function inlineFont(quote, family, file) {
  // Excalidraw treats a "local:" URI as "no remote source" and skips it.
  if (family === "Xiaolai") return `${quote}local:${file}${quote}`;
  const data = readFileSync(join(EXCALIDRAW_DIST, "fonts", family, file)).toString("base64");
  return `${quote}data:font/woff2;base64,${data}${quote}`;
}

const excalidrawAssets = {
  name: "excalidraw-assets",
  setup(build) {
    build.onResolve({ filter: /^\.\/locales\/[\w-]+\.js$/ }, (args) => {
      if (!args.importer.startsWith(EXCALIDRAW_DIST)) return undefined;
      if (/^\.\/locales\/en-[A-Z0-9]+\.js$/.test(args.path)) return undefined;
      return { path: "locale", namespace: "whiteboard-stub" };
    });
    build.onResolve({ filter: /^@excalidraw\/mermaid-to-excalidraw$/ }, () => ({
      path: "mermaid",
      namespace: "whiteboard-stub",
    }));
    build.onResolve({ filter: /^\.\/subset-(shared|worker)\.chunk\.js$/ }, (args) => (
      args.importer.startsWith(EXCALIDRAW_DIST)
        ? { path: "subset", namespace: "whiteboard-stub" }
        : undefined
    ));
    build.onLoad({ filter: /.*/, namespace: "whiteboard-stub" }, (args) => ({
      contents: STUBS[args.path],
      loader: "js",
    }));
    build.onLoad({ filter: /\.(js|css)$/ }, (args) => {
      if (!args.path.startsWith(EXCALIDRAW_DIST)) return undefined;
      const source = readFileSync(args.path, "utf8");
      if (args.path.endsWith(".css")) {
        return {
          contents: source.replace(/url\((["'])\.\/fonts\/([A-Za-z]+)\/([\w.-]+\.woff2)\1\)/g,
            (_, quote, family, file) => `url(${inlineFont(quote, family, file)})`),
          loader: "text",
        };
      }
      return { contents: source.replace(FONT_REF, (_, ...parts) => inlineFont(...parts)), loader: "js" };
    });
  },
};

const shared = {
  bundle: true,
  format: "esm",
  platform: "browser",
  target: "es2022",
  minify: true,
  legalComments: "none",
  write: false,
  define: { "process.env.NODE_ENV": '"production"' },
  conditions: ["production"],
  logLevel: "warning",
};

const board = await esbuild.build({
  ...shared,
  entryPoints: [join(here, "src/board.jsx")],
  jsx: "automatic",
  loader: { ".css": "text" },
  plugins: [excalidrawAssets],
});
const boardSource = board.outputFiles[0].contents;
const payload = gzipSync(boardSource, { level: 9 }).toString("base64");

const shell = await esbuild.build({
  ...shared,
  entryPoints: [join(here, "src/extension.js")],
  plugins: [{
    name: "board-payload",
    setup(build) {
      build.onResolve({ filter: /^virtual:board-payload$/ }, () => ({
        path: "board-payload",
        namespace: "whiteboard-payload",
      }));
      build.onLoad({ filter: /.*/, namespace: "whiteboard-payload" }, () => ({
        contents: `export default ${JSON.stringify(payload)};`,
        loader: "js",
      }));
    },
  }],
});

writeFileSync(OUTFILE, shell.outputFiles[0].contents);
const kb = (bytes) => `${Math.round(bytes / 1024).toLocaleString()} KB`;
console.log(
  `Wrote ${MANIFEST.entrypoint}: ${kb(shell.outputFiles[0].contents.length)} ` +
    `(board ${kb(boardSource.length)} minified, ${kb(payload.length)} embedded)`,
);
