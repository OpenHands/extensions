import { createHash } from "node:crypto";
import { readdir, readFile, mkdir, rm, writeFile, chmod, stat } from "node:fs/promises";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";

const exec = promisify(execFile);
const appRoot = path.resolve(new URL("..", import.meta.url).pathname);
const root = path.resolve(appRoot, "../..");
if (process.platform !== "linux") throw new Error("VS Code App packaging currently supports Linux build runners only");

/**
 * Force a umask-independent mode set on the staged tree.
 *
 * `cp -a` preserves whatever modes tar materialized, and the build host's umask
 * narrows them (0664/0775 under umask 0002, 0644/0755 under umask 022). Those
 * bits end up in the final archive's tar headers, so the digest — and with it
 * the `sha256` declared in canvas-extension.json — used to vary per build host.
 */
async function normalizeModes(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const target = path.join(dir, entry.name);
    if (entry.isSymbolicLink()) continue;
    if (entry.isDirectory()) {
      await chmod(target, 0o755);
      await normalizeModes(target);
    } else if (entry.isFile()) {
      const { mode } = await stat(target);
      await chmod(target, mode & 0o111 ? 0o755 : 0o644);
    }
  }
}
const output = path.resolve(process.env.OUTPUT_DIR ?? path.join(root, "dist"));
const version = "1.109.5";
const releases = {
  "linux-amd64": ["x64", "b433bf4f0227321a7014d8460d10a8f958adc0f45aa79bd889e84e65e8f88363"],
  "linux-arm64": ["arm64", "36d9c14036489b63de84ebace837fcacf7e60e669a0dc715802c5443684ea4dc"],
};
const work = path.join(output, ".download");
const packageRoot = path.join(output, "apps", "vscode");
const manifest = JSON.parse(await readFile(path.join(appRoot, "canvas-extension.json"), "utf8"));
await rm(work, { recursive: true, force: true });
await rm(packageRoot, { recursive: true, force: true });
await mkdir(work, { recursive: true });
await mkdir(path.join(packageRoot, "backend"), { recursive: true });
for (const [platform, [upstreamArch, expected]] of Object.entries(releases)) {
  const source = path.join(work, `${platform}.tar.gz`);
  const archive = `openvscode-server-v${version}-linux-${upstreamArch}.tar.gz`;
  const url = `https://github.com/gitpod-io/openvscode-server/releases/download/openvscode-server-v${version}/${archive}`;
  await exec("curl", ["--fail", "--location", "--retry", "3", "--output", source, url]);
  const actual = createHash("sha256").update(await readFile(source)).digest("hex");
  if (actual !== expected) throw new Error(`${platform}: upstream checksum mismatch (${actual})`);
  const unpacked = path.join(work, `${platform}-unpacked`);
  const normalized = path.join(work, `${platform}-normalized`);
  await mkdir(unpacked, { recursive: true });
  await exec("tar", ["-xzf", source, "-C", unpacked]);
  await mkdir(normalized, { recursive: true });
  const [top] = await readdir(unpacked);
  await exec("cp", ["-a", `${path.join(unpacked, top)}/.`, normalized]);
  await writeFile(path.join(normalized, "bin", "openvscode-bootstrap"), "#!/bin/sh\nset -eu\ndata_dir=\"\"\nfor candidate do data_dir=\"$candidate\"; done\nmkdir -p \"$data_dir\" \"$data_dir/home\" \"$data_dir/workspace\"\nexport HOME=\"$data_dir/home\"\nexec \"$(dirname \"$0\")/openvscode-server\" \"$@\"\n");
  await exec("chmod", ["0755", path.join(normalized, "bin", "openvscode-bootstrap")]);
  await normalizeModes(normalized);
  const destination = path.join(packageRoot, "backend", `openvscode-${platform}.tar.gz`);
  await exec("tar", ["--sort=name", "--mtime=UTC 1970-01-01", "--owner=0", "--group=0", "--numeric-owner", "-czf", destination, "-C", normalized, "."]);
  const produced = createHash("sha256").update(await readFile(destination)).digest("hex");
  const artifact = manifest?.backend?.artifacts?.[platform];
  if (!artifact?.sha256) {
    throw new Error(`canvas-extension.json declares no backend.artifacts.${platform}.sha256`);
  }
  if (path.basename(destination) !== path.basename(artifact.path)) {
    throw new Error(`${platform}: built ${path.basename(destination)} but canvas-extension.json declares ${artifact.path}`);
  }
  if (produced !== artifact.sha256) {
    throw new Error(
      `${platform}: built archive digest ${produced} does not match the sha256 declared for backend.artifacts.${platform} in canvas-extension.json (${artifact.sha256}); update the manifest with the reproducible digest`
    );
  }
  console.log(`${platform}: ${produced}`);
}
await exec("cp", [path.join(appRoot, "canvas-extension.json"), path.join(packageRoot, "canvas-extension.json")]);
await exec("cp", [path.join(appRoot, "extension.js"), path.join(packageRoot, "extension.js")]);
await exec("cp", [path.join(appRoot, "README.md"), path.join(packageRoot, "README.md")]);
await rm(work, { recursive: true, force: true });
console.log(`Wrote ${packageRoot}`);
