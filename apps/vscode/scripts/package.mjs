import { createHash } from "node:crypto";
import { readdir, readFile, mkdir, rm, writeFile } from "node:fs/promises";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";

const exec = promisify(execFile);
const appRoot = path.resolve(new URL("..", import.meta.url).pathname);
const root = path.resolve(appRoot, "../..");
if (process.platform !== "linux") throw new Error("VS Code App packaging currently supports Linux build runners only");
const output = path.resolve(process.env.OUTPUT_DIR ?? path.join(root, "dist"));
const version = "1.109.5";
const releases = {
  "linux-amd64": ["x64", "b433bf4f0227321a7014d8460d10a8f958adc0f45aa79bd889e84e65e8f88363"],
  "linux-arm64": ["arm64", "36d9c14036489b63de84ebace837fcacf7e60e669a0dc715802c5443684ea4dc"],
};
const work = path.join(output, ".download");
const packageRoot = path.join(output, "apps", "vscode");
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
  const destination = path.join(packageRoot, "backend", `openvscode-${platform}.tar.gz`);
  await exec("tar", ["--sort=name", "--mtime=UTC 1970-01-01", "--owner=0", "--group=0", "--numeric-owner", "-czf", destination, "-C", normalized, "."]);
  console.log(`${platform}: ${createHash("sha256").update(await readFile(destination)).digest("hex")}`);
}
await exec("cp", [path.join(appRoot, "canvas-extension.json"), path.join(packageRoot, "canvas-extension.json")]);
await exec("cp", [path.join(appRoot, "extension.js"), path.join(packageRoot, "extension.js")]);
await exec("cp", [path.join(appRoot, "README.md"), path.join(packageRoot, "README.md")]);
await rm(work, { recursive: true, force: true });
console.log(`Wrote ${packageRoot}`);
