import { cp, mkdir, readFile, rm } from "node:fs/promises";
import path from "node:path";

const appRoot = path.resolve(new URL("..", import.meta.url).pathname);
const root = path.resolve(appRoot, "../..");
const output = path.resolve(process.env.OUTPUT_DIR ?? path.join(root, "dist"));
const packageRoot = path.join(output, "apps", "vscode");
const manifest = JSON.parse(
  await readFile(path.join(appRoot, "canvas-extension.json"), "utf8"),
);

for (const [platform, artifact] of Object.entries(manifest.backend.artifacts)) {
  const url = new URL(artifact.url);
  if (url.protocol !== "https:" || !url.pathname.endsWith(".tar.gz")) {
    throw new Error(`${platform}: invalid HTTPS artifact URL`);
  }
  if (!/^[0-9a-f]{64}$/.test(artifact.sha256)) {
    throw new Error(`${platform}: invalid SHA-256`);
  }
  if (!Number.isInteger(artifact.strip_components) || artifact.strip_components < 0) {
    throw new Error(`${platform}: invalid strip_components`);
  }
}

await rm(packageRoot, { recursive: true, force: true });
await mkdir(packageRoot, { recursive: true });
for (const filename of ["canvas-extension.json", "extension.js", "README.md"]) {
  await cp(path.join(appRoot, filename), path.join(packageRoot, filename));
}
console.log(`Wrote source-installable App package to ${packageRoot}`);
