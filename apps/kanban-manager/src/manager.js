/* Creating and stopping the per-workspace manager automation.

   This is the one piece of vibe-manager that used to require its FastAPI
   service: `ensure_manager_automation` in app.py packed automation/ into a
   tar.gz, uploaded it and created a cron automation. Canvas extensions have no
   server side, so the browser does all three itself:

     1. The automation sources are compiled into the bundle (build.mjs injects
        __VIBE_AUTOMATION__ from ../../automation/*.py), because there is no
        vibe-manager checkout to read them from on the Canvas machine.
     2. tar + gzip happen here — a ustar archive is 512-byte blocks, and
        CompressionStream("gzip") is in every browser Canvas supports.
     3. The upload is a RAW fetch, not host.agentServer.request: the host
        client JSON.stringifies every body that isn't FormData, which would
        corrupt the gzip bytes. The JSON calls around it do go through the
        host client (same path live.js uses for the status badge).

   The automation name matches app.py's `_automation_name`, so a workspace
   already bootstrapped by the service is refreshed rather than duplicated. */

import { resolveBackendCredentials } from "./store.js";

const AUTOMATION_BASE = "/api/automation/v1";

/* Only a fallback: the automation runner injects AGENT_SERVER_URL, which
   main.py prefers. This is what app.py wrote for the same field. */
const DEFAULT_AGENT_SERVER = "http://127.0.0.1:18000";

const CRON_EVERY_MINUTE = "* * * * *";
const RUN_TIMEOUT_SECONDS = 300;

// Injected by build.mjs: {"main.py": "<source>", ...}.
const AUTOMATION_SOURCES =
  typeof __VIBE_AUTOMATION__ === "object" && __VIBE_AUTOMATION__ ? __VIBE_AUTOMATION__ : {};

const encoder = new TextEncoder();

export function automationName(ws) {
  return `Vibe Manager — ${ws.name} (${ws.id})`;
}

function putString(block, offset, value, length) {
  // Every ustar field is NUL-terminated, so a value may fill length - 1 bytes.
  block.set(encoder.encode(value).subarray(0, length - 1), offset);
}

function putOctal(block, offset, value, length) {
  putString(block, offset, value.toString(8).padStart(length - 1, "0"), length);
}

function header(name, size, mtime) {
  const block = new Uint8Array(512);
  putString(block, 0, name, 100);
  putOctal(block, 100, 0o644, 8); // mode
  putOctal(block, 108, 0, 8); // uid
  putOctal(block, 116, 0, 8); // gid
  putOctal(block, 124, size, 12);
  putOctal(block, 136, mtime, 12);
  block.fill(32, 148, 156); // checksum is computed over spaces here
  block[156] = 48; // typeflag "0": regular file
  putString(block, 257, "ustar", 6);
  block[263] = 48; // version "00"
  block[264] = 48;
  putString(block, 265, "root", 32);
  putString(block, 297, "root", 32);

  let sum = 0;
  for (const byte of block) sum += byte;
  // The checksum field is 6 octal digits, a NUL and a space.
  putString(block, 148, sum.toString(8).padStart(6, "0"), 8);
  block[154] = 0;
  block[155] = 32;
  return block;
}

/** Minimal ustar archive of {name: text} — enough for the automation package. */
export function tar(files, mtime = Math.floor(Date.now() / 1000)) {
  const blocks = [];
  let size = 0;
  for (const [name, text] of Object.entries(files)) {
    const data = encoder.encode(text);
    const padded = new Uint8Array(Math.ceil(data.length / 512) * 512);
    padded.set(data);
    const head = header(name, data.length, mtime);
    blocks.push(head, padded);
    size += head.length + padded.length;
  }
  // Two zero blocks terminate the archive.
  const trailer = new Uint8Array(1024);
  blocks.push(trailer);
  size += trailer.length;

  const out = new Uint8Array(size);
  let at = 0;
  for (const block of blocks) {
    out.set(block, at);
    at += block.length;
  }
  return out;
}

export async function gzip(bytes) {
  const stream = new Blob([bytes]).stream().pipeThrough(new CompressionStream("gzip"));
  return new Response(stream).blob();
}

export class Manager {
  constructor(host, store) {
    this.host = host;
    this.store = store;
  }

  request(path, { method = "GET", body } = {}) {
    return this.host.agentServer.request({ method, path: `${AUTOMATION_BASE}${path}`, body });
  }

  /** config.json for the automation package — see automation/main.py. */
  async config(ws) {
    return {
      workspace_id: ws.id,
      workspace_path: ws.path,
      workspace_name: ws.name,
      agent_server: DEFAULT_AGENT_SERVER,
      canvas_base: window.location.origin,
      // The board the automation must read is the one this tab writes, which
      // is not necessarily under the automation user's own home.
      store_dir: await this.store.storeRoot(),
    };
  }

  async tarball(ws) {
    if (!Object.keys(AUTOMATION_SOURCES).length) {
      throw new Error("automation sources missing from the bundle");
    }
    return gzip(tar({
      ...AUTOMATION_SOURCES,
      "config.json": `${JSON.stringify(await this.config(ws), null, 2)}\n`,
    }));
  }

  /** Upload the tarball; returns the oh-internal:// path the API assigns. */
  async upload(ws, blob) {
    const creds = resolveBackendCredentials(this.host?.backend?.id);
    if (!creds) throw new Error("no backend credentials available for the tarball upload");
    const query = new URLSearchParams({
      name: `vibe-manager-${ws.id}`,
      description: `Vibe manager for ${ws.path}`,
    });
    const res = await fetch(`${creds.host}${AUTOMATION_BASE}/uploads?${query}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/gzip",
        ...(creds.apiKey ? { "X-Session-API-Key": creds.apiKey } : {}),
      },
      body: blob,
    });
    if (!res.ok) throw new Error(`tarball upload failed: ${res.status} ${res.statusText}`);
    const { tarball_path: tarballPath } = await res.json();
    if (!tarballPath) throw new Error("upload returned no tarball_path");
    return tarballPath;
  }

  async findByName(name) {
    const res = await this.request("?limit=100");
    return (res?.automations || []).find((a) => a.name === name)?.id ?? null;
  }

  /** Create the manager automation, or refresh + re-enable an existing one.

      Refreshing on every start is deliberate: the sources in this bundle are
      the ones that must run, and a "Start manager" on a workspace whose
      automation was stopped weeks ago should not resurrect stale code. */
  async ensure(ws) {
    const name = automationName(ws);
    const existingId = ws.automation_id || (await this.findByName(name));
    const tarballPath = await this.upload(ws, await this.tarball(ws));

    if (existingId) {
      await this.request(`/${existingId}`, {
        method: "PATCH",
        body: { tarball_path: tarballPath, enabled: true },
      });
      return existingId;
    }
    const created = await this.request("", {
      method: "POST",
      body: {
        name,
        trigger: { type: "cron", schedule: CRON_EVERY_MINUTE, timezone: "UTC" },
        tarball_path: tarballPath,
        entrypoint: "python3 main.py",
        timeout: RUN_TIMEOUT_SECONDS,
      },
    });
    const id = created?.id;
    if (!id) throw new Error("automation backend returned no automation id");
    return id;
  }

  /** Stop the manager: the automation stays, disabled, so it can be restarted
      with its history intact (deleting it would lose the run log). */
  async stop(automationId) {
    if (!automationId) throw new Error("manager automation not configured for this workspace");
    await this.request(`/${automationId}`, { method: "PATCH", body: { enabled: false } });
  }
}
