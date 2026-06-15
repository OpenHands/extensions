"""
Datadog Error Monitor — OpenHands Automation Script

Polls Datadog for log errors on a cron schedule. On each run:
  1. Queries Datadog logs using a pre-configured filter query.
  2. Matches each log against known error patterns (regex).
  3. Tracks hit counts per pattern across runs.
  4. If unknown/uncategorized logs are detected OR a pattern count spikes
     significantly, creates a single OpenHands investigation conversation.
  5. The conversation agent categorizes unknown logs, investigates root causes,
     optionally creates PRs, and posts a summary to Slack.

Configuration constants are embedded at automation-creation time by the skill.
See SKILL.md for the full setup workflow.

Required secrets (set in OpenHands Settings → Secrets):
  DD_API_KEY      — Datadog API key
  DD_APP_KEY      — Datadog Application key (required for log search)
  SLACK_BOT_TOKEN — Slack bot token (chat:write scope)

Optional secret:
  OPENHANDS_URL — base URL for conversation links (default: http://localhost:8000)
"""

import json
import os
import re
import sys
from pathlib import Path
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

# ── Embedded configuration (filled in by the skill at creation time) ──────────
DD_QUERY = "service:(deploy OR runtime-api) status:error"
DD_SITE = "datadoghq.com"
SLACK_CHANNEL_ID = "C0123456789"
REPO_CONFIGS: list[dict] = []  # [{"path": "/path/to/repo", "host": "github", "remote": "owner/repo"}]
MAX_UNKNOWN_LOGS = 100
EXAMPLES_PER_PATTERN = 3
SPIKE_MULTIPLIER = 3.0
DEFAULT_OPENHANDS_URL = "http://localhost:8000"

# ── Internal constants ─────────────────────────────────────────────────────────
INITIAL_LOOKBACK_MINUTES = 15   # lookback window on the very first run
OVERLAP_SECONDS = 60            # extend each query back by this to avoid boundary gaps
MIN_RUNS_FOR_SPIKE = 3          # minimum run_history entries before spike detection activates
MAX_LOG_MESSAGE_CHARS = 500     # truncate individual extracted log messages at this length
MAX_RUN_HISTORY = 20            # keep at most this many entries in run_history per pattern
INVESTIGATION_BUDGET = 10       # total tool calls the agent may spend across all investigation tasks
PATTERN_ARCHIVE_DAYS = 30       # patterns not seen within this many days are moved to the archive


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


# ── State management ───────────────────────────────────────────────────────────

def _state_file_path() -> str:
    """Derive a persistent storage path stable across cron runs.

    WORKSPACE_BASE = {root}/automation-runs/{run_id}
    State lives at   {root}/automation-state/dd_monitor_{automation_id}.json
    """
    workspace_base = os.environ.get("WORKSPACE_BASE", "")
    event_payload = json.loads(os.environ.get("AUTOMATION_EVENT_PAYLOAD", "{}"))
    automation_id = event_payload.get("automation_id", "default")

    if workspace_base:
        root = Path(workspace_base).resolve().parent.parent
    else:
        root = Path.home() / ".openhands" / "workspaces"

    state_dir = root / "automation-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return str(state_dir / f"dd_monitor_{automation_id}.json")


def _default_since() -> str:
    return (
        datetime.now(timezone.utc) - timedelta(minutes=INITIAL_LOOKBACK_MINUTES)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: state file unreadable ({exc}); starting fresh")
    return {
        "version": 1,
        "last_poll_timestamp": _default_since(),
        "active_conversation": None,
        "known_patterns": {},
    }


def save_state(path: str, state: dict) -> None:
    """Atomic write — write to .tmp then rename to avoid partial reads."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)


# ── Pattern archiving ──────────────────────────────────────────────────────────

def _archive_file_path(state_path: str) -> str:
    p = Path(state_path)
    return str(p.parent / (p.stem + "_archive" + p.suffix))


def archive_stale_patterns(state: dict, state_path: str) -> int:
    """Move patterns last seen more than PATTERN_ARCHIVE_DAYS ago to a separate
    archive file.  Returns the number of patterns archived.

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

    archive_path = _archive_file_path(state_path)
    try:
        with open(archive_path) as f:
            archive: dict = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        archive = {}

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for pid, pattern in to_archive.items():
        archive[pid] = {**pattern, "archived_at": now_str}

    tmp = archive_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(archive, f, indent=2)
    os.replace(tmp, archive_path)

    state["known_patterns"] = to_keep
    names = [p.get("name", pid) for pid, p in to_archive.items()]
    print(f"Archived {len(to_archive)} stale pattern(s) → {archive_path}: {names}")
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
    agent_url: str, api_key: str, method: str, path: str, body: dict | None = None
) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{agent_url.rstrip('/')}{path}",
        data=data,
        headers={"X-Session-API-Key": api_key, "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Agent server {exc.code} on {method} {path}: {exc.read().decode()[:300]}"
        ) from exc


def _fetch_settings(agent_url: str, api_key: str) -> dict:
    """Fetch the full user settings from the agent server.

    Uses X-Expose-Secrets: plaintext so the LLM api_key is a real string
    rather than a masked placeholder.
    """
    url = f"{agent_url.rstrip('/')}/api/settings"
    headers = {
        "X-Session-API-Key": api_key,
        "X-Expose-Secrets": "plaintext",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        print(f"Warning: could not fetch agent settings: {exc.code}")
        return {}
    except Exception as exc:
        print(f"Warning: could not fetch agent settings: {exc}")
        return {}


def _get_agent_dict(agent_url: str, api_key: str) -> dict:
    data = _fetch_settings(agent_url, api_key)
    llm = data.get("agent_settings", {}).get("llm", {})
    return {
        "kind": "Agent",
        "llm": llm,
        "tools": [{"name": "terminal"}, {"name": "file_editor"}],
    }


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
    payload: dict = {
        "workspace": {"working_dir": workspace_dir},
        "agent": _get_agent_dict(agent_url, api_key),
        "initial_message": {"content": [{"text": initial_message}]},
    }
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
    state_file_path: str,
    from_ts: str,
    to_ts: str,
    unknown_samples: list[str],
    total_unknown: int,
    spiking: list[tuple[str, dict, int]],
) -> str:
    lines = [
        "# Datadog Error Monitor — Investigation Request",
        "",
        "## Context",
        f"- **Datadog query:** `{DD_QUERY}`",
        f"- **Time window:** {from_ts} → {to_ts}",
        f"- **State file:** `{state_file_path}`",
        f"- **Archive file:** `{_archive_file_path(state_file_path)}`",
        "",
        "## Investigation Budget",
        "",
        f"You have **{INVESTIGATION_BUDGET} tool calls** (terminal commands, file reads,",
        "Datadog API queries combined) to spend across **all tasks**.",
        "",
        "- Simple cases (clear stack trace → matching code location): 2–3 calls",
        "- Ambiguous cases: spend at most 3–4 calls, then **declare inconclusive**",
        "- Stop when the budget is exhausted, even if patterns remain uninvestigated",
        "",
        "If you cannot identify the root cause within your allocated calls, set the",
        "pattern's `description` to `\"Inconclusive — <brief notes on what you tried>\"`",
        "and move on. An inconclusive finding is more useful than no finding.",
        "",
        "## Tasks",
        "",
        "Work through the following tasks in order. The state file is a JSON document;",
        "read it, make your changes, then write it back **atomically** (write to a `.tmp`",
        "file, then `os.replace`). Preserve all existing top-level fields.",
        "",
        "---",
        "",
        "### Task 1 — Categorize unknown logs",
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
            "**Before creating any new pattern**, read `known_patterns` from the state file",
            "and check for overlap with the samples below:",
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
            '  "regex": "Python regex — re.IGNORECASE | re.DOTALL — matching this error class",',
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
        "### Task 2 — Correlate errors with deployments",
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
        lines += ["*(No repositories configured — skip deployment correlation.)*"]

    # ── Task 3: Investigate spiking patterns ──────────────────────────────────
    lines += [
        "",
        "---",
        "",
        "### Task 3 — Investigate spiking patterns",
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
            "After investigating each pattern, **overwrite its `description`** in the state",
            "file with your current findings.",
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
                f"- `{cfg['path']}` — {cfg.get('host', 'git')} · `{cfg.get('remote', '')}`"
            )

    # ── Task 4: Slack summary ──────────────────────────────────────────────────
    lines += [
        "",
        "---",
        "",
        "### Task 4 — Post Slack summary",
        "",
        f"Post to Slack channel `{SLACK_CHANNEL_ID}` using the `SLACK_BOT_TOKEN` secret.",
        "",
        "**Only post if there were actual findings** (new patterns, spikes, or deployment",
        "correlations). Skip this task entirely if nothing triggered.",
        "",
        "Include:",
        "- New error patterns: name, event count, and brief description",
        "- Spiking patterns: diagnosis, deployment correlation if found, PR link if opened",
        "- Inconclusive patterns: name + what was tried — flag for manual investigation",
        "",
        "Keep it concise — bullet points preferred. Example:",
        "",
        "```",
        f"🔴 *Datadog Error Monitor — {from_ts}*",
        "",
        "New patterns (2):",
        "  • Redis timeout in CacheService — 12 events, likely from deploy v2.3.1",
        "  • JWT validation failure — 4 events — inconclusive, needs manual review",
        "Spike:",
        "  • NullPointerException in PaymentService — 47 events (baseline ~3)",
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
    state_path = _state_file_path()
    print(f"State file: {state_path}")
    state = load_state(state_path)

    # ── Archive patterns not seen recently ───────────────────────────────────
    archive_stale_patterns(state, state_path)

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
            print(f"Spike: '{pattern['name']}' — {count} events (history: {history[-MIN_RUNS_FOR_SPIKE:]})")
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

        if status in ("idle", "finished", "error", "stuck"):
            print("Conversation finished — clearing active slot")
            state["active_conversation"] = None
            active = None
        else:
            # Investigation still running — save updated pattern data and exit
            state["last_poll_timestamp"] = to_ts
            save_state(state_path, state)
            print("Investigation in progress — skipping trigger evaluation")
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
            state_file_path=state_path,
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
        print("Triggers detected but AGENT_SERVER_URL not set — cannot create conversation")
    else:
        print("No triggers — no investigation needed")

    # ── Save state and return ─────────────────────────────────────────────────
    state["last_poll_timestamp"] = to_ts
    save_state(state_path, state)
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
