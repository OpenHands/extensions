"""
Datadog Error Monitor - OpenHands Automation Script

Polls Datadog for log errors on a cron schedule. On each run:
  1. Queries Datadog logs using a pre-configured filter query.
  2. Matches each log against known error patterns (regex).
  3. Tracks hit counts per pattern across runs.
  4. If unknown/uncategorized logs are detected OR a pattern count spikes
     significantly, creates a single OpenHands investigation conversation.
  5. The conversation agent categorizes unknown logs, investigates root causes,
     optionally creates PRs, and posts a summary to Slack.

Configuration. Two setup paths write it, and both end up here:
  - the agent-driven path (SKILL.md) substitutes these constants directly
    into a copy of this file before packaging it;
  - the catalog path packs an unmodified copy and ships a rendered
    config.json beside it, which is loaded over these defaults below.
A declarative host cannot rewrite Python - the catalog schema admits data,
not code - so the constants stay as the defaults and config.json is the
override, rather than one path being expressed in terms of the other.
See SKILL.md for the full setup workflow.

Required secrets (set in OpenHands Settings -> Secrets):
  DD_API_KEY      - Datadog API key
  DD_APP_KEY      - Datadog Application key (required for log search)
  SLACK_BOT_TOKEN - Slack bot token (chat:write scope)

Optional secret:
  OPENHANDS_URL - base URL for conversation links (default: http://localhost:8000)
"""

import json
import os
import re
import sys
from pathlib import Path
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

# ── Embedded configuration (defaults; overridden by config.json when present) ──
DD_QUERY = "service:(deploy OR runtime-api) status:error"
DD_SITE = "datadoghq.com"
SLACK_CHANNEL_ID = "C0123456789"
REPO_CONFIGS: list[dict] = []  # [{"path": "/path/to/repo", "host": "github", "remote": "owner/repo"}]
MAX_UNKNOWN_LOGS = 100
EXAMPLES_PER_PATTERN = 3
SPIKE_MULTIPLIER = 3.0
DEFAULT_OPENHANDS_URL = "http://localhost:8000"

CONFIG_FILENAME = "config.json"

# Config keys, paired with the type each may have. A wrong type is a hard
# error at import: the alternative is querying a Datadog site that is silently
# an integer, or matching a channel ID that is secretly a list.
#
# repo_configs also accepts a string, because the setup form has no list input
# for structured records - a textarea is what a host can render, and what it
# sends is one string with a repo per line in `path|host|remote` form. Both
# shapes are accepted and normalised to a list of dicts here.
_CONFIG_TYPES: dict[str, tuple[type, ...]] = {
    "dd_query": (str,),
    "dd_site": (str,),
    "slack_channel_id": (str,),
    "repo_configs": (list, str),
    "max_unknown_logs": (int,),
    "examples_per_pattern": (int,),
    "spike_multiplier": (int, float),
    "openhands_url": (str,),
}


def _parse_repo_configs(value: list | str) -> list[dict]:
    """Normalise a list-or-string repo_configs value to a list of dicts.

    A textarea sends one string with a repo per line in `path|host|remote`
    form. Blank lines are dropped: a textarea ends with a newline more often
    than not, and failing the run over it would be a surprising way to learn
    that. A list of dicts (the agent-driven path) is passed through after
    validation.
    """
    if isinstance(value, str):
        items: list[dict] = []
        for line in value.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) != 3:
                raise SystemExit(
                    f"{CONFIG_FILENAME}: repo_configs lines must be "
                    f"'path|host|remote', got {line!r}"
                )
            path, host, remote = (p.strip() for p in parts)
            if not path or not host or not remote:
                raise SystemExit(
                    f"{CONFIG_FILENAME}: repo_configs lines must have "
                    f"non-empty path, host, and remote, got {line!r}"
                )
            items.append({"path": path, "host": host, "remote": remote})
        return items
    if not all(isinstance(item, dict) and item for item in value):
        raise SystemExit(
            f"{CONFIG_FILENAME}: repo_configs must be a list of objects"
        )
    return list(value)


def load_config(directory: Path | None = None) -> dict:
    """Return the rendered config shipped beside this script, or {} if absent.

    Only the keys above are read; anything else in the file is ignored, so a
    host may ship provenance there without this script caring.
    """
    path = (directory or Path(__file__).resolve().parent) / CONFIG_FILENAME
    if not path.is_file():
        return {}

    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise SystemExit(f"{CONFIG_FILENAME} is not valid JSON: {e}") from e
    if not isinstance(raw, dict):
        raise SystemExit(f"{CONFIG_FILENAME} must contain a JSON object")

    config = {}
    for key, expected in _CONFIG_TYPES.items():
        if key not in raw:
            continue
        value = raw[key]
        # bool is an int in Python, so an unguarded int check would accept
        # `"max_unknown_logs": true` and then send one log to the agent.
        if not isinstance(value, expected) or (
            int in expected and isinstance(value, bool)
        ):
            names = " or ".join(t.__name__ for t in expected)
            raise SystemExit(
                f"{CONFIG_FILENAME}: {key} must be {names}, "
                f"got {type(value).__name__}"
            )
        if key == "repo_configs":
            value = _parse_repo_configs(value)
        config[key] = value
    return config


_CONFIG = load_config()
DD_QUERY = _CONFIG.get("dd_query", DD_QUERY)
DD_SITE = _CONFIG.get("dd_site", DD_SITE)
SLACK_CHANNEL_ID = _CONFIG.get("slack_channel_id", SLACK_CHANNEL_ID)
REPO_CONFIGS = _CONFIG.get("repo_configs", REPO_CONFIGS)
MAX_UNKNOWN_LOGS = _CONFIG.get("max_unknown_logs", MAX_UNKNOWN_LOGS)
EXAMPLES_PER_PATTERN = _CONFIG.get("examples_per_pattern", EXAMPLES_PER_PATTERN)
SPIKE_MULTIPLIER = _CONFIG.get("spike_multiplier", SPIKE_MULTIPLIER)
DEFAULT_OPENHANDS_URL = _CONFIG.get("openhands_url", DEFAULT_OPENHANDS_URL)

# ── Internal constants ─────────────────────────────────────────────────────────
INITIAL_LOOKBACK_MINUTES = 15   # lookback window on the very first run
OVERLAP_SECONDS = 60            # extend each query back by this to avoid boundary gaps
MIN_RUNS_FOR_SPIKE = 3          # minimum run_history entries before spike detection activates
MAX_LOG_MESSAGE_CHARS = 500     # truncate individual extracted log messages at this length
MAX_RUN_HISTORY = 20            # keep at most this many entries in run_history per pattern
INVESTIGATION_BUDGET = 10       # total tool calls the agent may spend across all investigation tasks
PATTERN_ARCHIVE_DAYS = 30       # patterns not seen within this many days are moved to the archive
STUCK_CONVERSATION_MINUTES = 45  # conversations still 'running' beyond this are treated as stuck


# ── Stdlib-only helpers ────────────────────────────────────────────────────────

def _env_api_key() -> str:
    return (
        os.environ.get("SESSION_API_KEY")
        or os.environ.get("OH_SESSION_API_KEYS_0")
        or ""
    )


def get_secret(name: str) -> str:
    """Fetch a named secret stored in the agent server."""
    url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    key = _env_api_key()
    req = urllib.request.Request(
        f"{url}/api/settings/secrets/{name}",
        headers={"X-Session-API-Key": key},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode().strip()


def fire_callback(
    status: str = "COMPLETED",
    error: str | None = None,
    conversation_id: str | None = None,
) -> None:
    """Signal run completion to the automation service. MUST be called on every exit path."""
    url = os.environ.get("AUTOMATION_CALLBACK_URL", "")
    if not url:
        return
    body: dict = {"status": status, "run_id": os.environ.get("AUTOMATION_RUN_ID", "")}
    if error:
        body["error"] = error
    if conversation_id:
        body["conversation_id"] = conversation_id
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('AUTOMATION_CALLBACK_API_KEY', '')}",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as exc:
        print(f"Callback error (non-fatal): {exc}")


# ── State persistence (KV store) ──────────────────────────────────────────────
#
# Both the cron script and the spawned investigation conversation read/write
# state via the KV store.  Two auth paths are supported:
#
# 1. KV JWT token (cron script): AUTOMATION_KV_TOKEN + AUTOMATION_API_URL
# 2. User auth (spawned conversation): SESSION_API_KEY + AUTOMATION_API_URL
#    + automation_id query parameter
#
# The cron script has both credentials (KV token + session key); it prefers
# the KV token.  The spawned conversation only has the session key, so it
# uses user auth with the automation_id query param.

_KV_TOKEN = os.environ.get("AUTOMATION_KV_TOKEN", "")
_KV_BASE = os.environ.get("AUTOMATION_API_URL", "").rstrip("/")
_SESSION_KEY = _env_api_key()
_STATE_KEY = "state"
_ARCHIVE_KEY = "archive"


def _automation_id() -> str:
    event_payload = json.loads(os.environ.get("AUTOMATION_EVENT_PAYLOAD", "{}"))
    return event_payload.get("automation_id", "default")


def _kv_available() -> bool:
    """KV is available if we have a base URL and either a KV token or session key."""
    return bool(_KV_BASE and (_KV_TOKEN or _SESSION_KEY))


def _kv_auth_headers() -> dict:
    """Return auth headers for KV requests.

    Prefers KV token (self-contained JWT); falls back to session API key
    (used with automation_id query param for user-authenticated access).
    """
    if _KV_TOKEN:
        return {"Authorization": f"Bearer {_KV_TOKEN}"}
    return {"X-Session-API-Key": _SESSION_KEY}


def _kv_url(key: str) -> str:
    """Build KV API URL.  User-auth path requires automation_id query param."""
    url = f"{_KV_BASE}/v1/kv/{key}"
    if not _KV_TOKEN and _SESSION_KEY:
        url += f"?automation_id={_automation_id()}"
    return url


def _kv_get(key: str):
    req = urllib.request.Request(
        _kv_url(key),
        headers=_kv_auth_headers(),
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())["value"]
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _kv_set(key: str, value) -> None:
    req = urllib.request.Request(
        _kv_url(key),
        data=json.dumps(value).encode(),
        headers={
            **_kv_auth_headers(),
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    with urllib.request.urlopen(req) as r:
        r.read()


def _default_since() -> str:
    return (
        datetime.now(timezone.utc) - timedelta(minutes=INITIAL_LOOKBACK_MINUTES)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_state() -> dict:
    return {
        "version": 1,
        "last_poll_timestamp": _default_since(),
        "active_conversation": None,
        "known_patterns": {},
    }


def load_state() -> dict:
    """Load state from the KV store."""
    if _kv_available():
        data = _kv_get(_STATE_KEY)
        if data is not None:
            print("State loaded from KV store")
            return data
    return _default_state()


def save_state(state: dict) -> None:
    """Write state to the KV store."""
    if _kv_available():
        _kv_set(_STATE_KEY, state)
    else:
        print("Warning: KV store not available — state not persisted")


# ── Pattern archiving ──────────────────────────────────────────────────────────


def _load_archive() -> dict:
    """Load the pattern archive from the KV store."""
    if _kv_available():
        data = _kv_get(_ARCHIVE_KEY)
        if data is not None:
            return data
    return {}


def _save_archive(archive: dict) -> None:
    if _kv_available():
        _kv_set(_ARCHIVE_KEY, archive)


def archive_stale_patterns(state: dict) -> int:
    """Move patterns last seen more than PATTERN_ARCHIVE_DAYS ago to a separate
    archive.  Returns the number of patterns archived.

    The archive is a flat JSON object keyed by pattern UUID.  Each entry gets
    an ``archived_at`` timestamp added so old investigations can be correlated
    with the time the pattern fell silent.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=PATTERN_ARCHIVE_DAYS)

    to_archive: dict = {}
    to_keep: dict = {}
    for pid, pattern in state.get("known_patterns", {}).items():
        last_seen_str = pattern.get("last_seen", "")
        if not last_seen_str:
            to_keep[pid] = pattern
            continue
        try:
            last_seen = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
            if last_seen < cutoff:
                to_archive[pid] = pattern
            else:
                to_keep[pid] = pattern
        except ValueError:
            to_keep[pid] = pattern  # keep if unparseable

    if not to_archive:
        return 0

    archive = _load_archive()

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for pid, pattern in to_archive.items():
        archive[pid] = {**pattern, "archived_at": now_str}

    _save_archive(archive)

    state["known_patterns"] = to_keep
    names = [p.get("name", pid) for pid, p in to_archive.items()]
    print(f"Archived {len(to_archive)} stale pattern(s) → KV archive: {names}")
    return len(to_archive)


# ── Datadog API ────────────────────────────────────────────────────────────────

def query_dd_logs(
    dd_api_key: str,
    dd_app_key: str,
    from_ts: str,
    to_ts: str,
) -> list[dict]:
    """Query Datadog logs and return a list of raw log event dicts (oldest first)."""
    url = f"https://api.{DD_SITE}/api/v2/logs/events/search"
    payload = json.dumps({
        "filter": {"query": DD_QUERY, "from": from_ts, "to": to_ts},
        "sort": "timestamp",
        "page": {"limit": 1000},
    }).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "DD-API-KEY": dd_api_key,
            "DD-APPLICATION-KEY": dd_app_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode()).get("data", [])
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()[:500]
        raise RuntimeError(f"Datadog API error {exc.code}: {body}") from exc


def _extract_message(log_event: dict) -> str:
    """Extract a representative message string from a Datadog log event."""
    attrs = log_event.get("attributes", {})
    msg = (
        attrs.get("message")
        or attrs.get("error", {}).get("message")
        or attrs.get("msg")
        or ""
    )
    stack = attrs.get("error", {}).get("stack", "")
    if stack and len(msg) < 200:
        msg = msg + "\n" + stack[:200]
    return msg[:MAX_LOG_MESSAGE_CHARS]


# ── Pattern matching ───────────────────────────────────────────────────────────

def match_log(message: str, known_patterns: dict) -> str | None:
    """Return the ID of the first pattern that matches, or None."""
    for pattern_id, pattern in known_patterns.items():
        try:
            if re.search(pattern["regex"], message, re.IGNORECASE | re.DOTALL):
                return pattern_id
        except re.error as exc:
            print(f"Warning: invalid regex in pattern '{pattern.get('name')}': {exc}")
    return None


# ── OpenHands conversation helpers ─────────────────────────────────────────────

def _oh_request(
    agent_url: str,
    api_key: str,
    method: str,
    path: str,
    body: dict | None = None,
    extra_headers: dict | None = None,
) -> dict:
    headers = {"X-Session-API-Key": api_key, "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{agent_url.rstrip('/')}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Agent server {exc.code} on {method} {path}: {exc.read().decode()[:300]}"
        ) from exc


def _fetch_settings(agent_url: str, api_key: str, encrypted: bool = False) -> dict:
    try:
        extra = {"X-Expose-Secrets": "encrypted"} if encrypted else None
        return _oh_request(agent_url, api_key, "GET", "/api/settings", extra_headers=extra)
    except Exception as exc:
        print(f"Warning: could not fetch agent settings: {exc}")
        return {}


def _get_agent_dict(agent_url: str, api_key: str) -> tuple[dict, bool]:
    """Return (agent_dict, secrets_encrypted).

    Fetches settings with X-Expose-Secrets: encrypted so the real LLM API key
    (a Fernet token starting with gAAAAA) is included. The caller must pass
    secrets_encrypted=True when creating the conversation so the agent server
    decrypts the key server-side. Without this, /api/settings returns the
    masked placeholder "**********" and the spawned conversation fails with
    LLMAuthenticationError.
    """
    data = _fetch_settings(agent_url, api_key, encrypted=True)
    llm = data.get("agent_settings", {}).get("llm", {})
    agent = {
        "kind": "Agent",
        "llm": llm,
        "tools": [{"name": "terminal"}, {"name": "file_editor"}],
    }
    has_encrypted_key = isinstance(llm.get("api_key"), str) and llm["api_key"].startswith("gAAAAA")
    return agent, has_encrypted_key


def _get_mcp_config(agent_url: str, api_key: str) -> dict | None:
    try:
        data = _fetch_settings(agent_url, api_key)
        mcp = data.get("agent_settings", {}).get("mcp_config")
        if isinstance(mcp, dict) and mcp.get("mcpServers"):
            return mcp
    except Exception as exc:
        print(f"Warning: could not fetch MCP config: {exc}")
    return None


def _build_secrets_payload(agent_url: str, api_key: str) -> dict:
    """Forward all user secrets to the spawned conversation as LookupSecret references."""
    try:
        secrets_list = _oh_request(agent_url, api_key, "GET", "/api/settings/secrets").get("secrets", [])
    except Exception as exc:
        print(f"Warning: could not list secrets: {exc}")
        return {}
    return {
        s["name"]: {
            "kind": "LookupSecret",
            "url": f"/api/settings/secrets/{s['name']}",
            **( {"headers": {"X-Session-API-Key": api_key}} if api_key else {} ),
            **( {"description": s["description"]} if s.get("description") else {} ),
        }
        for s in secrets_list
        if s.get("name")
    }


def create_conversation(
    agent_url: str, api_key: str, initial_message: str, workspace_dir: str
) -> str:
    """Create an OpenHands conversation and return its ID."""
    agent_dict, has_encrypted_key = _get_agent_dict(agent_url, api_key)
    payload: dict = {
        "workspace": {"working_dir": workspace_dir},
        "agent": agent_dict,
        "initial_message": {"content": [{"text": initial_message}]},
    }
    if has_encrypted_key:
        payload["secrets_encrypted"] = True
    if secrets := _build_secrets_payload(agent_url, api_key):
        payload["secrets"] = secrets
    if mcp := _get_mcp_config(agent_url, api_key):
        payload["mcp_config"] = mcp
    return _oh_request(agent_url, api_key, "POST", "/api/conversations", payload)["id"]


def conversation_status(agent_url: str, api_key: str, conv_id: str) -> str:
    return _oh_request(agent_url, api_key, "GET", f"/api/conversations/{conv_id}").get(
        "execution_status", "unknown"
    )


# ── Spike detection ────────────────────────────────────────────────────────────

def _is_spike(current_count: int, history_before_this_run: list[int]) -> bool:
    """Return True if current_count significantly exceeds the recent baseline.

    Requires MIN_RUNS_FOR_SPIKE history entries before activating.
    When all recent counts are zero, any non-zero value is a spike.
    """
    if not history_before_this_run:
        return False
    if len(history_before_this_run) < MIN_RUNS_FOR_SPIKE:
        return False
    recent = history_before_this_run[-MIN_RUNS_FOR_SPIKE:]
    baseline = sum(recent) / len(recent)
    if baseline == 0:
        return current_count > 0
    return current_count > baseline * SPIKE_MULTIPLIER


# ── Investigation prompt ───────────────────────────────────────────────────────

def _build_prompt(
    automation_id: str,
    from_ts: str,
    to_ts: str,
    unknown_samples: list[str],
    total_unknown: int,
    spiking: list[tuple[str, dict, int]],
) -> str:
    kv_base = _KV_BASE
    # The spawned conversation uses user auth (SESSION_API_KEY + automation_id)
    lines = [
        "# Datadog Error Monitor - Investigation Request",
        "",
        "## Context",
        f"- **Datadog query:** `{DD_QUERY}`",
        f"- **Time window:** {from_ts} → {to_ts}",
        f"- **KV API base:** `{kv_base}`",
        f"- **Automation ID:** `{automation_id}`",
        "",
        "## State Access (KV Store)",
        "",
        "Read and write state via the KV store API.  Use the `X-Session-API-Key`",
        "header with the `$SESSION_API_KEY` environment variable, and include",
        f"`automation_id={automation_id}` as a query parameter.",
        "",
        "**Read state:**",
        "```bash",
        f'curl -s "{kv_base}/v1/kv/state?automation_id={automation_id}"'
        ' -H "X-Session-API-Key: $SESSION_API_KEY"'
        " | python3 -c \"import json,sys; print(json.dumps(json.load(sys.stdin)['value'], indent=2))\"",
        "```",
        "",
        "**Write state** (after making changes, write the entire state back):",
        "```bash",
        f'curl -s -X PUT "{kv_base}/v1/kv/state?automation_id={automation_id}"'
        ' -H "X-Session-API-Key: $SESSION_API_KEY"'
        ' -H "Content-Type: application/json"'
        " -d '$(cat /tmp/state.json | python3 -c \"import json,sys; print(json.dumps(json.load(sys.stdin)))\")'",
        "```",
        "",
        "> **Important:** Read the state first, modify it locally, then write the",
        "> complete state back.  Never write a partial state — always include all",
        "> top-level fields (`version`, `last_poll_timestamp`, `active_conversation`,",
        "> `known_patterns`).",
        "",
        "## Investigation Budget",
        "",
        f"You have **{INVESTIGATION_BUDGET} tool calls** (terminal commands, file reads,",
        "Datadog API queries combined) to spend across **all tasks**.",
        "",
        "- Simple cases (clear stack trace → matching code location): 2-3 calls",
        "- Ambiguous cases: spend at most 3-4 calls, then **declare inconclusive**",
        "- Stop when the budget is exhausted, even if patterns remain uninvestigated",
        "",
        "If you cannot identify the root cause within your allocated calls, set the",
        "pattern's `description` to `\"Inconclusive - <brief notes on what you tried>\"`",
        "and move on. An inconclusive finding is more useful than no finding.",
        "",
        "## Tasks",
        "",
        "Work through the following tasks in order. The state is a JSON document",
        "stored in the KV store; read it via the API above, make your changes,",
        "then write it back. Preserve all existing top-level fields.",
        "",
        "---",
        "",
        "### Task 1 - Categorize unknown logs",
    ]

    if total_unknown == 0:
        lines += ["", "No uncategorized logs this run. Proceed to Task 2."]
    else:
        truncation_note = (
            f"  Only the first {MAX_UNKNOWN_LOGS} of {total_unknown} are shown."
            if total_unknown > MAX_UNKNOWN_LOGS else ""
        )
        lines += [
            "",
            f"**{total_unknown} log event(s)** did not match any known pattern.{truncation_note}",
            "",
            "**Before creating any new pattern**, read `known_patterns` from the state",
            "via the KV API and check for overlap with the samples below:",
            "",
            "- Test each existing pattern's `regex` against the new samples:",
            "  `re.search(pattern['regex'], sample, re.IGNORECASE | re.DOTALL)`",
            "- If an existing regex already covers a sample, do **not** create a new pattern;",
            "  note the overlap in the Slack summary (Task 4) instead.",
            "- If root causes appear similar but error messages are distinct, create a new",
            "  pattern and cross-reference both `description` fields.",
            "",
            "For each genuinely new error class, add an entry to `known_patterns` using a",
            "new UUID key (`import uuid; str(uuid.uuid4())`).",
            "",
            "Each new pattern requires these fields:",
            "```json",
            "{",
            '  "name": "Concise human-readable label (e.g. Redis connection timeout)",',
            '  "regex": "Python regex - re.IGNORECASE | re.DOTALL - matching this error class",',
            '  "first_seen": "<earliest example timestamp, or current UTC if unavailable>",',
            '  "last_seen": "<current UTC ISO 8601 timestamp>",',
            '  "total_events": <count of matching samples from this window>,',
            '  "description": "Brief notes: likely cause, related service, stack trace clues.",',
            '  "run_history": [<count of matching logs from this window>],',
            '  "examples": [{"timestamp": "...", "message": "..."}]',
            "}",
            "```",
            "",
            "**Regex quality rules:**",
            "- Match the error *class*, not a single occurrence",
            "- Avoid embedding timestamps, request IDs, memory addresses, or UUIDs",
            "- Use `.*` to skip variable parts between fixed anchor strings",
            "- Prefer fewer, broader patterns over many narrow ones",
            "",
            "<unknown_logs>",
        ]
        for i, msg in enumerate(unknown_samples, 1):
            lines.append(f"[{i}] {msg}")
        lines.append("</unknown_logs>")

    # ── Task 2: Deployment correlation ────────────────────────────────────────
    lines += [
        "",
        "---",
        "",
        "### Task 2 - Correlate errors with deployments",
        "",
        "For every newly created pattern (Task 1) and every spiking pattern (listed in",
        "Task 3), compare `first_seen` against recent deployments to identify likely cause.",
        "",
    ]

    if REPO_CONFIGS:
        lines += [
            "Fetch tags and list recent ones with dates for each configured repository:",
            "```bash",
        ]
        for cfg in REPO_CONFIGS:
            repo_label = cfg.get("remote", cfg["path"])
            lines += [
                f"# {repo_label}",
                f"git -C {cfg['path']} fetch --tags --quiet origin 2>/dev/null",
                f"git -C {cfg['path']} log --tags --simplify-by-decoration"
                " --pretty=format:'%D  %ai' --since='60 days ago' | grep 'tag:'",
            ]
        lines += [
            "```",
            "",
            "> **Note:** This step assumes git tags mark production deployments.",
            "> If your team deploys differently (branch tip, CI artefact, Datadog",
            "> deployment markers), confirm the right signal with the repo owner and",
            "> adjust this step accordingly.",
            "",
            "If a pattern's `first_seen` falls within a few hours after a tag, update its",
            "`description` to note the correlation, e.g.:",
            '`"Errors first seen ~2 h after deploy v2.3.1 (2024-03-12T14:05Z). Likely introduced then."`',
        ]
    else:
        lines += ["*(No repositories configured - skip deployment correlation.)*"]

    # ── Task 3: Investigate spiking patterns ──────────────────────────────────
    lines += [
        "",
        "---",
        "",
        "### Task 3 - Investigate spiking patterns",
        "",
    ]

    if not spiking:
        lines += ["No patterns have spiked this run. Proceed to Task 4."]
    else:
        lines += [
            "The following patterns have counts significantly above their recent baseline.",
            "",
            "For **each** spiking pattern, work through these steps within your budget:",
            "",
            "1. `git -C <repo> pull --ff-only origin` to ensure you are on the latest code",
            "2. Check the stack traces in the examples for a specific code location",
            "3. If a location is identified: read that file and check recent changes",
            "   (`git -C <repo> log -8 --oneline -- <file>`)",
            "4. If the cause is still unclear, run **one** follow-up Datadog query:",
            "   ```bash",
            f'   curl -s -X POST "https://api.{DD_SITE}/api/v2/logs/events/search" \\',
            '     -H "DD-API-KEY: $DD_API_KEY" -H "DD-APPLICATION-KEY: $DD_APP_KEY" \\',
            '     -H "Content-Type: application/json" \\',
            "     -d '{\"filter\":{\"query\":\"<refine query>\","
            "\"from\":\"now-1h\",\"to\":\"now\"},\"page\":{\"limit\":10}}'",
            "   ```",
            "5. If still unclear after step 4: **declare inconclusive** and move on",
            "",
            "After investigating each pattern, **overwrite its `description`** in the",
            "state via the KV API with your current findings.",
            "",
        ]

        for pid, pattern, count in spiking:
            history = pattern.get("run_history", [])
            recent = history[-MIN_RUNS_FOR_SPIKE:] if len(history) >= MIN_RUNS_FOR_SPIKE else history
            baseline_str = f"{sum(recent) / len(recent):.1f}" if recent else "N/A"
            lines += [
                f"#### `{pattern['name']}`",
                f"- Count this run: **{count}**  |  Baseline: {baseline_str}"
                f"  (last {len(recent)} runs: `{recent}`)",
                f"- First seen: {pattern.get('first_seen', 'unknown')}",
                f"- Last seen:  {pattern.get('last_seen', 'unknown')}",
                f"- Total events: {pattern.get('total_events', 'unknown')}",
                f"- Regex: `{pattern.get('regex', 'N/A')}`",
                f"- Description: {pattern.get('description', '(none yet)')}",
                "",
            ]
            examples = pattern.get("examples", [])[:EXAMPLES_PER_PATTERN]
            if examples:
                lines.append("Recent examples:")
                for ex in examples:
                    lines.append(f"  - `{ex.get('message', '')[:300]}`")
            lines.append("")

        lines += [
            "**If you identify a code-level fix:**",
            "- Create a focused PR using the appropriate git host (GitHub / GitLab / Bitbucket)",
            "- Only open a PR when you are **highly confident** the fix is correct",
            "- Include a description referencing the error pattern name and `first_seen`",
            "",
            "**Otherwise** (infrastructure / config / data issue, or inconclusive):",
            "- Do NOT create a PR",
            "- Capture your findings in the pattern's `description` for the Slack summary",
        ]

    if REPO_CONFIGS:
        lines += [
            "",
            "**Repositories (already cloned on this machine):**",
        ]
        for cfg in REPO_CONFIGS:
            lines.append(
                f"- `{cfg['path']}` - {cfg.get('host', 'git')} · `{cfg.get('remote', '')}`"
            )

    # ── Task 4: Slack summary ──────────────────────────────────────────────────
    lines += [
        "",
        "---",
        "",
        "### Task 4 - Post Slack summary",
        "",
        f"Post to Slack channel `{SLACK_CHANNEL_ID}` using the `SLACK_BOT_TOKEN` secret.",
        "",
        "**Only post if there were actual findings** (new patterns, spikes, or deployment",
        "correlations). Skip this task entirely if nothing triggered.",
        "",
        "Include:",
        "- New error patterns: name, event count, and brief description",
        "- Spiking patterns: diagnosis, deployment correlation if found, PR link if opened",
        "- Inconclusive patterns: name + what was tried - flag for manual investigation",
        "",
        "Keep it concise - bullet points preferred. Example:",
        "",
        "```",
        f"🔴 *Datadog Error Monitor - {from_ts}*",
        "",
        "New patterns (2):",
        "  • Redis timeout in CacheService - 12 events, likely from deploy v2.3.1",
        "  • JWT validation failure - 4 events - inconclusive, needs manual review",
        "Spike:",
        "  • NullPointerException in PaymentService - 47 events (baseline ~3)",
        "    → null check missing after optional-field refactor → PR #123 opened",
        "```",
        "",
        "```bash",
        "curl -s -X POST https://slack.com/api/chat.postMessage \\",
        '  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \\',
        '  -H "Content-Type: application/json" \\',
        f'  -d \'{{\"channel\": \"{SLACK_CHANNEL_ID}\", \"text\": \"YOUR SUMMARY\"}}\' \\',
        "  | python3 -c \"import json,sys; d=json.load(sys.stdin);"
        " print('OK' if d.get('ok') else d.get('error'))\"",
        "```",
    ]

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> str | None:
    autom_id = _automation_id()
    print(f"Automation ID: {autom_id}")
    state = load_state()

    # ── Archive patterns not seen recently ───────────────────────────────────
    archive_stale_patterns(state)

    # ── Resolve Datadog secrets ──────────────────────────────────────────────
    try:
        dd_api_key = get_secret("DD_API_KEY")
        dd_app_key = get_secret("DD_APP_KEY")
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch Datadog secrets: {exc}") from exc

    agent_url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    api_key = _env_api_key()

    # ── Define query window with overlap ─────────────────────────────────────
    now = datetime.now(timezone.utc)
    to_ts = (now - timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    from_dt = (
        datetime.fromisoformat(state["last_poll_timestamp"].replace("Z", "+00:00"))
        - timedelta(seconds=OVERLAP_SECONDS)
    )
    from_ts = from_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Querying: {DD_QUERY!r}  [{from_ts} → {to_ts}]")

    # ── Query Datadog ────────────────────────────────────────────────────────
    logs = query_dd_logs(dd_api_key, dd_app_key, from_ts, to_ts)
    print(f"Retrieved {len(logs)} log events")

    # ── Match logs against known patterns ────────────────────────────────────
    known_patterns = state.setdefault("known_patterns", {})
    pattern_counts: dict[str, int] = {}
    unknown_samples: list[str] = []
    total_unknown = 0

    for log_event in logs:
        msg = _extract_message(log_event)
        pid = match_log(msg, known_patterns)
        if pid:
            pattern_counts[pid] = pattern_counts.get(pid, 0) + 1
            pattern = known_patterns[pid]
            pattern["last_seen"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            pattern["total_events"] = pattern.get("total_events", 0) + 1
            pattern.setdefault("examples", [])
            new_example = {
                "timestamp": log_event.get("attributes", {}).get("timestamp", ""),
                "message": msg,
            }
            pattern["examples"] = ([new_example] + pattern["examples"])[:EXAMPLES_PER_PATTERN]
        else:
            total_unknown += 1
            if len(unknown_samples) < MAX_UNKNOWN_LOGS:
                unknown_samples.append(msg)

    # ── Update run_history and detect spikes ─────────────────────────────────
    # History is updated AFTER spike detection so we compare against prior runs.
    spiking: list[tuple[str, dict, int]] = []
    for pid, pattern in known_patterns.items():
        history = pattern.setdefault("run_history", [])
        count = pattern_counts.get(pid, 0)
        if _is_spike(count, history):
            spiking.append((pid, pattern, count))
            print(f"Spike: '{pattern['name']}' - {count} events (history: {history[-MIN_RUNS_FOR_SPIKE:]})")
        history.append(count)
        pattern["run_history"] = history[-MAX_RUN_HISTORY:]

    if pattern_counts:
        print("Pattern counts:", {known_patterns[pid]["name"]: c for pid, c in pattern_counts.items()})
    print(f"Unknown: {total_unknown} total, {len(unknown_samples)} sampled")

    # ── Check active conversation ─────────────────────────────────────────────
    active = state.get("active_conversation")
    conversation_id: str | None = None

    if active and agent_url:
        conv_id = active["id"]
        try:
            status = conversation_status(agent_url, api_key, conv_id)
        except Exception as exc:
            print(f"Warning: could not check conversation {conv_id}: {exc}")
            status = "unknown"

        print(f"Active conversation {conv_id} → status={status}")

        # Treat conversations stuck in a non-terminal state beyond the timeout as stuck.
        if status not in ("idle", "finished", "error", "stuck"):
            started_at_str = active.get("started_at", "")
            if started_at_str:
                try:
                    started_dt = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
                    elapsed_min = (now - started_dt).total_seconds() / 60
                    if elapsed_min > STUCK_CONVERSATION_MINUTES:
                        print(
                            f"Conversation {conv_id} has been running for {elapsed_min:.0f} min "
                            f"(> {STUCK_CONVERSATION_MINUTES} min limit) - treating as stuck"
                        )
                        status = "stuck"
                except ValueError:
                    pass

        if status in ("idle", "finished", "error", "stuck"):
            print("Conversation finished - clearing active slot")
            state["active_conversation"] = None
            active = None
        else:
            # Investigation still running - save updated pattern data and exit
            state["last_poll_timestamp"] = to_ts
            save_state(state)
            print("Investigation in progress - skipping trigger evaluation")
            return conv_id

    # ── Evaluate triggers ────────────────────────────────────────────────────
    should_trigger = total_unknown > 0 or bool(spiking)

    if should_trigger and agent_url:
        # Use the first configured repo as workspace so the agent has code access
        if REPO_CONFIGS:
            workspace_dir = REPO_CONFIGS[0]["path"]
        else:
            workspace_base = os.environ.get("WORKSPACE_BASE", "")
            root = (
                str(Path(workspace_base).resolve().parent.parent)
                if workspace_base
                else os.path.expanduser("~/.openhands/workspaces")
            )
            workspace_dir = os.path.join(root, "dd-monitor-investigations")
            os.makedirs(workspace_dir, exist_ok=True)

        prompt = _build_prompt(
            automation_id=autom_id,
            from_ts=from_ts,
            to_ts=to_ts,
            unknown_samples=unknown_samples,
            total_unknown=total_unknown,
            spiking=spiking,
        )

        trigger_parts = []
        if total_unknown > 0:
            trigger_parts.append(f"{total_unknown} unknown logs")
        if spiking:
            trigger_parts.append("spikes in: " + ", ".join(p["name"] for _, p, _ in spiking))
        trigger_summary = "; ".join(trigger_parts)

        try:
            conversation_id = create_conversation(agent_url, api_key, prompt, workspace_dir)
            print(f"Started investigation conversation: {conversation_id}")
            state["active_conversation"] = {
                "id": conversation_id,
                "started_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "trigger_summary": trigger_summary,
                "status": "running",
            }
        except Exception as exc:
            print(f"Failed to create conversation (will retry next run): {exc}")
    elif should_trigger:
        print("Triggers detected but AGENT_SERVER_URL not set - cannot create conversation")
    else:
        print("No triggers - no investigation needed")

    # ── Save state and return ─────────────────────────────────────────────────
    state["last_poll_timestamp"] = to_ts
    save_state(state)
    print(f"State saved. Next poll window starts from: {to_ts}")
    return conversation_id


if __name__ == "__main__":
    try:
        conv_id = main()
        fire_callback("COMPLETED", conversation_id=conv_id)
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        fire_callback("FAILED", error=str(exc))
        sys.exit(1)
