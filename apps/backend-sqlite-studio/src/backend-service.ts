import type { CanvasHost, DatabaseSnapshot, ProbeStatus, QueryResponse } from "./types";

export const DATA_SUBPATH = ".openhands/apps/backend-sqlite-studio";
export const DATABASE_FILENAME = "studio.sqlite3";
export const RUNTIME_VERSION = "1";
export const MAX_IMPORT_BYTES = 16 * 1024 * 1024;

const WRAPPER_SOURCE = String.raw`from __future__ import annotations
import base64, json, os, re, sqlite3, sys, time
from datetime import datetime, timezone
from pathlib import Path

APP_SUBPATH = Path(".openhands/apps/backend-sqlite-studio")
ROOT = (Path.cwd() / APP_SUBPATH).resolve()
EXPECTED = (Path.cwd().resolve() / APP_SUBPATH).resolve()
if ROOT != EXPECTED:
    raise RuntimeError("App data path escaped the Agent Server home")
DB = ROOT / "studio.sqlite3"
MIGRATIONS = [
    ("001-create-notes", """CREATE TABLE IF NOT EXISTS notes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      body TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )"""),
]

def now():
    return datetime.now(timezone.utc).isoformat()

def connect(path=DB):
    conn = sqlite3.connect(path, timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn

def internal(conn):
    conn.executescript("""
      CREATE TABLE IF NOT EXISTS _backend_sqlite_studio_migrations (
        id TEXT PRIMARY KEY, applied_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS _backend_sqlite_studio_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sql TEXT NOT NULL, status TEXT NOT NULL,
        executed_at TEXT NOT NULL, message TEXT NOT NULL DEFAULT ''
      );
    """)
    conn.commit()

def migrate(conn):
    internal(conn)
    applied = {row[0] for row in conn.execute("SELECT id FROM _backend_sqlite_studio_migrations")}
    for migration_id, sql in MIGRATIONS:
        if migration_id in applied:
            continue
        try:
            conn.execute("BEGIN")
            conn.execute(sql)
            conn.execute("INSERT INTO _backend_sqlite_studio_migrations(id, applied_at) VALUES (?, ?)", (migration_id, now()))
            conn.commit()
        except Exception:
            conn.rollback()
            raise

def json_value(value):
    if isinstance(value, bytes):
        return {"blobBytes": len(value)}
    return value

def snapshot(conn):
    internal(conn)
    tables = []
    for name, sql in conn.execute("""SELECT name, COALESCE(sql, '') FROM sqlite_master
      WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_backend_sqlite_studio_%'
      ORDER BY name"""):
        escaped = name.replace('"', '""')
        columns = [{"name": row[1], "type": row[2] or "ANY", "nullable": not bool(row[3]) and not bool(row[5]), "primaryKey": bool(row[5])}
                   for row in conn.execute(f'PRAGMA table_info("{escaped}")')]
        tables.append({"name": name, "sql": sql, "columns": columns})
    migrations = [{"id": row[0], "appliedAt": row[1]} for row in conn.execute(
        "SELECT id, applied_at FROM _backend_sqlite_studio_migrations ORDER BY id")]
    history = [{"id": row[0], "sql": row[1], "status": row[2], "executedAt": row[3], "message": row[4]}
               for row in conn.execute("SELECT id, sql, status, executed_at, message FROM _backend_sqlite_studio_history ORDER BY id DESC LIMIT 40")]
    return {"initialized": True, "databasePath": str(DB), "sizeBytes": DB.stat().st_size if DB.exists() else 0,
            "journalMode": conn.execute("PRAGMA journal_mode").fetchone()[0], "tables": tables,
            "migrations": migrations, "history": history}

def ensure_safe(statements):
    for statement in statements:
        scrubbed = re.sub(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|--[^\n]*|/\*.*?\*/", " ", statement, flags=re.S)
        upper = " ".join(scrubbed.upper().split())
        first = upper.split(" ", 1)[0] if upper else ""
        outside_boundary = (
            first in {"ATTACH", "DETACH", "BEGIN", "COMMIT", "END", "ROLLBACK", "SAVEPOINT", "RELEASE"}
            or re.search(r"\bVACUUM\s+INTO\b", upper)
            or re.search(r"\bLOAD_EXTENSION\b|\bWRITABLE_SCHEMA\b|_BACKEND_SQLITE_STUDIO_", upper)
        )
        if outside_boundary:
            raise ValueError("That statement is outside this App's database boundary")

def record(sql, status, message=""):
    with connect() as history_conn:
        internal(history_conn)
        history_conn.execute("INSERT INTO _backend_sqlite_studio_history(sql, status, executed_at, message) VALUES (?, ?, ?, ?)",
                             (sql[:20000], status, now(), message[:1000]))
        history_conn.commit()

def handle(request):
    action = request.get("action")
    if action == "initialize":
        ROOT.mkdir(parents=True, exist_ok=True)
        with connect() as conn:
            migrate(conn)
            return snapshot(conn)
    if action == "import":
        raw = base64.b64decode(request.get("databaseBase64", ""), validate=True)
        if len(raw) > 16 * 1024 * 1024 or not raw.startswith(b"SQLite format 3\x00"):
            raise ValueError("Import must be a valid SQLite file no larger than 16 MiB")
        ROOT.mkdir(parents=True, exist_ok=True)
        temporary = ROOT / ".import.sqlite3.tmp"
        temporary.write_bytes(raw)
        try:
            with connect(temporary) as check:
                result = check.execute("PRAGMA integrity_check").fetchone()[0]
                if result != "ok": raise ValueError("SQLite integrity check failed")
            for suffix in ("-wal", "-shm", "-journal"):
                Path(str(DB) + suffix).unlink(missing_ok=True)
            os.replace(temporary, DB)
            with connect() as conn:
                migrate(conn)
                record("[database import]", "success", f"Imported {len(raw)} bytes")
                return snapshot(conn)
        finally:
            temporary.unlink(missing_ok=True)
    if not DB.exists():
        raise RuntimeError("Database is not initialized")
    if action == "status":
        with connect() as conn:
            return snapshot(conn)
    if action == "export":
        temporary = ROOT / ".export.sqlite3.tmp"
        try:
            with connect() as source, sqlite3.connect(temporary) as destination:
                source.backup(destination)
            raw = temporary.read_bytes()
            return {"databaseBase64": base64.b64encode(raw).decode("ascii"), "sizeBytes": len(raw)}
        finally:
            temporary.unlink(missing_ok=True)
    if action == "query":
        statements = request.get("statements")
        sql = request.get("sql", "")
        if not isinstance(statements, list) or not statements:
            raise ValueError("Enter a complete SQL statement before running the query")
        ensure_safe(statements)
        started = time.perf_counter()
        with connect() as conn:
            migrate(conn)
            before = conn.total_changes
            results = []
            try:
                conn.execute("BEGIN")
                for statement in statements:
                    cursor = conn.execute(statement)
                    if cursor.description:
                        values = [[json_value(value) for value in row] for row in cursor.fetchmany(251)]
                        results.append({"columns": [item[0] for item in cursor.description], "values": values[:250], "truncated": len(values) > 250})
                conn.commit()
                affected = conn.total_changes - before
            except Exception as exc:
                conn.rollback()
                record(sql, "error", str(exc))
                raise
        record(sql, "success")
        with connect() as conn:
            result = snapshot(conn)
        result.update({"results": results, "rowsAffected": affected, "durationMs": (time.perf_counter() - started) * 1000})
        return result
    raise ValueError("Unknown structured database action")

try:
    payload = json.loads(base64.b64decode(sys.argv[1]).decode("utf-8"))
    result = {"ok": True, "data": handle(payload)}
except Exception as exc:
    result = {"ok": False, "error": str(exc)}
encoded = base64.b64encode(json.dumps(result, separators=(",", ":")).encode("utf-8")).decode("ascii")
print("BACKEND_SQLITE_STUDIO\t" + encoded)
`;

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

const WRAPPER_BASE64 = utf8Base64(WRAPPER_SOURCE);
const INITIALIZE_PAYLOAD = utf8Base64(JSON.stringify({ action: "initialize" }));

export const PROBE_COMMAND = String.raw`python_ready=0
python_version=''
python_sqlite=''
sqlite_cli=''
if command -v python3 >/dev/null 2>&1; then
  python_version=$(python3 --version 2>&1 || true)
  if python3 -c 'import sqlite3; print(sqlite3.sqlite_version)' >/dev/null 2>&1; then
    python_ready=1
    python_sqlite=$(python3 -c 'import sqlite3; print(sqlite3.sqlite_version)' 2>/dev/null || true)
  fi
fi
if command -v sqlite3 >/dev/null 2>&1; then sqlite_cli=$(sqlite3 --version 2>/dev/null || true); fi
app_dir='.openhands/apps/backend-sqlite-studio'
wrapper_present=0; database_present=0; initialized=0; runtime_version=''
[ -f "$app_dir/wrapper.py" ] && wrapper_present=1
[ -f "$app_dir/studio.sqlite3" ] && database_present=1
[ -f "$app_dir/.runtime-version" ] && runtime_version=$(head -c 40 "$app_dir/.runtime-version" 2>/dev/null || true)
[ "$wrapper_present" -eq 1 ] && [ "$database_present" -eq 1 ] && [ "$runtime_version" = '1' ] && initialized=1
probe_json=$(printf '{"pythonReady":%s,"pythonVersion":"%s","sqliteModuleVersion":"%s","sqliteCliVersion":"%s","initialized":%s,"wrapperPresent":%s,"databasePresent":%s,"runtimeVersion":"%s"}' "$python_ready" "$python_version" "$python_sqlite" "$sqlite_cli" "$initialized" "$wrapper_present" "$database_present" "$runtime_version")
if printf '%s' "$probe_json" | base64 --decode >/dev/null 2>&1; then :; fi
probe64=$(printf '%s' "$probe_json" | base64 | tr -d '\n')
printf 'BACKEND_SQLITE_STUDIO_PROBE\t%s\n' "$probe64"`;

export const INSTALL_COMMAND = String.raw`app_dir='.openhands/apps/backend-sqlite-studio'
mkdir -p "$app_dir"
wrapper64='${WRAPPER_BASE64}'
temporary="$app_dir/.wrapper.py.tmp"
if printf '%s' "$wrapper64" | base64 --decode > "$temporary" 2>/dev/null; then :
else printf '%s' "$wrapper64" | base64 -D > "$temporary"; fi
chmod 700 "$temporary"
mv "$temporary" "$app_dir/wrapper.py"
printf '%s' '${RUNTIME_VERSION}' > "$app_dir/.runtime-version"
python3 "$app_dir/wrapper.py" '${INITIALIZE_PAYLOAD}'`;

export const RESET_COMMAND = String.raw`python3 -c 'import pathlib, shutil; base=pathlib.Path.cwd().resolve(); target=(base/".openhands/apps/backend-sqlite-studio").resolve(); expected=(base/".openhands/apps/backend-sqlite-studio").resolve(); target == expected or (_ for _ in ()).throw(RuntimeError("unsafe reset target")); shutil.rmtree(target) if target.exists() else None; print("BACKEND_SQLITE_STUDIO_RESET")'`;

export const AGENT_SETUP_PROMPT_PREFIX = `Work with the Backend SQLite Studio database on this Agent Server. The exact database path is`;

interface CommandResponse { exit_code?: unknown; stdout?: unknown; stderr?: unknown }
interface HomeResponse { home?: unknown }

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) throw new DOMException("The Agent Server request was cancelled.", "AbortError");
}

export function isValidHomePath(path: unknown): path is string {
  if (typeof path !== "string" || path.length < 2 || path.length > 4096 || !path.startsWith("/")) return false;
  if (/[\0-\x1f\x7f]/.test(path) || path.includes("//")) return false;
  return path.split("/").filter(Boolean).every((segment) => segment !== "." && segment !== "..");
}

export function dataDirectory(home: string): string {
  if (!isValidHomePath(home)) throw new Error("The Agent Server returned an unsafe home path.");
  return `${home.replace(/\/+$/, "")}/${DATA_SUBPATH}`;
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
  const response = await host.agentServer.request<CommandResponse>({
    path: "/api/bash/execute_bash_command", method: "POST", body: { command, cwd: home, timeout },
  });
  throwIfAborted(signal);
  const stdout = typeof response?.stdout === "string" ? response.stdout : "";
  const stderr = typeof response?.stderr === "string" ? response.stderr.trim() : "";
  const exitCode = typeof response?.exit_code === "number" ? response.exit_code : -1;
  if (exitCode !== 0) throw new Error(stderr || `The controlled backend command failed with exit code ${exitCode}.`);
  return stdout;
}

function parseEnvelope<T>(output: string): T {
  const match = output.match(/^BACKEND_SQLITE_STUDIO\t([A-Za-z0-9+/=]+)$/m);
  if (!match) throw new Error("The SQLite wrapper returned an unexpected response.");
  let parsed: { ok?: boolean; data?: T; error?: string };
  try { parsed = JSON.parse(decodeUtf8Base64(match[1])); }
  catch { throw new Error("The SQLite wrapper response could not be decoded."); }
  if (!parsed.ok) throw new Error(parsed.error || "The SQLite wrapper failed.");
  return parsed.data as T;
}

export function commandForPayload(payload: unknown): string {
  const encoded = utf8Base64(JSON.stringify(payload));
  if (!/^[A-Za-z0-9+/=]+$/.test(encoded)) throw new Error("The structured SQLite payload could not be safely encoded.");
  return `python3 '${DATA_SUBPATH}/wrapper.py' '${encoded}'`;
}

export async function probePrerequisites(host: CanvasHost, home: string, signal?: AbortSignal): Promise<ProbeStatus> {
  const output = await execute(host, home, PROBE_COMMAND, 15, signal);
  const match = output.match(/^BACKEND_SQLITE_STUDIO_PROBE\t([A-Za-z0-9+/=]+)$/m);
  if (!match) throw new Error("The prerequisite probe returned an unexpected response.");
  try {
    const raw = JSON.parse(decodeUtf8Base64(match[1])) as Record<string, unknown>;
    return {
      pythonReady: raw.pythonReady === 1,
      pythonVersion: typeof raw.pythonVersion === "string" && raw.pythonVersion ? raw.pythonVersion : null,
      sqliteModuleVersion: typeof raw.sqliteModuleVersion === "string" && raw.sqliteModuleVersion ? raw.sqliteModuleVersion : null,
      sqliteCliVersion: typeof raw.sqliteCliVersion === "string" && raw.sqliteCliVersion ? raw.sqliteCliVersion : null,
      initialized: raw.initialized === 1,
      wrapperPresent: raw.wrapperPresent === 1,
      databasePresent: raw.databasePresent === 1,
      runtimeVersion: typeof raw.runtimeVersion === "string" && raw.runtimeVersion ? raw.runtimeVersion : null,
    };
  } catch { throw new Error("The prerequisite probe returned malformed data."); }
}

export async function installOrRepair(host: CanvasHost, home: string, signal?: AbortSignal): Promise<DatabaseSnapshot> {
  return parseEnvelope(await execute(host, home, INSTALL_COMMAND, 30, signal));
}

export async function loadDatabase(host: CanvasHost, home: string, signal?: AbortSignal): Promise<DatabaseSnapshot> {
  return parseEnvelope(await execute(host, home, commandForPayload({ action: "status" }), 20, signal));
}

export function parseSqlStatements(sql: string): string[] {
  const statements: string[] = [];
  let current = "", quote = "", lineComment = false, blockComment = false;
  for (let index = 0; index < sql.length; index += 1) {
    const char = sql[index], next = sql[index + 1] ?? "";
    if (lineComment) { current += char; if (char === "\n") lineComment = false; continue; }
    if (blockComment) { current += char; if (char === "*" && next === "/") { current += next; index += 1; blockComment = false; } continue; }
    if (quote) {
      current += char;
      if (char === quote) {
        if (next === quote && quote !== "]") { current += next; index += 1; }
        else quote = "";
      }
      continue;
    }
    if (char === "-" && next === "-") { current += char + next; index += 1; lineComment = true; continue; }
    if (char === "/" && next === "*") { current += char + next; index += 1; blockComment = true; continue; }
    if (char === "'" || char === '"' || char === "`") { quote = char; current += char; continue; }
    if (char === "[") { quote = "]"; current += char; continue; }
    if (char === ";") { if (current.trim()) statements.push(current.trim()); current = ""; continue; }
    current += char;
  }
  if (quote || blockComment) throw new Error("The SQL editor contains an unterminated quote or comment.");
  if (current.trim()) statements.push(current.trim());
  return statements;
}

export async function runQuery(host: CanvasHost, home: string, sql: string, signal?: AbortSignal): Promise<QueryResponse> {
  const statements = parseSqlStatements(sql);
  if (!statements.length) throw new Error("Enter a SQL statement before running the query.");
  return parseEnvelope(await execute(host, home, commandForPayload({ action: "query", sql, statements }), 60, signal));
}

export async function exportDatabase(host: CanvasHost, home: string, signal?: AbortSignal): Promise<{ bytes: Uint8Array; sizeBytes: number }> {
  const result = parseEnvelope<{ databaseBase64: string; sizeBytes: number }>(await execute(host, home, commandForPayload({ action: "export" }), 30, signal));
  const bytes = Uint8Array.from(atob(result.databaseBase64), (character) => character.charCodeAt(0));
  return { bytes, sizeBytes: result.sizeBytes };
}

export async function importDatabase(host: CanvasHost, home: string, bytes: Uint8Array, signal?: AbortSignal): Promise<DatabaseSnapshot> {
  if (bytes.byteLength > MAX_IMPORT_BYTES) throw new Error("Import is limited to 16 MiB.");
  let binary = ""; for (const byte of bytes) binary += String.fromCharCode(byte);
  return parseEnvelope(await execute(host, home, commandForPayload({ action: "import", databaseBase64: btoa(binary) }), 60, signal));
}

export async function resetData(host: CanvasHost, home: string, signal?: AbortSignal): Promise<void> {
  const output = await execute(host, home, RESET_COMMAND, 20, signal);
  if (!output.includes("BACKEND_SQLITE_STUDIO_RESET")) throw new Error("The reset command returned an unexpected response.");
}

export function agentHandoffText(home: string): string {
  const databasePath = `${dataDirectory(home)}/${DATABASE_FILENAME}`;
  return `${AGENT_SETUP_PROMPT_PREFIX} ${databasePath}\n\nUse Python's sqlite3 module (or sqlite3 CLI) and open only that database. Before writing, inspect its schema and preserve tables prefixed _backend_sqlite_studio_, which hold migrations and query history. Use parameterized SQL for values, a transaction for mutations, and a 10-second busy timeout. Do not move, replace, reset, or delete the database or its parent directory. Report the SQL operation, affected rows, and any schema changes when finished.`;
}

export function agentSetupText(home: string): string {
  const directory = dataDirectory(home);
  return `Set up the prerequisite for the Backend SQLite Studio App on this Agent Server. The App's proposed data directory is ${directory}, but do not create, replace, reset, or delete that directory yourself. First inspect whether python3 can import the standard sqlite3 module and report both Python and SQLite versions. If that runtime is missing, identify the operating system and package manager, explain the exact install command and files it may change, and obtain my approval before installing Python 3 with SQLite support. Do not install anything if the runtime is already usable. Verify with "python3 -c 'import sqlite3; print(sqlite3.sqlite_version)'", then tell me to use Recheck and the deliberate Install or Repair action in the App.`;
}

export const __testing = { WRAPPER_SOURCE };
