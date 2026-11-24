// Usage: node build.mjs /absolute/path/to/web/index (export basename)
import { readFile, writeFile } from 'node:fs/promises';
import { gzipSync } from 'node:zlib';
const base = process.argv[2];
if (!base) throw new Error('Pass the basename of a Godot 4.4.1 single-thread Web release export.');
const assets = {};
for (const ext of ['js', 'wasm', 'pck']) {
  assets[ext] = gzipSync(await readFile(`${base}.${ext}`), {level: 9}).toString('base64');
}
const source = await readFile(new URL('src/player.js', import.meta.url), 'utf8');
await writeFile(new URL('extension.js', import.meta.url), source.replace('= BUILD_ASSETS;', `= ${JSON.stringify(assets)};`));
