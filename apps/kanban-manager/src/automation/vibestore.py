"""Board state and worker dispatch for the Vibe Manager automation.

This is the half of the old vibe-manager service that could not move into the
browser: reading and writing the board on disk, provisioning git worktrees,
and creating agent conversations. The extension owns everything a browser can
reach; this owns everything that needs a shell.

Stdlib only — it is packaged into the automation tarball and runs wherever the
automation runs.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

STATUSES = ("pending", "in_progress", "needs_input", "finished")
VERIFIED = "verified"
WORKTREE_ROOT = Path("/tmp/conversation-worktrees")


def store_root() -> Path:
    """Root of the JSON store. Mirrors the extension's resolution order."""
    env = os.environ.get("VIBE_STORE_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".openhands" / "vibe-manager"


def now() -> float:
    return time.time()


def install_cli(workspace_id: str, workspace_path: str) -> str:
    """Copy the CLI to a stable per-workspace location and return its path.

    The automation tarball is unpacked into a per-run directory that may be
    cleaned up once the run ends, but the manager conversation it starts keeps
    working long after that — so the CLI it was told to call has to live
    somewhere that outlives the run. Refreshed every run, so a redeployed
    automation updates it.

    The install is scoped to the workspace because every workspace's cron
    re-installs once a minute: one shared config.json meant whichever cron ran
    last decided which board every manager's `vibectl` acted on, so managers
    read other projects' boards and patches against their own tickets failed
    with "ticket not found".
    """
    src = Path(__file__).parent
    bin_dir = store_root() / "bin" / workspace_id
    bin_dir.mkdir(parents=True, exist_ok=True)
    for name in ("vibestore.py", "vibectl.py"):
        shutil.copy2(src / name, bin_dir / name)
    (bin_dir / "vibectl.py").chmod(0o755)
    # Defaults for the manager's shell, which does not inherit the automation
    # run's environment.
    (bin_dir / "config.json").write_text(json.dumps({
        "workspace_id": workspace_id,
        "workspace_path": workspace_path,
        "store_dir": str(store_root()),
    }, indent=2))
    # Retire the shared config a manager conversation from before this change
    # may still be pointed at: without it that CLI reports a missing workspace
    # instead of silently acting on whichever one was installed last.
    (store_root() / "bin" / "config.json").unlink(missing_ok=True)
    return str(bin_dir / "vibectl.py")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


# ----------------------------------------------------------------- json files

def _read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return fallback
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"corrupt JSON at {path}: {exc}") from exc


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write-then-rename: a crash mid-write must not truncate the board.
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    tmp.replace(path)


def _stamp(doc: dict, **fields) -> dict:
    """Prepare a document for its next write. Mirrors store.js `stamp`."""
    return {**doc, **fields, "rev": (doc.get("rev") or 0) + 1, "writer": new_id()}


@contextlib.contextmanager
def _locked(path: Path):
    """Serialize the shell-side writers of one document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".lock")
    with open(lock, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _mutate_document(path: Path, read, write, mutate, attempts: int = 5):
    """Read-modify-write `path`, re-applying `mutate` if another writer lands.

    The browser writes these same documents through the agent server's file
    API, which no local lock can reach, so the lock only serializes the shell
    side and the revision check catches the browser. Without it a card the
    user had just added was silently dropped by the next manager patch.
    """
    for _ in range(attempts):
        with _locked(path):
            doc = read()
            base = doc.get("rev") or 0
            result = mutate(doc)
            if (read().get("rev") or 0) != base:
                continue  # the browser wrote while we worked; start over
            token = write(doc)
            after = read()
            # `rev > base + 1` means someone built on top of our write.
            if after.get("writer") == token or (after.get("rev") or 0) > base + 1:
                return result
    raise RuntimeError(f"{path.name} is being written concurrently; retry")


def index_path() -> Path:
    return store_root() / "index.json"


def read_index() -> dict:
    return _read_json(index_path(), {"version": 1, "workspaces": []})


def write_index(index: dict) -> str:
    """Write the index and return the token identifying this write."""
    stamped = _stamp(index, version=1)
    _write_json(index_path(), stamped)
    return stamped["writer"]


def mutate_index(mutate):
    return _mutate_document(index_path(), read_index, write_index, mutate)


def get_workspace(ws_id: str) -> dict | None:
    for ws in read_index().get("workspaces", []):
        if ws.get("id") == ws_id:
            return ws
    return None


def update_workspace(ws_id: str, **patch) -> dict:
    def mutate(index: dict) -> dict:
        for ws in index.get("workspaces", []):
            if ws.get("id") == ws_id:
                ws.update(patch)
                return ws
        raise KeyError(f"workspace {ws_id} not found")

    return mutate_index(mutate)


def board_path(ws_id: str) -> Path:
    return store_root() / "workspaces" / ws_id / "board.json"


def tickets_dir(ws_id: str) -> Path:
    return store_root() / "workspaces" / ws_id / "tickets"


def ticket_path(ws_id: str, ticket_id: str) -> Path:
    """One directory per ticket; see store.js for why it is a dir, not a file."""
    return tickets_dir(ws_id) / ticket_id / "ticket.json"


def _by_priority(ticket: dict) -> tuple:
    return (ticket.get("sort_order") or 0, ticket.get("created_at") or 0)


def read_board(ws_id: str) -> dict:
    """Rebuild the board from the per-ticket files.

    Falls back to a pre-split board.json so a workspace that has not been
    migrated yet still reads correctly.
    """
    directory = tickets_dir(ws_id)
    if not directory.is_dir():
        board = _read_json(
            board_path(ws_id), {"version": 2, "workspace_id": ws_id, "tickets": []}
        )
        board.setdefault("tickets", [])
        board["tickets"].sort(key=_by_priority)
        return board

    tickets = []
    for entry in directory.iterdir():
        if not entry.is_dir():
            continue
        ticket = _read_json(entry / "ticket.json", None)
        if ticket:
            tickets.append(ticket)
    tickets.sort(key=_by_priority)
    return {"version": 2, "workspace_id": ws_id, "tickets": tickets}


def write_board(ws_id: str, board: dict) -> None:
    """Write a whole board out as per-ticket files.

    No longer a single document write, so it carries no revision token: it is
    used to seed or migrate a board, never to land a concurrent edit.
    """
    for ticket in board.get("tickets", []):
        write_ticket(ws_id, ticket)


def read_ticket(ws_id: str, ticket_id: str) -> dict | None:
    return _read_json(ticket_path(ws_id, ticket_id), None)


def write_ticket(ws_id: str, ticket: dict) -> str:
    """Write one ticket and return the token identifying this write."""
    stamped = _stamp(ticket)
    _write_json(ticket_path(ws_id, ticket["id"]), stamped)
    return stamped["writer"]


def mutate_ticket(ws_id: str, ticket_id: str, mutate):
    """Read-modify-write a single ticket file.

    Writers touching different tickets no longer share a document, so the
    manager patching one card cannot drop a card the user added meanwhile.
    """
    def read() -> dict:
        ticket = read_ticket(ws_id, ticket_id)
        if ticket is None:
            raise KeyError(f"ticket {ticket_id} not found")
        return ticket

    return _mutate_document(
        ticket_path(ws_id, ticket_id),
        read,
        lambda ticket: write_ticket(ws_id, ticket),
        mutate,
    )


def snapshot(ws_id: str) -> dict:
    """Board in the shape the old /api/manager/.../snapshot endpoint returned."""
    return {"workspace": get_workspace(ws_id), "tickets": read_board(ws_id)["tickets"]}


def get_ticket(ws_id: str, ticket_id: str) -> dict:
    ticket = next((t for t in read_board(ws_id)["tickets"] if t["id"] == ticket_id), None)
    if ticket is None:
        raise KeyError(f"ticket {ticket_id} not found")
    return ticket


def ticket_llm_profile(ws_id: str | None, ticket_id: str | None) -> str | None:
    """The model the user asked for on a ticket, if any.

    None means "manager's choice": the ticket carries no explicit selection,
    so the model the manager picked for this dispatch stands.
    """
    if not (ws_id and ticket_id):
        return None
    return get_ticket(ws_id, ticket_id).get("llm_profile") or None


# --------------------------------------------------------------- ticket patch

def patch_ticket(
    ws_id: str,
    ticket_id: str,
    *,
    status: str | None = None,
    title: str | None = None,
    conversation_id: str | None = None,
    pr_url: str | None = None,
    manager_note: str | None = None,
    dispatched_entry_count: int | None = None,
    append_entry: str | None = None,
) -> dict:
    """Manager-side ticket update. Same semantics as the old PATCH endpoint."""
    if status is not None and status not in STATUSES:
        raise ValueError(f"bad status {status!r}; expected one of {list(STATUSES)}")

    stamp = now()

    def mutate(ticket: dict) -> dict:
        return _apply_ticket_patch(
            ticket, stamp,
            status=status, title=title, conversation_id=conversation_id, pr_url=pr_url,
            manager_note=manager_note, dispatched_entry_count=dispatched_entry_count,
            append_entry=append_entry,
        )

    return mutate_ticket(ws_id, ticket_id, mutate)


def _apply_ticket_patch(
    ticket: dict,
    stamp: float,
    *,
    status: str | None,
    title: str | None,
    conversation_id: str | None,
    pr_url: str | None,
    manager_note: str | None,
    dispatched_entry_count: int | None,
    append_entry: str | None,
) -> dict:
    touched = False
    if status is not None:
        if status == "finished" and ticket.get("status") != "finished":
            ticket["finished_at"] = stamp
        ticket["status"] = status
        touched = True
    if title is not None:
        ticket["title"] = title.strip() or None
        touched = True
    if conversation_id is not None:
        ticket["conversation_id"] = conversation_id
        touched = True
    if pr_url is not None:
        ticket["pr_url"] = pr_url
        touched = True
    if manager_note is not None:
        ticket["manager_note"] = manager_note
        touched = True
    if dispatched_entry_count is not None:
        ticket["dispatched_entry_count"] = int(dispatched_entry_count)
        touched = True

    if append_entry and append_entry.strip():
        ticket.setdefault("entries", []).append({
            "id": new_id(),
            "author": "manager",
            "body": append_entry.strip(),
            "created_at": stamp,
        })
        # Absorb trailing manager comments into dispatched_entry_count so the
        # manager's own notes never read as "undispatched entries" and
        # re-summon it. Never advances past a user/agent entry.
        authors = [e["author"] for e in ticket["entries"]]
        advanced = int(ticket.get("dispatched_entry_count") or 0)
        while advanced < len(authors) and authors[advanced] == "manager":
            advanced += 1
        ticket["dispatched_entry_count"] = advanced
        touched = True

    if touched:
        ticket["updated_at"] = stamp
    return ticket


# -------------------------------------------------------------- agent server

def agent_server_url() -> str:
    return os.environ.get("AGENT_SERVER_URL", "http://127.0.0.1:18000").rstrip("/")


def session_key() -> str:
    key = os.environ.get("SESSION_API_KEY") or os.environ.get("OH_SESSION_API_KEYS_0")
    if key:
        return key
    # Falls back to the on-disk key the service used, for local runs.
    for candidate in (Path.cwd() / ".session-key", Path("/root/git/vibe-manager/.session-key")):
        if candidate.exists():
            return candidate.read_text().strip()
    raise RuntimeError("no agent-server session key available")


def agent_request(path: str, method: str = "GET", data: dict | None = None,
                  extra_headers: dict | None = None, timeout: int = 60):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        f"{agent_server_url()}{path}", data=body, method=method,
        headers={
            "Content-Type": "application/json",
            "X-Session-API-Key": session_key(),
            **(extra_headers or {}),
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode()
    return json.loads(raw) if raw else None


def llm_profiles() -> dict:
    """Available LLM profiles, without secrets."""
    try:
        data = agent_request("/api/profiles", timeout=15)
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return {"profiles": [], "active_profile": None}
    # The list endpoint returns `model` at the top level of each profile; only
    # GET /api/profiles/<name> nests the full LLM config under "config".
    profiles = [
        {"name": p.get("name"), "model": p.get("model")}
        for p in (data.get("profiles") or [])
    ]
    return {"profiles": profiles, "active_profile": data.get("active_profile")}


def agent_settings_payload(llm_profile: str | None = None) -> dict:
    """Active agent settings with encrypted secrets and default exec tools.

    The stored `tools` value is `[]`, which means a bare agent with no tools;
    `None` makes the SDK resolve the standard exec set instead. When a profile
    is named, its own LLM config (which carries its own encrypted key)
    replaces the settings LLM.
    """
    headers = {"X-Expose-Secrets": "encrypted"}
    settings = agent_request("/api/settings", extra_headers=headers, timeout=15)["agent_settings"]
    settings["tools"] = None
    if llm_profile:
        try:
            profile = agent_request(
                f"/api/profiles/{llm_profile}", extra_headers=headers, timeout=15
            )
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                names = [p["name"] for p in llm_profiles()["profiles"]]
                raise ValueError(
                    f"unknown llm_profile {llm_profile!r}; available: {names}"
                ) from exc
            raise
        config = profile["config"]
        # Keep the usage_id the settings LLM carries — profile dumps default it.
        config["usage_id"] = (settings.get("llm") or {}).get("usage_id") or "default"
        settings["llm"] = config
    return settings


# ------------------------------------------------------------------- git work

def git(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(project), *args],
        capture_output=True, text=True, timeout=120,
    )


def origin_default_ref(project: Path) -> str | None:
    """Remote-tracking ref of origin's default branch (e.g. `origin/master`).

    `origin/HEAD` is missing in `--single-branch` clones and in repos whose
    remote was added by hand, so it is resolved from the remote when absent.
    """
    if git(project, "remote", "get-url", "origin").returncode != 0:
        return None
    head = git(project, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if head.returncode != 0:
        git(project, "remote", "set-head", "origin", "--auto")
        head = git(project, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
        if head.returncode != 0:
            return None
    return head.stdout.strip().removeprefix("refs/remotes/")


def fast_forward_project(project: Path, default_ref: str) -> None:
    """Fast-forward the checkout so it stops drifting behind origin.

    Deliberately a no-op unless the checkout is on the default branch, clean
    and strictly behind origin: never touch a human's in-flight work.
    """
    branch = git(project, "symbolic-ref", "--quiet", "--short", "HEAD")
    if branch.returncode != 0 or branch.stdout.strip() != default_ref.split("/", 1)[1]:
        return
    if git(project, "status", "--porcelain").stdout.strip():
        return
    git(project, "merge", "--ff-only", default_ref)


def sync_project_checkout(project: Path) -> str | None:
    """Fetch origin and fast-forward the checkout to origin's default branch.

    Returns the ref workers should branch from, or None for repos with no
    origin. A failed fetch raises rather than falling back to a local ref, so
    a worker never starts from a base that is behind the default branch.
    """
    default_ref = origin_default_ref(project)
    if default_ref is None:
        return None
    r = git(project, "fetch", "--prune", "origin")
    if r.returncode != 0:
        raise RuntimeError(f"git fetch origin failed in {project}: {r.stderr.strip()[:300]}")
    fast_forward_project(project, default_ref)
    return default_ref


def refresh_workspace_checkout(working_dir: str) -> None:
    """Best-effort refresh for conversations that run in the checkout itself.

    Manager conversations need it current, but a fetch failure must not block
    coordination work.
    """
    try:
        sync_project_checkout(Path(working_dir).resolve())
    except (RuntimeError, OSError, subprocess.SubprocessError):
        pass


def provision_worker_worktree(working_dir: str, conv_id: str) -> dict:
    """Create an isolation git worktree for a worker conversation.

    Created here rather than via the agent server's `worktree: true`, which
    would rewrite `workspace.working_dir` to the worktree path and dissociate
    the conversation from its workspace in the UI.
    """
    project = Path(working_dir).resolve()
    wt_path = WORKTREE_ROOT / conv_id / project.name
    start = sync_project_checkout(project) or "HEAD"
    wt_path.parent.mkdir(parents=True, exist_ok=True)
    branch = f"openhands/{conv_id}"
    r = git(project, "worktree", "add", "-b", branch, str(wt_path), start)
    if r.returncode != 0:
        raise RuntimeError(f"git worktree add failed: {r.stderr.strip()[:300]}")
    return {"path": str(wt_path), "branch": branch, "start": start}


def worktree_guidance(working_dir: str, wt: dict) -> str:
    return (
        "\n\nThis conversation uses a dedicated git worktree.\n"
        f"- Original workspace: {working_dir}\n"
        f"- Worktree (do ALL file and git work here): {wt['path']}\n"
        f"- You are on branch `{wt['branch']}` (based on {wt['start']}).\n"
        "cd into the worktree before doing anything else; never modify the "
        "original checkout directly."
    )


# ---------------------------------------------------------------- dispatching

def canvas_base() -> str:
    return os.environ.get("VIBE_CANVAS_BASE", "https://canvas.rbren.io").rstrip("/")


def start_conversation(
    working_dir: str,
    prompt: str,
    *,
    title: str | None = None,
    llm_profile: str | None = None,
    conversation_id: str | None = None,
    role: str = "worker",
    worktree: bool = True,
    max_iterations: int = 500,
    ws_id: str | None = None,
    ticket_id: str | None = None,
) -> dict:
    """Start a worker/manager conversation, or follow up on an existing one.

    A ticket's own model selection wins over `llm_profile`: what the user
    picked on the request is what the worker runs on.
    """
    llm_profile = ticket_llm_profile(ws_id, ticket_id) or llm_profile
    if conversation_id:
        if llm_profile:
            agent_request(
                f"/api/conversations/{conversation_id}/switch_profile",
                "POST", {"profile_name": llm_profile},
            )
        agent_request(
            f"/api/conversations/{conversation_id}/events", "POST",
            {"role": "user", "content": [{"text": prompt}], "run": True},
        )
        _ensure_workspace_tags(conversation_id, working_dir, role)
        return {
            "id": conversation_id,
            "followup": True,
            "conversation_url": f"{canvas_base()}/conversations/{conversation_id}",
        }

    conv_id = str(uuid.uuid4())
    # Resolve settings (and validate llm_profile) BEFORE provisioning the
    # worktree, so an unknown profile never leaks one.
    settings = agent_settings_payload(llm_profile)

    wt = None
    if worktree:
        wt = provision_worker_worktree(working_dir, conv_id)
        prompt += worktree_guidance(working_dir, wt)
    else:
        refresh_workspace_checkout(working_dir)

    body = {
        "workspace": {"kind": "LocalWorkspace", "working_dir": working_dir},
        # `true` here would rewrite working_dir to the worktree path.
        "worktree": False,
        "conversation_id": conv_id,
        "agent_settings": settings,
        "secrets_encrypted": True,
        "initial_message": {"role": "user", "content": [{"text": prompt}], "run": True},
        "max_iterations": max_iterations,
        "autotitle": not title,
        "tags": {"workspace": working_dir, "viberole": role},
    }
    try:
        created = agent_request("/api/conversations", "POST", body, timeout=120)
    except Exception:
        if wt:  # don't leak the orphaned isolation worktree
            git(Path(working_dir), "worktree", "remove", "--force", wt["path"])
            git(Path(working_dir), "branch", "-D", wt["branch"])
        raise

    conv_id = created["id"]
    if role == "manager" and ws_id:
        update_workspace(ws_id, manager_conversation_id=conv_id)
    if title:
        agent_request(f"/api/conversations/{conv_id}", "PATCH", {"title": title})
    return {
        "id": conv_id,
        "followup": False,
        "conversation_url": f"{canvas_base()}/conversations/{conv_id}",
    }


def _ensure_workspace_tags(conv_id: str, working_dir: str, role: str) -> None:
    """Retro-tag a conversation that predates tagging.

    PATCH replaces the whole tag map, so existing tags are merged in.
    """
    try:
        conv = agent_request(f"/api/conversations/{conv_id}?include_skills=false", timeout=30)
        tags = dict(conv.get("tags") or {})
        if tags.get("workspace"):
            return
        tags.update({"workspace": working_dir, "viberole": tags.get("viberole") or role})
        agent_request(f"/api/conversations/{conv_id}", "PATCH", {"tags": tags}, timeout=30)
    except Exception:
        # Tagging is cosmetic (UI grouping); never fail a dispatch over it.
        pass
