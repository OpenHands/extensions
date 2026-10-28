import { describe, expect, it, vi } from "vitest";
import {
  APP_SUBPATH,
  DELETE_COMMAND,
  INSTALL_COMMAND,
  PROBE_COMMAND,
  START_COMMAND,
  STOP_COMMAND,
  agentSetupText,
  commandForPayload,
  dataDirectory,
  deleteAppData,
  discoverHome,
  installOrRepair,
  isValidHomePath,
  probePrerequisites,
  repairRuntime,
  runNative,
  startService,
  stopService,
} from "./native-service";
import type { AgentServerRequest, CanvasHost } from "./types";

const HOME = "/Users/tester";
function encode(value: unknown): string { return btoa(JSON.stringify(value)); }
function native(data?: unknown, error?: string): string { return `CONVERSATION_SEARCH\t${encode(error ? { ok: false, error } : { ok: true, data })}\n`; }
function hostWith(request: (request: AgentServerRequest) => Promise<unknown>): CanvasHost {
  return { apiVersion: "1", extension: { name: "conversation-search-sidecar", version: "0.1.0" }, backend: { id: "local" }, agentServer: { request: request as CanvasHost["agentServer"]["request"] }, registerPage: vi.fn(), navigate: vi.fn() };
}

describe("home and non-mutating prerequisite discovery", () => {
  it("discovers and validates the Agent Server home", async () => {
    const request = vi.fn(async () => ({ home: HOME }));
    await expect(discoverHome(hostWith(request))).resolves.toBe(HOME);
    expect(request).toHaveBeenCalledWith({ path: "/api/file/home" });
    expect(dataDirectory(HOME)).toBe(`${HOME}/${APP_SUBPATH}`);
  });

  it.each(["", "relative", "/tmp/../escape", "/tmp//double", "/tmp\nunsafe"])("rejects unsafe home %j", (value) => expect(isValidHomePath(value)).toBe(false));

  it("parses platform, toolchain, installation, and both required layouts from a read-only probe", async () => {
    const locations = [{ path: `${HOME}/.openhands/dev_conversations`, layout: "sdk-dev", state: "empty", conversations: 0, files: 0, malformed: 0 }, { path: `${HOME}/.openhands/conversations`, layout: "sdk-standard", state: "missing", conversations: 0, files: 0, malformed: 0 }];
    const result = { os: "Darwin", arch: "arm64", target: "darwin-arm64", supported: true, goVersion: "go version go1.25 darwin/arm64", goReady: true, installed: false, runtimeVersion: null, binaryPresent: false, artifactPresent: false, artifactVerified: false, locations };
    const request = vi.fn(async () => ({ exit_code: 0, stdout: `CONVERSATION_SEARCH_PROBE\t${encode(result)}\n`, stderr: "" }));
    await expect(probePrerequisites(hostWith(request), HOME)).resolves.toEqual(result);
    expect(request).toHaveBeenCalledWith({ path: "/api/bash/execute_bash_command", method: "POST", body: { command: PROBE_COMMAND, cwd: HOME, timeout: 20 } });
    expect(PROBE_COMMAND).not.toMatch(/mkdir|write_text|write_bytes|unlink|rmtree/);
    expect(PROBE_COMMAND).toContain('base / "dev_conversations"');
    expect(PROBE_COMMAND).toContain('base / "conversations"');
    expect(PROBE_COMMAND).toContain("hashlib.sha256");
    expect(PROBE_COMMAND).toContain("artifact_verified");
  });
});

describe("verified runtime lifecycle", () => {
  it("uses a fixed local-build template with pinned source verification and App-scoped caches", async () => {
    const request = vi.fn(async () => ({ exit_code: 0, stdout: native({ message: "conversation-search 0.1.0" }), stderr: "" }));
    await installOrRepair(hostWith(request), HOME);
    expect(request).toHaveBeenCalledWith({ path: "/api/bash/execute_bash_command", method: "POST", body: { command: INSTALL_COMMAND, cwd: HOME, timeout: 900 } });
    expect(INSTALL_COMMAND).toContain("go mod download");
    expect(INSTALL_COMMAND).toContain("GOMODCACHE");
    expect(INSTALL_COMMAND).toContain("main.go checksum mismatch");
    expect(INSTALL_COMMAND).toContain("binarySha256");
    expect(INSTALL_COMMAND).toContain("Go 1.23+");
    expect(INSTALL_COMMAND).not.toContain(HOME);
  });

  it("keeps start, stop, and deletion distinct and exact", async () => {
    const request = vi.fn(async (_request: AgentServerRequest) => ({ exit_code: 0, stdout: "ok\n", stderr: "" }));
    const host = hostWith(request);
    await startService(host, HOME); await stopService(host, HOME); await deleteAppData(host, HOME);
    expect(request.mock.calls.map((call) => (call[0].body as { command: string }).command)).toEqual([START_COMMAND, STOP_COMMAND, DELETE_COMMAND]);
    expect(START_COMMAND).toContain("binary checksum mismatch");
    expect(START_COMMAND).toContain("artifact version/source mismatch");
    expect(START_COMMAND).toContain("nohup");
    expect(STOP_COMMAND).not.toMatch(/\bkill\b/);
    expect(STOP_COMMAND).toContain("sha_file");
    expect(DELETE_COMMAND).toContain("app_dir='.openhands/apps/conversation-search-sidecar'");
    expect(DELETE_COMMAND).toContain('target=apps/"conversation-search-sidecar"');
    expect(DELETE_COMMAND).toContain("is_relative_to(base)");
    expect(DELETE_COMMAND).toContain("repair and stop before deletion");
  });

  it("repairs an unverifiable runtime from reviewed source before using the replacement CLI", async () => {
    let stops = 0;
    const request = vi.fn(async (request: AgentServerRequest) => {
      const command = (request.body as { command: string }).command;
      if (command === STOP_COMMAND && stops++ === 0) return { exit_code: 1, stdout: "", stderr: "native artifact verification failed; use Repair runtime" };
      return { exit_code: 0, stdout: command === INSTALL_COMMAND ? native({ message: "installed" }) : "CONVERSATION_SEARCH_STOPPED\tstopped\n", stderr: "" };
    });
    await repairRuntime(hostWith(request), HOME);
    expect(request.mock.calls.map((call) => (call[0].body as { command: string }).command)).toEqual([STOP_COMMAND, INSTALL_COMMAND, STOP_COMMAND]);
  });
});

describe("structured companion CLI", () => {
  it("base64-encodes user text so it never becomes shell source", async () => {
    const query = "'$HOME'; touch /tmp/never; native phrase";
    const command = commandForPayload({ action: "search", query, filters: { tool: "terminal" } }, "rpc");
    expect(command).not.toContain(query);
    expect(command).toContain("native artifact verification failed");
    expect(command).toContain("sha_file");
    expect(command).toMatch(/exec "\$binary" 'rpc' '[A-Za-z0-9+/=]+'$/);
    const response = { search: { total: 0, durationMs: 1, hits: [], status: { ready: true } } };
    const request = vi.fn(async (_request: AgentServerRequest) => ({ exit_code: 0, stdout: native(response), stderr: "" }));
    await expect(runNative(hostWith(request), HOME, { action: "search", query }, "rpc")).resolves.toEqual(response);
    expect((request.mock.calls[0][0].body as { command: string }).command).not.toContain("touch /tmp/never");
  });

  it("surfaces native and transport failures", async () => {
    await expect(runNative(hostWith(async () => ({ exit_code: 0, stdout: native(undefined, "index corrupt"), stderr: "" })), HOME, { action: "search", query: "x" }, "once")).rejects.toThrow("index corrupt");
    await expect(runNative(hostWith(async () => ({ exit_code: 2, stdout: "", stderr: "binary missing" })), HOME, { action: "status" }, "once")).rejects.toThrow("binary missing");
  });

  it("produces a consent-focused agent setup prompt", () => {
    const prompt = agentSetupText(HOME);
    expect(prompt).toContain(`${HOME}/${APP_SUBPATH}`);
    expect(prompt).toContain("obtain my approval");
    expect(prompt).toContain("verify its source checksums");
    expect(prompt).toContain("do not expose");
  });
});
