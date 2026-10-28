"""Vibe Manager automation — runs every minute per workspace.

Deterministic phase (pure stdlib, no LLM):
  1. Pull the board snapshot from the vibe API.
  2. Enrich with live conversation execution statuses (agent server) and
     PR states (GitHub API).
  3. Apply mechanical transitions: PR open -> needs_input, PR merged -> finished.
  4. Fingerprint the enriched state; compare with the KV store; compute
     actionable "signals" (new entries, dispatchable tickets, finished workers,
     manually resumed agents). Per-conversation execution statuses are also
     persisted in the state so manual interventions (e.g. the user messaging a
     needs_input worker directly) are tracked between runs.

Only when the fingerprint changed AND something is actionable does it kick off
the Manager agent conversation, which does the smart work: dispatching worker
conversations (always in git worktrees, one per ticket), serializing
conflicting tickets, updating card statuses, and maintaining AGENTS.md.
The manager runs asynchronously; subsequent cycles skip while it is running.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import vibestore  # noqa: E402 - must follow the sys.path shim above

CONFIG = json.loads((Path(__file__).parent / "config.json").read_text())
WORKSPACE_ID = CONFIG["workspace_id"]
WORKSPACE_PATH = CONFIG["workspace_path"]
WORKSPACE_NAME = CONFIG["workspace_name"]
CANVAS_BASE = CONFIG["canvas_base"].rstrip("/")

if CONFIG.get("store_dir"):
    os.environ.setdefault("VIBE_STORE_DIR", CONFIG["store_dir"])

# Installed outside the per-run tarball dir so the manager conversation can
# still call it after this run is cleaned up.
VIBECTL = vibestore.install_cli(WORKSPACE_ID, WORKSPACE_PATH)

AGENT_SERVER = os.environ.get("AGENT_SERVER_URL", CONFIG["agent_server"]).rstrip("/")
SESSION_KEY = os.environ.get("SESSION_API_KEY") or os.environ.get("OH_SESSION_API_KEYS_0", "")

_KV_TOKEN = os.environ.get("AUTOMATION_KV_TOKEN", "")
_KV_BASE = os.environ.get("AUTOMATION_API_URL", "").rstrip("/")
_STATE_KEY = "state"

MANAGER_STALE_SECONDS = 45 * 60  # give up on a manager conversation after this
RETRY_INTERVAL_SECONDS = 10 * 60  # re-kick manager if signals persist without board change
MAX_RETRY_ATTEMPTS = 3  # cap crash-recovery retries per unchanged board state
TERMINAL_CONV_STATUSES = {"finished", "idle", "error", "stuck", "deleted", "paused"}
MANAGER_ACTIVE_STATUS = "running"  # the only status that means "still working"
MANAGER_FAILED_STATUSES = {"error", "stuck"}  # died without finishing its job


# ------------------------------------------------------------------- http utils

def _request(url: str, method: str = "GET", data: dict | None = None,
             headers: dict | None = None, timeout: int = 30):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def agent(path: str, method: str = "GET", data: dict | None = None, timeout: int = 60):
    return _request(
        f"{AGENT_SERVER}{path}", method, data,
        headers={"X-Session-API-Key": SESSION_KEY}, timeout=timeout,
    )


def fire_callback(status: str = "COMPLETED", error: str | None = None) -> None:
    url = os.environ.get("AUTOMATION_CALLBACK_URL", "")
    if not url:
        return
    body = {"status": status, "run_id": os.environ.get("AUTOMATION_RUN_ID", "")}
    if error:
        body["error"] = error
    try:
        _request(url, "POST", body, headers={
            "Authorization": f"Bearer {os.environ.get('AUTOMATION_CALLBACK_API_KEY', '')}",
        })
    except Exception as exc:  # noqa: BLE001
        print(f"callback error (non-fatal): {exc}")


# --------------------------------------------------------------------- kv store

def kv_available() -> bool:
    return bool(_KV_TOKEN and _KV_BASE)


def _kv(path: str, method: str = "GET", data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        f"{_KV_BASE}/v1/kv/{path}", data=body, method=method,
        headers={"Authorization": f"Bearer {_KV_TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def _state_file() -> Path:
    d = Path.home() / ".openhands" / "vibe-manager-state"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{WORKSPACE_ID}.json"


def load_state() -> dict:
    if kv_available():
        try:
            return _kv(_STATE_KEY).get("value") or {}
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return {}
            raise
    f = _state_file()
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:  # noqa: BLE001
            return {}
    return {}


def save_state(state: dict) -> None:
    if kv_available():
        _kv(_STATE_KEY, "PUT", state)
    else:
        _state_file().write_text(json.dumps(state, indent=2))


# ------------------------------------------------------------- status gathering

def get_secret(name: str) -> str:
    try:
        req = urllib.request.Request(
            f"{AGENT_SERVER}/api/settings/secrets/{name}",
            headers={"X-Session-API-Key": SESSION_KEY},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode().strip().strip('"')
    except Exception:  # noqa: BLE001
        return ""


def conversation_spend(conv: dict) -> float:
    """Total USD the conversation has spent, across every LLM it used."""
    usage = (conv.get("stats") or {}).get("usage_to_metrics") or {}
    return sum(float((m or {}).get("accumulated_cost") or 0.0) for m in usage.values())


def conversation_info(conv_id: str) -> dict:
    """Return {status, spend, tags, created_at_ts} for a conversation."""
    try:
        d = agent(f"/api/conversations/{conv_id}?include_skills=false")
        created = d.get("created_at") or ""
        try:
            created_ts = datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
        except ValueError:
            created_ts = 0.0
        return {
            "status": d.get("execution_status", "unknown"),
            "spend": conversation_spend(d),
            "tags": d.get("tags") or {},
            "created_at_ts": created_ts,
        }
    except urllib.error.HTTPError as exc:
        status = "deleted" if exc.code == 404 else f"error_{exc.code}"
        return {"status": status, "spend": 0.0, "tags": {}, "created_at_ts": 0.0}
    except Exception:  # noqa: BLE001
        return {"status": "unreachable", "spend": 0.0, "tags": {}, "created_at_ts": 0.0}


def conversation_status(conv_id: str) -> str:
    return conversation_info(conv_id)["status"]


def manager_conversation_state(state: dict, ws: dict) -> dict:
    """State of the manager conversation this workspace started last.

    Returns {id, status, started_at, active, failed}. Only `running` counts as
    active: a manager that ended in error/stuck (or paused/idle/finished) is
    done and must never suppress the next kickoff — otherwise a crashed
    manager freezes the board until someone notices.

    Checks the KV-tracked id first, then the id recorded on the workspace row
    (survives KV state loss). Tags verify it really is this workspace's manager.
    """
    candidates = []
    if state.get("manager_conversation_id"):
        candidates.append(state["manager_conversation_id"])
    row_conv = ws.get("manager_conversation_id")
    if row_conv and row_conv not in candidates:
        candidates.append(row_conv)
    for conv_id in candidates:
        info = conversation_info(conv_id)
        # The KV-tracked id is trusted; a row-recorded id must carry our tags.
        if conv_id != state.get("manager_conversation_id") and not (
            info["tags"].get("viberole") == "manager"
            and info["tags"].get("workspace") == WORKSPACE_PATH
        ):
            continue
        return {
            "id": conv_id,
            "status": info["status"],
            "started_at": state.get("manager_started_at") or info["created_at_ts"],
            "active": info["status"] == MANAGER_ACTIVE_STATUS,
            "failed": info["status"] in MANAGER_FAILED_STATUSES,
        }
    return {"id": None, "status": None, "started_at": 0.0, "active": False, "failed": False}


_PR_RE = re.compile(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)")


def pr_state(pr_url: str, token: str) -> str:
    """Return 'open' | 'merged' | 'closed' | 'unknown'."""
    m = _PR_RE.search(pr_url or "")
    if not m:
        return "unknown"
    owner, repo, num = m.groups()
    try:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "vibe-manager"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        d = _request(f"https://api.github.com/repos/{owner}/{repo}/pulls/{num}", headers=headers)
        if d.get("merged") or d.get("merged_at"):
            return "merged"
        return d.get("state", "unknown")
    except Exception:  # noqa: BLE001
        return "unknown"


def snapshot() -> dict:
    return vibestore.snapshot(WORKSPACE_ID)


def enrich(board: dict) -> tuple[dict, list[dict]]:
    """Return (workspace, enriched tickets)."""
    ws = board["workspace"]
    gh_token = None
    tickets = []
    for t in board["tickets"]:
        if t["status"] == "verified":  # terminal; user signed off — nothing to poll or manage
            continue
        conv = conversation_info(t["conversation_id"]) if t.get("conversation_id") else None
        prs = None
        if t.get("pr_url") and t["status"] != "finished":
            if gh_token is None:
                gh_token = get_secret("GITHUB_PERSONAL_ACCESS_TOKEN")
            prs = pr_state(t["pr_url"], gh_token)
        t["conv_status"] = conv["status"] if conv else None
        t["conv_spend"] = conv["spend"] if conv else 0.0
        t["pr_state"] = prs
        tickets.append(t)
    return ws, tickets


def has_undispatched_entries(t: dict) -> bool:
    """True if a non-manager entry lies beyond dispatched_entry_count.

    dispatched_entry_count is an index into the full entry thread; only
    user/agent-authored entries past it count as awaiting dispatch. The
    manager's own append_entry comments live in the same thread and must be
    ignored here, or each status comment re-summons the manager forever
    (the 2026-08-21 overnight loop: 50 no-op manager runs).
    """
    dispatched = t.get("dispatched_entry_count", 0)
    return any(e.get("author") != "manager" for e in t["entries"][dispatched:])


def over_budget(t: dict) -> bool:
    """Has this ticket's worker spent the budget the user set on the request?"""
    budget = t.get("max_budget")
    if not budget or not t.get("conversation_id"):
        return False
    return (t.get("conv_spend") or 0.0) >= float(budget)


def apply_budget_stops(tickets: list[dict], state: dict) -> None:
    """Pause a worker that has spent its ticket's budget. Deterministic, no LLM.

    The agent server has no max-spend option of its own, so the cap chosen on
    the request is enforced here: the conversation is paused and the card goes
    to needs_input, where the user decides whether the work is worth more.
    Each conversation is stopped at most once (remembered in the KV state), so
    a deliberate resume — by the user or by the manager relaying a follow-up —
    is not immediately undone.
    """
    stopped = set(state.get("budget_stopped") or [])
    for t in tickets:
        conv_id = t.get("conversation_id")
        if conv_id in stopped or not over_budget(t):
            continue
        if (t.get("conv_status") or "") in TERMINAL_CONV_STATUSES:
            continue  # already done spending; nothing to pause
        spend, budget = t.get("conv_spend") or 0.0, float(t["max_budget"])
        print(f"budget: ticket {t['id']} spent ${spend:.2f} of ${budget:.2f} — pausing {conv_id}")
        try:
            agent(f"/api/conversations/{conv_id}/pause", "POST")
        except Exception as exc:  # noqa: BLE001
            print(f"budget: pausing {conv_id} failed: {exc}")
            continue
        vibestore.patch_ticket(
            WORKSPACE_ID, t["id"], status="needs_input",
            manager_note=f"Paused — spent ${spend:.2f} of the ${budget:.2f} budget",
        )
        t["status"] = "needs_input"
        t["conv_status"] = "paused"
        stopped.add(conv_id)
    state["budget_stopped"] = sorted(stopped)


def apply_mechanical_transitions(tickets: list[dict]) -> None:
    """PR open -> needs_input, PR merged -> finished. Deterministic, no LLM."""
    for t in tickets:
        prs = t.get("pr_state")
        if not prs:
            continue
        new_status = None
        note = None
        if prs == "merged" and t["status"] != "finished":
            new_status, note = "finished", "PR merged — ticket finished."
        elif prs == "open" and t["status"] not in ("needs_input", "finished"):
            # Only park the card once the worker is done pushing commits, and
            # not while a new user entry awaits dispatch (the app reopens such
            # tickets to pending; don't fight it before the manager relays it).
            undispatched = has_undispatched_entries(t)
            if not undispatched and (
                (t.get("conv_status") or "") in TERMINAL_CONV_STATUSES or not t.get("conversation_id")
            ):
                new_status, note = "needs_input", "PR is open and awaiting review."
        if new_status:
            print(f"mechanical: ticket {t['id']} {t['status']} -> {new_status} (pr {prs})")
            vibestore.patch_ticket(
                WORKSPACE_ID, t["id"], status=new_status, manager_note=note
            )
            t["status"] = new_status


def fingerprint(ws: dict, tickets: list[dict]) -> str:
    parts = [f"settings:{ws['max_concurrent']}:{ws['push_mode']}"]
    for t in sorted(tickets, key=lambda x: x["id"]):
        parts.append(
            ":".join(str(x) for x in (
                t["id"], t["status"], len(t["entries"]), t.get("dispatched_entry_count", 0),
                t.get("conversation_id"), t.get("conv_status"), t.get("pr_url"), t.get("pr_state"),
                ",".join(a["id"] for a in t.get("attachments", [])),
            ))
        )
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def compute_signals(ws: dict, tickets: list[dict]) -> tuple[list[str], list[str]]:
    """Actionable conditions that justify invoking the Manager agent.

    Returns (signals, retry_safe). `signals` gate kickoff on a board change;
    `retry_safe` additionally allow the slow-cadence retry. One-shot signals
    (e.g. a user appending to a deliberately deferred ticket) are excluded
    from retry_safe so a standing manager decision doesn't re-fire forever.

    Contract with the manager: deliberately deferring a pending ticket
    requires setting a manager_note, which suppresses re-kicks.
    """
    signals: list[str] = []
    retry_safe: list[str] = []
    running = sum(
        1 for t in tickets
        if t.get("conversation_id") and t.get("conv_status") == "running"
    )
    for t in tickets:
        undispatched = has_undispatched_entries(t)
        if undispatched:
            sig = f"new-entries:{t['id']}"
            signals.append(sig)
            if t.get("conversation_id"):
                retry_safe.append(sig)  # relayable follow-up; safe to retry
        if (
            t["status"] == "pending"
            and not t.get("conversation_id")
            and not t.get("manager_note")
            and running < ws["max_concurrent"]
        ):
            sig = f"dispatchable:{t['id']}"
            signals.append(sig)
            retry_safe.append(sig)
        if (
            t["status"] == "in_progress"
            and t.get("conversation_id")
            and (t.get("conv_status") or "") in TERMINAL_CONV_STATUSES
        ):
            sig = f"worker-done:{t['id']}"
            signals.append(sig)
            retry_safe.append(sig)
        # Conversation running but the board says otherwise (e.g. the user
        # manually sent a message to a needs_input worker): the agent is
        # working again — the manager should move the card to in_progress.
        if (
            t["status"] != "in_progress"
            and t.get("conversation_id")
            and t.get("conv_status") == "running"
        ):
            sig = f"agent-resumed:{t['id']}"
            signals.append(sig)
            retry_safe.append(sig)
    return signals, retry_safe


def kickoff_decision(state: dict, changed: bool, signals: list[str],
                     retry_safe: list[str], manager_failed: bool = False) -> tuple[bool, int]:
    """Return (kick_manager, retry_count) for this cycle.

    Normal path: kick when the board changed AND something is actionable.
    Safety net: if retry-safe signals persist without a board change (e.g. a
    previous manager run crashed before acting), retry on a slow cadence —
    but capped at MAX_RETRY_ATTEMPTS per unchanged fingerprint. Without the
    cap, a manager that completed but deliberately declined to act would be
    re-summoned every RETRY_INTERVAL forever (the 2026-08-21 overnight loop:
    50 no-op manager runs). The count resets whenever the fingerprint changes.

    `manager_failed` (the last manager conversation ended in error/stuck)
    skips the slow cadence: the board is unchanged precisely because that
    manager never acted, so waiting out RETRY_INTERVAL just leaves the cards
    stale. The attempt cap still applies, so a manager that keeps dying can
    only be restarted MAX_RETRY_ATTEMPTS times per board state.
    """
    retry_count = 0 if changed else state.get("retry_count", 0)
    waited = time.time() - (state.get("manager_started_at") or 0)
    stale_retry = (
        bool(retry_safe)
        and retry_count < MAX_RETRY_ATTEMPTS
        and (manager_failed or waited > RETRY_INTERVAL_SECONDS)
    )
    return bool(signals and changed) or stale_retry, retry_count


def conv_statuses(tickets: list[dict]) -> dict[str, str]:
    """Map conversation_id -> execution_status for every tracked ticket conversation."""
    return {
        t["conversation_id"]: t.get("conv_status") or "unknown"
        for t in tickets
        if t.get("conversation_id")
    }


# ------------------------------------------------------------- manager kickoff

def model_selection_instructions() -> str:
    """Manager-prompt policy for choosing worker LLM profiles."""
    return """## Model selection for workers
For manager-dispatched work, use only these GPT profiles and always pass the matching `--profile`:
- `gpt-6-astra` → high effort: architecture, tricky debugging, large refactors, vague requirements
- `gpt-5.6-sol` → medium/default effort: routine feature work and bug fixes
- `gpt-5.6-terra` → low effort: trivial chores, copy tweaks, docs, config, and one-liners
Do not select or recommend Anthropic profiles for manager-dispatched work. Passing `--profile` to a follow-up switches that EXISTING conversation's model first — escalate a stuck worker to a stronger GPT tier this way.
**The user's choice wins**: a ticket with a non-null `requested_model` runs on that profile, and passing `--ticket <ticket_id>` applies it for you — your `--profile` is ignored for that ticket. A null `requested_model` is "manager's choice": you pick from the GPT tiers above. Each ticket also carries `budget_usd`, the spend cap its worker gets; a worker that hits it is paused automatically and its card is moved to needs_input, so do not restart it without a new instruction from the user."""


def build_manager_prompt(ws: dict, tickets: list[dict]) -> str:
    board_json = json.dumps(
        [
            {
                "id": t["id"],
                "status": t["status"],
                "title": t.get("title"),
                "priority_rank": t["sort_order"],
                "conversation_id": t.get("conversation_id"),
                "conversation_status": t.get("conv_status"),
                "pr_url": t.get("pr_url"),
                "pr_state": t.get("pr_state"),
                "manager_note": t.get("manager_note"),
                "dispatched_entry_count": t.get("dispatched_entry_count", 0),
                "requested_model": t.get("llm_profile"),
                "budget_usd": t.get("max_budget"),
                "entries": [
                    {"author": e["author"], "body": e["body"], "created_at": e["created_at"]}
                    for e in t["entries"]
                ],
                "attachments": [
                    {
                        "filename": a["filename"],
                        "path": a["path"],
                        "content_type": a.get("content_type"),
                        "size": a.get("size"),
                    }
                    for a in t.get("attachments", [])
                ],
            }
            for t in tickets
        ],
        indent=1,
    )
    push_instructions = (
        "Push mode is **pull request**: workers must create a feature branch in their worktree, commit, "
        "push the branch, and open a PR against the default branch (gh CLI is available; "
        "GITHUB_PERSONAL_ACCESS_TOKEN is auto-injected into their terminal). When a worker finishes and "
        "reports a PR URL, patch the ticket with --pr-url and --status needs_input. "
        "(PR merged -> finished is handled automatically; don't merge PRs yourself.)"
        if ws["push_mode"] == "pr"
        else
        "Push mode is **push to main**: workers must commit in their worktree and push directly to the "
        "default branch (main). When a worker finishes and its commits are on main, set the ticket status "
        "to finished. Verify with `git log origin/main` if unsure."
    )
    push_instructions += (
        " Worker worktrees are branched off the freshly fetched default branch, but tell every worker to "
        "`git fetch origin` and rebase onto the latest default branch right before pushing, so concurrent "
        "workers never land on a stale base."
    )
    return f"""You are the **Vibe Manager** for the project at `{WORKSPACE_PATH}` (workspace id `{WORKSPACE_ID}`).
You manage a kanban queue of vibecoding tickets and a pool of worker agent conversations. You do NOT write feature code yourself — you dispatch and coordinate workers.

## Current board (tickets with full history)
```json
{board_json}
```

## Settings
- max concurrent worker conversations: **{ws['max_concurrent']}**
- {push_instructions}

## Board control (run `{VIBECTL}` from the terminal)

Every command prints JSON. A non-zero exit means it failed — read the `error` field rather than assuming success. The workspace id and project path are already in the environment, so you never pass them.

- **Update a ticket**: `{VIBECTL} patch <ticket_id> [options]`
  Options (all optional): `--status pending|in_progress|needs_input|finished`, `--title` (see the title rule below), `--conversation-id`, `--pr-url`, `--manager-note` (STATUS-ONLY one-liner shown on the card — see the note style rule; ALSO the contract for deferrals — see below), `--dispatched-entry-count <int>` (entries you have relayed so far), `--append-entry` (visible manager comment on the ticket thread).
- **Re-read the board**: `{VIBECTL} snapshot`

{model_selection_instructions()}

Worker dispatch — workers ALWAYS work in a git worktree, never in the main checkout. The worktree is provisioned for you, its path is appended to the worker's prompt, and the conversation is filed under the right workspace in the UI.

- **Start a worker**: `{VIBECTL} dispatch --ticket <ticket_id> --prompt-file <file> --title "🎫 <short summary>" [--profile <model>]`
  Write the task prompt to a file first (heredoc or the file editor) — do NOT try to pass a long multi-line prompt as a shell argument.
  ALWAYS pass `--ticket`: it applies the model the user requested on that ticket (see Model selection).
  Prints `{{"id": "<conversation_id>", ...}}` — immediately patch that id onto the ticket along with `--status in_progress`.
- **Follow up on an existing conversation**: `{VIBECTL} followup <conv_id> --ticket <ticket_id> --prompt-file <file> [--profile <model>]`
- **Inspect a conversation**: `{VIBECTL} conversation <conv_id> [--final-response]`
  Prints `execution_status` (running|idle|finished|error|stuck|paused), the model, and optionally the worker's final report.

## Your job this run
1. Read `AGENTS.md` in `{WORKSPACE_PATH}` (create it if missing) so you understand the project architecture. Keep it up to date: when finished tickets reveal new architecture/conventions, append concise notes so future workers benefit.
2. For every ticket whose worker conversation just ended (conversation_status finished/idle but ticket still in_progress): read its final response. If it opened a PR, patch --pr-url and --status needs_input. In push-to-main mode verify the push landed on main and normally mark finished. If the worker failed or stalled (error/stuck), decide: send a corrective follow-up message, or mark needs_input with a concise append_entry asking the user for guidance.
   - **Report-back/information rule**: first determine the ticket's intent from its user entries. If the ticket says "report back", asks a question, or otherwise asks for information (including investigation, research, status, or an explanation), then after the worker reports the requested information always patch it to `--status needs_input`, even in push-to-main mode. Do not mark it finished merely because no code or commit was expected; needs_input means the requested report is ready for the user to read and respond to.
   - Conversely, if a ticket's conversation_status is **running** but the ticket is needs_input/finished/pending, the user likely resumed the agent manually (sent it a message directly). Set the ticket status back to in_progress (and clear a stale manager_note with `--manager-note ''`) so the board reflects that the agent is working again.
3. For tickets with NEW user entries beyond dispatched_entry_count:
   - Only user/agent-authored entries count as new requests. If the entries beyond dispatched_entry_count are all manager comments (yours), there is nothing to relay — bump dispatched_entry_count to the current entry count so the board reads as fully dispatched, and move on.
   - If the ticket already has its OWN conversation, prefer **reusing it**: send a follow-up containing only the new user request and any new context needed to act on it, bump dispatched_entry_count to the current entry count, and ensure status is in_progress. The same ticket's existing conversation already contains its history, so do not replay the full prior ticket history in the follow-up.
   - A finished/needs_input ticket that receives a new user entry is automatically moved back to pending by the app; it moves to in_progress once you dispatch the follow-up.
4. For pending tickets with no conversation: dispatch workers, **highest priority first** (lower priority_rank = higher priority; the user orders cards within columns).
   - Respect the concurrency cap: count worker conversations currently in execution_status "running" on this board; never exceed **{ws['max_concurrent']}**.
   - **Avoid conflicts**: think about which tickets touch the same files/subsystems. Serialize tickets that would collide — run only independent tickets concurrently.
   - **Deferral contract**: if you deliberately leave a pending ticket undispatched (conflict serialization, capacity, needs another ticket first), you MUST set a manager_note on it (e.g. "queued behind a1b2c3 to avoid conflicts in the audio engine"). This suppresses re-invocation loops. Clear/replace the note when you later dispatch it.
   - **One conversation per ticket**: never graft a new ticket onto another ticket's conversation, however related. A conversation belongs to the ticket it was created for, and once that ticket is finished/verified it is retired — every new ticket gets a fresh conversation. (Follow-ups on the SAME ticket still reuse its own conversation — see 3.) Carry over context by putting it in the new worker's prompt, not by reusing the old thread.
5. Prompts that start a NEW worker conversation must be self-contained: the full ticket text (all user entries), the project path, a reminder to read AGENTS.md first, the push-mode instructions above (branch+PR, or push directly to main), and — in PR mode — to report the PR URL in their final message. Follow-ups to the same ticket are the exception: include only the new request/context needed, as described in 3, because that conversation already has the prior messages.
   - **Attachments**: tickets may carry file/image attachments (see each ticket's `attachments` array). Each has a stable absolute `path` on this machine, readable from worker worktrees. In a new-conversation prompt, list every attachment as `<filename> (<content_type>) at <path>` and tell the worker to read/view it from that path (agents can view images with the file viewer). In a follow-up, mention only new attachments or ones relevant to the new request. Workers must `cp` an attachment into their worktree only if it should become part of the repo. Never inline file contents into the prompt yourself.
6. Update every card you acted on: status, conversation_id, manager_note, dispatched_entry_count, and append_entry comments where the user needs context. Every ticket you dispatch MUST get its conversation_id set so the card links to its conversation.
   - **Note style rule**: manager_note and append_entry are STATUS ONLY — a few words about what happened, NEVER a description of the task itself (the card already shows the task). Good: "Worker dispatched", "Landed 37d9ab on origin/master", "Worker restarted for fix", "PR open, awaiting review". Bad: anything summarizing or paraphrasing the feature/bug. Two exceptions: deferral notes keep their short reason (see the deferral contract), and a needs_input append_entry may contain the specific question the user must answer.
7. **Title rule**: every ticket you touch that has a null `title` MUST get one via `patch --title`. Format: one emoji prefix + ONE or TWO words, NEVER more than two words (e.g. "🐛 Login fix", "🎨 Dark mode", "📎 Attachments"). Keep existing titles unless the ticket's scope clearly changed.
8. Do not wait for workers to finish — dispatch and exit. You will be re-invoked automatically when statuses change.

Be decisive and terse. When done, summarize what you dispatched/updated in one short final message."""


def start_manager_conversation(prompt: str) -> str:
    d = vibestore.start_conversation(
        WORKSPACE_PATH,
        prompt,
        title=f"🧠 Vibe Manager — {WORKSPACE_NAME} {time.strftime('%m-%d %H:%M')}",
        role="manager",
        # The manager only reads/updates AGENTS.md; workers get the worktrees.
        worktree=False,
        max_iterations=200,
        ws_id=WORKSPACE_ID,
    )
    return d["id"]


# ------------------------------------------------------------------------ main

def main() -> None:
    state = load_state()
    board = snapshot()

    # If a manager conversation is still running for this workspace, bail out.
    # Checks both the KV-tracked id and the workspace-row id (tag-verified),
    # so a lost KV state can't cause overlapping managers.
    mgr = manager_conversation_state(state, board["workspace"])
    if mgr["active"]:
        if time.time() - mgr["started_at"] < MANAGER_STALE_SECONDS:
            print(f"manager conversation {mgr['id']} still running — skipping")
            fire_callback()
            return
        print(f"manager conversation {mgr['id']} exceeded stale limit — proceeding")
    elif state.get("manager_conversation_id"):
        print(
            f"previous manager conversation {state['manager_conversation_id']} "
            f"ended ({mgr['status']})"
        )
        state["last_manager_finished_at"] = time.time()
    state["manager_conversation_id"] = None

    ws, tickets = enrich(board)
    apply_budget_stops(tickets, state)
    apply_mechanical_transitions(tickets)
    fp = fingerprint(ws, tickets)
    signals, retry_safe = compute_signals(ws, tickets)
    # Track each conversation's execution status so manual interventions
    # (e.g. the user messaging a needs_input worker, flipping it back to
    # running) are visible in the persisted state between runs.
    state["conv_statuses"] = conv_statuses(tickets)

    changed = fp != state.get("fingerprint")
    kick, retry_count = kickoff_decision(
        state, changed, signals, retry_safe, manager_failed=mgr["failed"]
    )
    print(
        f"fingerprint changed: {changed}; signals: {signals or 'none'}; "
        f"last manager: {mgr['status'] or 'none'}; "
        f"kick: {kick} (retries used: {retry_count}/{MAX_RETRY_ATTEMPTS})"
    )

    if kick:
        prompt = build_manager_prompt(ws, tickets)
        conv_id = start_manager_conversation(prompt)
        print(f"manager kicked off: {CANVAS_BASE}/conversations/{conv_id}")
        state.update({
            "manager_conversation_id": conv_id,
            "manager_started_at": time.time(),
            "fingerprint": fp,
            "retry_count": retry_count + (0 if changed else 1),
        })
    else:
        state["fingerprint"] = fp
        state["retry_count"] = retry_count

    state["last_checked_at"] = time.time()
    save_state(state)
    fire_callback()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        fire_callback("FAILED", str(exc))
        raise
