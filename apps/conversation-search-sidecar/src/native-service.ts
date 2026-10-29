import mainSource from "../native/main.go?raw";
import goModSource from "../native/go.mod?raw";
import goSumSource from "../native/go.sum?raw";
import artifactMetadata from "../native/artifact-metadata.json";
import type { CanvasHost, IndexStatus, NativeResponse, ProbeStatus, SearchFilters, SearchResponse, SearchHit } from "./types";

export const APP_SUBPATH = ".openhands/apps/conversation-search-sidecar";
export const RUNTIME_VERSION = "1";
export const SIDECAR_VERSION = artifactMetadata.version;
export const SOURCE_SHA256 = artifactMetadata.source_sha256;
export const IDLE_SHUTDOWN_SECONDS = 600;

interface CommandResponse { exit_code?: unknown; stdout?: unknown; stderr?: unknown }
interface HomeResponse { home?: unknown }
interface NativeEnvelope { ok?: unknown; data?: unknown; error?: unknown }

function utf8Base64(value: string): string {
  const bytes = new TextEncoder().encode(value);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function decodeUtf8Base64(value: string): string {
  const bytes = Uint8Array.from(atob(value), (character) => character.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

const MAIN_BASE64 = utf8Base64(mainSource);
const GO_MOD_BASE64 = utf8Base64(goModSource);
const GO_SUM_BASE64 = utf8Base64(goSumSource);
const STOP_PAYLOAD = utf8Base64(JSON.stringify({ action: "stop" }));
const STATUS_PAYLOAD = utf8Base64(JSON.stringify({ action: "status" }));

export const PROBE_COMMAND = String.raw`python3 - <<'PY'
import base64, hashlib, json, os, platform, re, shutil, subprocess
from pathlib import Path
home = Path.cwd().resolve()
base = home / ".openhands"
candidates = [(base / "dev_conversations", "sdk-dev"), (base / "conversations", "sdk-standard")]
candidates += [(item, "sdk-discovered") for item in base.glob("*/dev_conversations")]
candidates += [(home / "dev_conversations", "sdk-home-root")]
locations, seen = [], set()
def contains_symlink(candidate):
    try: parts = candidate.absolute().relative_to(home).parts
    except ValueError: return True
    current = home
    for part in parts:
        current = current / part
        if current.is_symlink(): return True
    return False
for candidate, layout in candidates:
    raw_candidate = candidate
    candidate = candidate.absolute()
    if str(candidate) in seen:
        continue
    seen.add(str(candidate))
    item = {"path": str(candidate), "layout": layout, "state": "missing", "conversations": 0, "files": 0, "malformed": 0}
    try:
        if not raw_candidate.exists():
            locations.append(item); continue
        if contains_symlink(raw_candidate) or not candidate.is_dir():
            item.update(state="unsupported", message="candidate is not a real directory")
            locations.append(item); continue
        for conversation in candidate.iterdir():
            if conversation.is_symlink() or not conversation.is_dir():
                continue
            item["conversations"] += 1
            meta = conversation / "meta.json"
            if not meta.is_symlink() and meta.is_file(): item["files"] += 1
            events = conversation / "events"
            if not events.is_symlink() and events.is_dir(): item["files"] += sum(1 for event in events.iterdir() if not event.is_symlink() and event.is_file() and event.name.startswith("event-") and event.suffix == ".json")
        item["state"] = "ready" if item["conversations"] else "empty"
    except OSError as exc:
        item.update(state="unreadable", message=str(exc))
    locations.append(item)
os_name, arch_name = platform.system() or "unknown", platform.machine() or "unknown"
targets = {("Darwin", "arm64"): "darwin-arm64", ("Darwin", "x86_64"): "darwin-amd64", ("Linux", "x86_64"): "linux-amd64", ("Linux", "aarch64"): "linux-arm64", ("Linux", "arm64"): "linux-arm64"}
target = targets.get((os_name, arch_name), f"{os_name}-{arch_name}")
go = shutil.which("go")
go_version = subprocess.run([go, "version"], capture_output=True, text=True).stdout.strip() if go else None
go_match = re.search(r"go(\d+)\.(\d+)", go_version or "")
go_ready = bool(go_match and (int(go_match.group(1)), int(go_match.group(2))) >= (1, 23))
app = base / "apps" / "conversation-search-sidecar"
binary, artifact, marker = app / "bin" / "conversation-search", app / "artifact.json", app / ".runtime-version"
runtime_version = marker.read_text(errors="replace")[:40] if marker.is_file() else None
installed = artifact_verified = False
paths_safe = not any(item.is_symlink() for item in (base, base / "apps", app, binary, artifact, marker))
if paths_safe and binary.is_file() and os.access(binary, os.X_OK) and artifact.is_file() and runtime_version == "${RUNTIME_VERSION}":
    try:
        metadata = json.loads(artifact.read_text())
        digest = hashlib.sha256()
        with binary.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""): digest.update(chunk)
        artifact_verified = metadata.get("version") == "${SIDECAR_VERSION}" and metadata.get("sourceSha256") == "${SOURCE_SHA256}" and metadata.get("binarySha256") == digest.hexdigest()
        if artifact_verified:
            result = subprocess.run([str(binary), "version"], capture_output=True, text=True, timeout=10)
            line = next((line for line in result.stdout.splitlines() if line.startswith("CONVERSATION_SEARCH\t")), "")
            envelope = json.loads(base64.b64decode(line.split("\t", 1)[1])) if line else {}
            installed = result.returncode == 0 and envelope.get("ok") is True and envelope.get("data", {}).get("message", "").startswith("conversation-search ${SIDECAR_VERSION} ")
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        pass
value = {"os": os_name, "arch": arch_name, "target": target, "supported": (os_name, arch_name) in targets, "goVersion": go_version, "goReady": go_ready, "installed": installed, "runtimeVersion": runtime_version, "binaryPresent": binary.is_file(), "artifactPresent": artifact.is_file(), "artifactVerified": artifact_verified, "locations": locations}
print("CONVERSATION_SEARCH_PROBE\t" + base64.b64encode(json.dumps(value, separators=(",", ":")).encode()).decode())
PY`;

export const INSTALL_COMMAND = String.raw`set -eu
app_dir='.openhands/apps/conversation-search-sidecar'
build_dir="$app_dir/build/src"
for checked in '.openhands' '.openhands/apps' "$app_dir" "$app_dir/build" "$build_dir" "$app_dir/bin" "$app_dir/index" "$app_dir/logs" "$app_dir/run" "$app_dir/artifact.json" "$app_dir/.runtime-version"; do [ ! -L "$checked" ] || { printf 'App data path contains a symbolic link\n' >&2; exit 1; }; done
case "$(uname -s)-$(uname -m)" in Darwin-arm64) target='darwin-arm64';; Darwin-x86_64) target='darwin-amd64';; Linux-aarch64|Linux-arm64) target='linux-arm64';; Linux-x86_64) target='linux-amd64';; *) printf 'unsupported native target\n' >&2; exit 1;; esac
command -v go >/dev/null 2>&1 || { printf 'Go 1.23+ is required for the local build\n' >&2; exit 1; }
go version | python3 -c 'import re,sys; value=sys.stdin.read(); match=re.search(r"go(\d+)\.(\d+)",value); sys.exit(0 if match and (int(match.group(1)),int(match.group(2))) >= (1,23) else 1)' || { printf 'Go 1.23+ is required for the local build\n' >&2; exit 1; }
mkdir -p "$build_dir" "$app_dir/bin" "$app_dir/index" "$app_dir/logs" "$app_dir/run"
decode_file() {
  encoded="$1"; destination="$2"
  if printf '%s' "$encoded" | base64 --decode > "$destination.tmp" 2>/dev/null; then :
  else printf '%s' "$encoded" | base64 -D > "$destination.tmp"; fi
  chmod 600 "$destination.tmp"
  mv "$destination.tmp" "$destination"
}
sha_file() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}
decode_file '${MAIN_BASE64}' "$build_dir/main.go"
decode_file '${GO_MOD_BASE64}' "$build_dir/go.mod"
decode_file '${GO_SUM_BASE64}' "$build_dir/go.sum"
[ "$(sha_file "$build_dir/main.go")" = '${artifactMetadata.main_go_sha256}' ] || { printf 'bundled main.go checksum mismatch\n' >&2; exit 1; }
[ "$(sha_file "$build_dir/go.mod")" = '${artifactMetadata.go_mod_sha256}' ] || { printf 'bundled go.mod checksum mismatch\n' >&2; exit 1; }
[ "$(sha_file "$build_dir/go.sum")" = '${artifactMetadata.go_sum_sha256}' ] || { printf 'bundled go.sum checksum mismatch\n' >&2; exit 1; }
export GOMODCACHE="$PWD/$app_dir/build/modcache"
export GOCACHE="$PWD/$app_dir/build/gocache"
export GOPATH="$PWD/$app_dir/build/gopath"
cd "$build_dir"
go mod download
go build -trimpath -ldflags='-s -w' -o '../../bin/conversation-search.tmp' .
cd "$OLDPWD"
chmod 700 "$app_dir/bin/conversation-search.tmp"
mv "$app_dir/bin/conversation-search.tmp" "$app_dir/bin/conversation-search"
binary_sha=$(sha_file "$app_dir/bin/conversation-search")
python3 -c 'import json,sys; json.dump({"version":sys.argv[1],"target":sys.argv[2],"binarySha256":sys.argv[3],"sourceSha256":sys.argv[4],"origin":"bundled, reviewed Go source built locally","builtAt":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()},open(sys.argv[5],"w"),indent=2)' '${SIDECAR_VERSION}' "$target" "$binary_sha" '${SOURCE_SHA256}' "$app_dir/artifact.json"
chmod 600 "$app_dir/artifact.json"
printf '%s' '${RUNTIME_VERSION}' > "$app_dir/.runtime-version"
"$app_dir/bin/conversation-search" version`;

export const START_COMMAND = String.raw`set -eu
app_dir='.openhands/apps/conversation-search-sidecar'
binary="$app_dir/bin/conversation-search"
sha_file() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'; else shasum -a 256 "$1" | awk '{print $1}'; fi; }
[ -x "$binary" ] || { printf 'native runtime is not installed\n' >&2; exit 1; }
[ -f "$app_dir/artifact.json" ] || { printf 'native artifact metadata is missing\n' >&2; exit 1; }
for checked in '.openhands' '.openhands/apps' "$app_dir" "$app_dir/bin" "$app_dir/index" "$app_dir/logs" "$app_dir/logs/service.log" "$app_dir/run" "$binary" "$app_dir/artifact.json" "$app_dir/.runtime-version"; do [ ! -L "$checked" ] || { printf 'native artifact path contains a symbolic link\n' >&2; exit 1; }; done
artifact_version=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$app_dir/artifact.json")
artifact_source=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sourceSha256"])' "$app_dir/artifact.json")
[ "$artifact_version" = '${SIDECAR_VERSION}' ] && [ "$artifact_source" = '${SOURCE_SHA256}' ] && [ "$(cat "$app_dir/.runtime-version" 2>/dev/null)" = '${RUNTIME_VERSION}' ] || { printf 'native artifact version/source mismatch; use Repair runtime\n' >&2; exit 1; }
expected=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["binarySha256"])' "$app_dir/artifact.json")
actual=$(sha_file "$binary")
[ "$actual" = "$expected" ] || { printf 'native binary checksum mismatch; use Repair runtime\n' >&2; exit 1; }
"$binary" version >/dev/null
if "$binary" rpc '${STATUS_PAYLOAD}' >/dev/null 2>&1; then
  printf 'CONVERSATION_SEARCH_STARTED\talready-running\n'
  exit 0
fi
nohup "$binary" serve >> "$app_dir/logs/service.log" 2>&1 &
attempt=0
while [ "$attempt" -lt 50 ]; do
  if "$binary" rpc '${STATUS_PAYLOAD}' >/dev/null 2>&1; then printf 'CONVERSATION_SEARCH_STARTED\tready\n'; exit 0; fi
  attempt=$((attempt + 1))
  sleep 0.1
done
printf 'native service did not become healthy; inspect the App log\n' >&2
exit 1`;

export const STOP_COMMAND = String.raw`set -eu
app_dir='.openhands/apps/conversation-search-sidecar'
binary="$app_dir/bin/conversation-search"
artifact="$app_dir/artifact.json"
if [ ! -x "$binary" ]; then [ ! -e "$app_dir/run/daemon.json" ] || { printf 'service state exists but the native runtime is missing; use Repair runtime\n' >&2; exit 1; }; printf 'CONVERSATION_SEARCH_STOPPED\tnot-installed\n'; exit 0; fi
[ -f "$artifact" ] || { printf 'native artifact metadata is missing; use Repair runtime\n' >&2; exit 1; }
for checked in '.openhands' '.openhands/apps' "$app_dir" "$binary" "$artifact"; do [ ! -L "$checked" ] || { printf 'native artifact path contains a symbolic link\n' >&2; exit 1; }; done
sha_file() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'; else shasum -a 256 "$1" | awk '{print $1}'; fi; }
artifact_version=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$artifact")
artifact_source=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sourceSha256"])' "$artifact")
expected=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["binarySha256"])' "$artifact")
[ "$artifact_version" = '${SIDECAR_VERSION}' ] && [ "$artifact_source" = '${SOURCE_SHA256}' ] && [ "$(cat "$app_dir/.runtime-version" 2>/dev/null)" = '${RUNTIME_VERSION}' ] && [ "$(sha_file "$binary")" = "$expected" ] || { printf 'native artifact verification failed; use Repair runtime\n' >&2; exit 1; }
if "$binary" rpc '${STOP_PAYLOAD}' >/dev/null 2>&1; then printf 'CONVERSATION_SEARCH_STOPPED\tstopped\n'
else printf 'CONVERSATION_SEARCH_STOPPED\talready-stopped\n'; fi`;

export const DELETE_COMMAND = String.raw`set -eu
app_dir='.openhands/apps/conversation-search-sidecar'
binary="$app_dir/bin/conversation-search"
artifact="$app_dir/artifact.json"
if [ -e "$app_dir/run/daemon.json" ] && [ ! -x "$binary" ]; then printf 'service state exists but the native runtime is missing; repair and stop before deletion\n' >&2; exit 1; fi
if [ -x "$binary" ]; then
  [ -f "$artifact" ] || { printf 'native artifact metadata is missing; repair and stop before deletion\n' >&2; exit 1; }
  for checked in '.openhands' '.openhands/apps' "$app_dir" "$binary" "$artifact"; do [ ! -L "$checked" ] || { printf 'native artifact path contains a symbolic link\n' >&2; exit 1; }; done
  sha_file() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'; else shasum -a 256 "$1" | awk '{print $1}'; fi; }
  artifact_version=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$artifact")
  artifact_source=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sourceSha256"])' "$artifact")
  expected=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["binarySha256"])' "$artifact")
  [ "$artifact_version" = '${SIDECAR_VERSION}' ] && [ "$artifact_source" = '${SOURCE_SHA256}' ] && [ "$(cat "$app_dir/.runtime-version" 2>/dev/null)" = '${RUNTIME_VERSION}' ] && [ "$(sha_file "$binary")" = "$expected" ] || { printf 'native artifact verification failed; repair and stop before deletion\n' >&2; exit 1; }
  "$binary" rpc '${STOP_PAYLOAD}' >/dev/null 2>&1 || true
fi
python3 -c 'import pathlib,shutil; base=pathlib.Path.cwd().resolve(); oh=base/".openhands"; apps=oh/"apps"; target=apps/"conversation-search-sidecar"; any(item.is_symlink() for item in (oh,apps,target)) and (_ for _ in ()).throw(RuntimeError("unsafe symbolic-link deletion target")); target.resolve().is_relative_to(base) or (_ for _ in ()).throw(RuntimeError("unsafe deletion target")); shutil.rmtree(target) if target.exists() else None; print("CONVERSATION_SEARCH_DELETED")'`;

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) throw new DOMException("The Agent Server request was cancelled.", "AbortError");
}

export function isValidHomePath(value: unknown): value is string {
  if (typeof value !== "string" || value.length < 2 || value.length > 4096 || !value.startsWith("/")) return false;
  if (/[\0-\x1f\x7f]/.test(value) || value.includes("//")) return false;
  return value.split("/").filter(Boolean).every((segment) => segment !== "." && segment !== "..");
}

export function dataDirectory(home: string): string {
  if (!isValidHomePath(home)) throw new Error("The Agent Server returned an unsafe home path.");
  return `${home.replace(/\/+$/, "")}/${APP_SUBPATH}`;
}

export async function discoverHome(host: CanvasHost, signal?: AbortSignal): Promise<string> {
  throwIfAborted(signal);
  const raw = await host.agentServer.request<HomeResponse | string>({ path: "/api/file/home" });
  throwIfAborted(signal);
  let response: HomeResponse;
  try { response = typeof raw === "string" ? JSON.parse(raw) as HomeResponse : raw; }
  catch { throw new Error("The Agent Server home response was not valid JSON."); }
  if (!isValidHomePath(response?.home)) throw new Error("The Agent Server did not report a safe absolute home directory.");
  return response.home;
}

async function execute(host: CanvasHost, home: string, command: string, timeout: number, signal?: AbortSignal): Promise<string> {
  if (!isValidHomePath(home)) throw new Error("The Agent Server home path failed validation.");
  throwIfAborted(signal);
  const response = await host.agentServer.request<CommandResponse>({ path: "/api/bash/execute_bash_command", method: "POST", body: { command, cwd: home, timeout } });
  throwIfAborted(signal);
  const stdout = typeof response?.stdout === "string" ? response.stdout : "";
  const stderr = typeof response?.stderr === "string" ? response.stderr.trim() : "";
  const exitCode = typeof response?.exit_code === "number" ? response.exit_code : -1;
  if (exitCode !== 0) throw new Error(stderr || "The Agent Server command failed.");
  return stdout;
}

function taggedPayload(stdout: string, tag: string): string {
  const line = stdout.split(/\r?\n/).find((candidate) => candidate.startsWith(`${tag}\t`));
  if (!line) throw new Error(`The native bridge did not return ${tag}.`);
  return line.slice(tag.length + 1).trim();
}

export async function probePrerequisites(host: CanvasHost, home: string, signal?: AbortSignal): Promise<ProbeStatus> {
  const stdout = await execute(host, home, PROBE_COMMAND, 20, signal);
  const encoded = taggedPayload(stdout, "CONVERSATION_SEARCH_PROBE");
  let value: ProbeStatus;
  try { value = JSON.parse(decodeUtf8Base64(encoded)) as ProbeStatus; }
  catch { throw new Error("The prerequisite probe returned malformed data."); }
  if (typeof value.supported !== "boolean" || typeof value.goReady !== "boolean" || typeof value.installed !== "boolean" || typeof value.artifactVerified !== "boolean" || typeof value.target !== "string") throw new Error("The prerequisite probe was incomplete.");
  return value;
}

function parseNative(stdout: string): NativeResponse {
  const encoded = taggedPayload(stdout, "CONVERSATION_SEARCH");
  let envelope: NativeEnvelope;
  try { envelope = JSON.parse(decodeUtf8Base64(encoded)) as NativeEnvelope; }
  catch { throw new Error("The native bridge returned malformed data."); }
  if (envelope.ok !== true) throw new Error(typeof envelope.error === "string" ? envelope.error : "The native bridge reported an unknown error.");
  if (!envelope.data || typeof envelope.data !== "object") throw new Error("The native bridge returned no structured result.");
  return envelope.data as NativeResponse;
}

export function commandForPayload(payload: object, mode: "once" | "rpc" = "once"): string {
  const encoded = utf8Base64(JSON.stringify(payload));
  return String.raw`set -eu
app_dir='.openhands/apps/conversation-search-sidecar'
binary="$app_dir/bin/conversation-search"
artifact="$app_dir/artifact.json"
[ -x "$binary" ] && [ -f "$artifact" ] || { printf 'native runtime is not installed\n' >&2; exit 1; }
for checked in '.openhands' '.openhands/apps' "$app_dir" "$binary" "$artifact"; do [ ! -L "$checked" ] || { printf 'native artifact path contains a symbolic link\n' >&2; exit 1; }; done
sha_file() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'; else shasum -a 256 "$1" | awk '{print $1}'; fi; }
artifact_version=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$artifact")
artifact_source=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sourceSha256"])' "$artifact")
expected=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["binarySha256"])' "$artifact")
[ "$artifact_version" = '${SIDECAR_VERSION}' ] && [ "$artifact_source" = '${SOURCE_SHA256}' ] && [ "$(cat "$app_dir/.runtime-version" 2>/dev/null)" = '${RUNTIME_VERSION}' ] && [ "$(sha_file "$binary")" = "$expected" ] || { printf 'native artifact verification failed; use Repair runtime\n' >&2; exit 1; }
exec "$binary" '${mode}' '${encoded}'`;
}

export async function installOrRepair(host: CanvasHost, home: string, signal?: AbortSignal): Promise<void> {
  parseNative(await execute(host, home, INSTALL_COMMAND, 900, signal));
}

export async function startService(host: CanvasHost, home: string, signal?: AbortSignal): Promise<void> {
  await execute(host, home, START_COMMAND, 30, signal);
}

export async function stopService(host: CanvasHost, home: string, signal?: AbortSignal): Promise<void> {
  await execute(host, home, STOP_COMMAND, 20, signal);
}

export async function repairRuntime(host: CanvasHost, home: string, signal?: AbortSignal): Promise<void> {
  try { await stopService(host, home, signal); }
  catch (error) {
    const recoverable = error instanceof Error && /artifact|binary checksum|runtime is missing/.test(error.message);
    if (!recoverable) throw error;
  }
  await installOrRepair(host, home, signal);
  await stopService(host, home, signal);
}

export async function deleteAppData(host: CanvasHost, home: string, signal?: AbortSignal): Promise<void> {
  await execute(host, home, DELETE_COMMAND, 30, signal);
}

export async function runNative(host: CanvasHost, home: string, payload: object, mode: "once" | "rpc", signal?: AbortSignal): Promise<NativeResponse> {
  const action = "action" in payload ? String((payload as { action?: unknown }).action) : "";
  const timeout = ["index", "rebuild", "repair"].includes(action) ? 900 : 60;
  return parseNative(await execute(host, home, commandForPayload(payload, mode), timeout, signal));
}

export async function loadStatus(host: CanvasHost, home: string, mode: "once" | "rpc", signal?: AbortSignal): Promise<IndexStatus> {
  const response = await runNative(host, home, { action: "status" }, mode, signal);
  if (!response.status) throw new Error("The native bridge omitted index status.");
  return response.status;
}

export async function updateIndex(host: CanvasHost, home: string, rebuild: boolean, mode: "once" | "rpc", signal?: AbortSignal): Promise<IndexStatus> {
  const response = await runNative(host, home, { action: rebuild ? "rebuild" : "index" }, mode, signal);
  if (!response.status) throw new Error("The native bridge omitted index status.");
  return response.status;
}

export async function search(host: CanvasHost, home: string, query: string, filters: SearchFilters, mode: "once" | "rpc", signal?: AbortSignal): Promise<SearchResponse> {
  const response = await runNative(host, home, { action: "search", query, filters, limit: 40 }, mode, signal);
  if (!response.search) throw new Error("The native bridge omitted search results.");
  return response.search;
}

export async function inspectResult(host: CanvasHost, home: string, documentId: string, mode: "once" | "rpc", signal?: AbortSignal): Promise<SearchHit> {
  const response = await runNative(host, home, { action: "inspect", documentId }, mode, signal);
  if (!response.hit) throw new Error("The native bridge omitted the indexed event.");
  return response.hit;
}

export function agentSetupText(home: string): string {
  const directory = dataDirectory(home);
  return `Set up Conversation Search Sidecar on this Agent Server. First inspect the host OS/architecture, Go availability, the App's bundled source under its installed copy, and ${directory}. Explain every package/network/filesystem change and obtain my approval before installing anything. Build only the pinned Go module from the App's reviewed source; verify its source checksums from artifact-metadata.json; place all build caches, binary, logs, run state, source manifest, and Bleve index below ${directory}; record and verify the resulting binary SHA-256; do not read or change conversation source data during setup; do not expose a general shell or daemon port; then tell me to use Recheck in the App.`;
}
