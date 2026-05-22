"""
GitHub Repository Monitor  -  OpenHands Automation Script

Polls a GitHub repository on a cron schedule. When an event matching the
configured trigger phrase and event-type filter is detected it:
  1. Posts a GitHub comment acknowledging the request with a conversation link.
  2. Creates (or resumes) an OpenHands conversation pre-loaded with full
     issue/PR context and recent comment history.
  3. When the conversation reaches a terminal/idle state the agent's final
     response is posted back to the issue/PR as a GitHub comment.

On subsequent runs:
  - New trigger comments on a tracked issue/PR are forwarded to the running
    conversation.
  - If the previous conversation was closed/deleted a new one is created.

Configuration constants are embedded at automation-creation time by the skill.
See SKILL.md for the full setup workflow.

Required secrets (set in OpenHands Settings → Secrets):
  GITHUB_TOKEN  - Personal Access Token
                  Classic PAT:       'repo' scope (private) or 'public_repo' (public)
                  Fine-grained PAT:  Issues: Read and Write

Optional secret:
  OPENHANDS_URL - base URL for conversation links (default: http://localhost:8000)
"""

import json
import os
import sys
from pathlib import Path
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

# ── Embedded configuration (filled in by the skill at creation time) ──────────
REPO = "owner/repo"                     # e.g. "microsoft/vscode"
TRIGGER_PHRASE = "@openhands"           # case-insensitive
EVENT_TYPES = ["issue_comment"]         # e.g. ["issue_comment", "pr_review_comment"]
DEFAULT_OPENHANDS_URL = "http://localhost:8000"

# Context: number of recent issue/PR comments to include in the initial prompt.
CONTEXT_COMMENT_LIMIT = 10

# Lookback slightly over 60 s on the first run to avoid boundary gaps.
INITIAL_LOOKBACK_SECONDS = 70

# Prevent posting summaries in the same run that created the conversation.
DONE_DEBOUNCE = 15

# Rolling window for processed event IDs — sized for ~1 week at high volume.
MAX_PROCESSED_IDS = 5000


# ── Stdlib helpers ─────────────────────────────────────────────────────────────

def _get_env_key() -> str:
    return (
        os.environ.get("SESSION_API_KEY")
        or os.environ.get("OH_SESSION_API_KEYS_0")
        or ""
    )


def get_secret(name: str) -> str:
    """Fetch a named secret from the agent server."""
    url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    key = _get_env_key()
    req = urllib.request.Request(
        f"{url}/api/settings/secrets/{name}",
        headers={"X-Session-API-Key": key},
    )
    with urllib.request.urlopen(req) as r:
        return r.read().decode().strip()


def fire_callback(status: str = "COMPLETED", error: str | None = None) -> None:
    """Signal run completion to the automation service."""
    url = os.environ.get("AUTOMATION_CALLBACK_URL", "")
    if not url:
        return
    body: dict = {"status": status, "run_id": os.environ.get("AUTOMATION_RUN_ID", "")}
    if error:
        body["error"] = error
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('AUTOMATION_CALLBACK_API_KEY', '')}",
        },
    )
    try:
        urllib.request.urlopen(req)
    except Exception as exc:
        print(f"Callback error (non-fatal): {exc}")


# ── State management ───────────────────────────────────────────────────────────

def _state_file_path() -> str:
    """Derive a persistent storage path from WORKSPACE_BASE.

    WORKSPACE_BASE = {root}/automation-runs/{run_id}
    State lives two levels up at {root}/automation-state/.
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
    return str(state_dir / f"github_poller_{automation_id}.json")


def _default_since() -> str:
    """ISO 8601 UTC timestamp for the initial lookback window."""
    return (
        datetime.now(timezone.utc) - timedelta(seconds=INITIAL_LOOKBACK_SECONDS)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: state file {path} unreadable ({exc}); starting fresh")
    return {
        "version": 1,
        "repo": REPO,
        "last_poll": _default_since(),
        "conversations": {},       # issue_number (str) → ConversationRecord
        "processed_comment_ids": [],  # list of int comment IDs already handled
    }


def save_state(path: str, state: dict) -> None:
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


# ── GitHub API helpers ─────────────────────────────────────────────────────────

def _github_request(
    token: str,
    method: str,
    path: str,
    params: dict | None = None,
    body: dict | None = None,
) -> tuple[dict | list, dict]:
    """Low-level GitHub API call.  Returns (parsed_body, response_headers).
    Raises urllib.error.HTTPError on non-2xx responses.
    """
    base = "https://api.github.com"
    url = f"{base}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as r:
        resp_headers = dict(r.headers)
        raw = r.read()
        return (json.loads(raw) if raw.strip() else {}), resp_headers


def _github_paginate(token: str, path: str, params: dict | None = None) -> list:
    """Fetch all pages from a GitHub list endpoint."""
    results = []
    page = 1
    base_params = dict(params or {})
    base_params.setdefault("per_page", 100)
    while True:
        base_params["page"] = page
        data, _ = _github_request(token, "GET", path, params=base_params)
        if not isinstance(data, list):
            break
        results.extend(data)
        if len(data) < base_params["per_page"]:
            break
        page += 1
    return results


def _resolve_github_token() -> str:
    """Fetch GITHUB_TOKEN from secrets.  Raises RuntimeError if absent."""
    try:
        token = get_secret("GITHUB_TOKEN")
        if token:
            return token
    except Exception:
        pass
    raise RuntimeError(
        "GITHUB_TOKEN secret is not set. "
        "Go to OpenHands Settings → Secrets and add your GitHub Personal Access Token."
    )


def _verify_token_and_repo(token: str, repo: str) -> str:
    """Verify the token is valid, the repo is accessible, and the token can
    post comments.  Returns the authenticated GitHub username.
    Raises RuntimeError with a user-friendly message on any failure.
    """
    # 1. Verify token validity and get scopes.
    try:
        user_data, user_headers = _github_request(token, "GET", "/user")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError(
                "GITHUB_TOKEN is invalid or expired. "
                "Update it in OpenHands Settings → Secrets."
            )
        raise RuntimeError(f"GitHub /user check failed: {exc.code}")

    username: str = user_data.get("login", "?")
    scopes_header: str = user_headers.get("X-OAuth-Scopes", "") or ""
    scopes = {s.strip() for s in scopes_header.split(",") if s.strip()}
    print(f"Authenticated as GitHub user: {username}  scopes: {scopes or '(fine-grained PAT)'}")

    # 2. Verify repo access.
    try:
        repo_data, _ = _github_request(token, "GET", f"/repos/{repo}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError(
                f"Repository '{repo}' not found or not accessible with the current GITHUB_TOKEN. "
                "Check the repo name (format: owner/repo) and token permissions."
            )
        if exc.code == 403:
            raise RuntimeError(
                f"Access denied to repository '{repo}'. "
                "Ensure GITHUB_TOKEN has the required permissions."
            )
        raise RuntimeError(f"GitHub /repos/{repo} check failed: {exc.code}")

    # 3. Verify comment-posting permission.
    is_private: bool = repo_data.get("private", False)
    permissions: dict = repo_data.get("permissions", {})
    can_push: bool = permissions.get("push", False)
    has_repo_scope: bool = "repo" in scopes
    has_public_repo_scope: bool = "public_repo" in scopes

    if is_private:
        # Private repo: must have push access or the 'repo' classic-PAT scope.
        if not can_push and not has_repo_scope and scopes:
            raise RuntimeError(
                f"GITHUB_TOKEN cannot post comments to private repository '{repo}'. "
                "A classic PAT needs the 'repo' scope; "
                "a fine-grained PAT needs 'Issues: Read and Write' permission."
            )
    else:
        # Public repo: need at minimum 'public_repo' scope or push access.
        if scopes and not (can_push or has_public_repo_scope or has_repo_scope):
            raise RuntimeError(
                f"GITHUB_TOKEN cannot post comments to public repository '{repo}'. "
                "A classic PAT needs the 'public_repo' scope; "
                "a fine-grained PAT needs 'Issues: Read and Write' permission."
            )

    print(f"Repository '{repo}' accessible. Private: {is_private}. Can push: {can_push}")
    return username


def _poll_issue_comments(token: str, repo: str, since: str) -> list[dict]:
    """Fetch all issue/PR comments created after `since` (ISO 8601 UTC)."""
    return _github_paginate(
        token,
        f"/repos/{repo}/issues/comments",
        {"since": since, "sort": "created", "direction": "asc"},
    )


def _poll_pr_review_comments(token: str, repo: str, since: str) -> list[dict]:
    """Fetch all PR inline review comments created after `since`."""
    return _github_paginate(
        token,
        f"/repos/{repo}/pulls/comments",
        {"since": since, "sort": "created", "direction": "asc"},
    )


def _extract_issue_number(comment: dict, event_type: str) -> int | None:
    """Extract the issue/PR number from a comment object."""
    try:
        if event_type == "issue_comment":
            # issue_url: .../repos/owner/repo/issues/42
            return int(comment["issue_url"].rstrip("/").rsplit("/", 1)[-1])
        if event_type == "pr_review_comment":
            # pull_request_url: .../repos/owner/repo/pulls/15
            return int(comment["pull_request_url"].rstrip("/").rsplit("/", 1)[-1])
    except (KeyError, ValueError, AttributeError):
        pass
    return None


def _get_issue_context(token: str, repo: str, issue_number: int) -> dict:
    """Fetch issue/PR metadata and up to CONTEXT_COMMENT_LIMIT recent comments."""
    issue_data, _ = _github_request(token, "GET", f"/repos/{repo}/issues/{issue_number}")

    # Fetch last CONTEXT_COMMENT_LIMIT comments (GitHub returns oldest-first by default).
    # We request a larger page and take the tail to get the most recent ones.
    all_comments = _github_paginate(
        token,
        f"/repos/{repo}/issues/{issue_number}/comments",
        {"per_page": 100},
    )
    recent_comments = all_comments[-CONTEXT_COMMENT_LIMIT:]

    return {
        "issue": issue_data,
        "recent_comments": recent_comments,
        "is_pr": "pull_request" in issue_data,
    }


def _post_github_comment(token: str, repo: str, issue_number: int, body: str) -> int | None:
    """Post a comment on an issue/PR and return the comment ID."""
    try:
        result, _ = _github_request(
            token,
            "POST",
            f"/repos/{repo}/issues/{issue_number}/comments",
            body={"body": body},
        )
        return result.get("id")
    except Exception as exc:
        print(f"  Warning: failed to post GitHub comment on #{issue_number}: {exc}")
        return None


# ── OpenHands conversation helpers ────────────────────────────────────────────

def _oh_request(
    agent_url: str, api_key: str, method: str, path: str, body: dict | None = None
) -> dict:
    url = f"{agent_url}{path}"
    headers = {"X-Session-API-Key": api_key, "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode()
        raise RuntimeError(f"Agent API {method} {path} → {exc.code}: {body_text}") from exc


def _get_agent_dict(agent_url: str, api_key: str) -> dict:
    """Fetch configured agent settings for conversation creation."""
    url = f"{agent_url}/api/settings"
    headers = {"X-Session-API-Key": api_key, "X-Expose-Secrets": "plaintext"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GET /api/settings failed: {exc.code}") from exc
    agent_settings = data.get("agent_settings", {})
    llm = agent_settings.get("llm", {})
    # settings["agent_settings"]["agent"] reflects the full-app agent registry
    # (e.g. "CodeActAgent", "BrowsingAgent").  The automation SDK is a separate
    # runtime whose only valid kind is "Agent" — never forward that value.
    return {
        "kind": "Agent",
        "llm": llm,
        # "terminal" and "file_editor" are the runtime-registered tool names.
        # Without an explicit tools list the SDK Agent defaults to think+finish only.
        "tools": [{"name": "terminal"}, {"name": "file_editor"}],
    }


def create_conversation(agent_url: str, api_key: str, initial_message: str) -> str:
    """Create an OpenHands conversation and return its ID."""
    workspace_dir = os.environ.get("WORKSPACE_BASE", "/workspace")
    agent = _get_agent_dict(agent_url, api_key)
    result = _oh_request(agent_url, api_key, "POST", "/api/conversations", {
        "workspace": {"working_dir": workspace_dir},
        "agent": agent,
        "initial_message": {"content": [{"text": initial_message}]},
    })
    return result["id"]


def send_to_conversation(agent_url: str, api_key: str, conv_id: str, text: str) -> None:
    """Send a user message to an existing conversation and resume the agent."""
    _oh_request(agent_url, api_key, "POST", f"/api/conversations/{conv_id}/events", {
        "role": "user",
        "content": [{"text": text}],
        "run": True,
    })


def conversation_status(agent_url: str, api_key: str, conv_id: str) -> str:
    result = _oh_request(agent_url, api_key, "GET", f"/api/conversations/{conv_id}")
    return result.get("execution_status", "unknown")


def conversation_final_response(agent_url: str, api_key: str, conv_id: str) -> str:
    result = _oh_request(
        agent_url, api_key, "GET", f"/api/conversations/{conv_id}/agent_final_response"
    )
    return result.get("response", "")


# ── Comment filtering helpers ─────────────────────────────────────────────────

def _is_bot_comment(comment: dict) -> bool:
    """Return True if the comment was posted by a bot account."""
    user = comment.get("user") or {}
    login = user.get("login", "")
    return login.endswith("[bot]") or user.get("type") == "Bot"


def _has_trigger(comment: dict, phrase: str) -> bool:
    """Return True if the comment body contains *phrase* (case-insensitive)."""
    body = (comment.get("body") or "").strip()
    return phrase.lower() in body.lower()


# ── Prompt building ────────────────────────────────────────────────────────────

def _build_initial_prompt(ctx: dict, trigger_comment: dict, event_type: str) -> str:
    """Build the initial prompt for a new OpenHands conversation."""
    issue = ctx["issue"]
    is_pr = ctx["is_pr"]
    item_type = "Pull Request" if is_pr else "Issue"
    number = issue.get("number", "?")
    title = issue.get("title", "(no title)")
    body = (issue.get("body") or "").strip() or "(no description)"
    state = issue.get("state", "?")
    html_url = issue.get("html_url", "")
    labels = [lb["name"] for lb in issue.get("labels", [])]
    label_str = ", ".join(labels) if labels else "(none)"

    comment_lines: list[str] = []
    for c in ctx["recent_comments"]:
        author = c.get("user", {}).get("login", "?")
        c_body = (c.get("body") or "").strip()
        comment_lines.append(f"[{author}]: {c_body}")
    context_block = "\n".join(comment_lines) if comment_lines else "(no prior comments)"

    trigger_author = trigger_comment.get("user", {}).get("login", "?")
    trigger_body = (trigger_comment.get("body") or "").strip()

    path_info = ""
    if event_type == "pr_review_comment":
        path = trigger_comment.get("path", "")
        line = trigger_comment.get("line") or trigger_comment.get("original_line")
        if path:
            path_info = f"\nTriggering comment location: {path}" + (f" line {line}" if line else "")

    return (
        f"You are an AI assistant responding to a request on a GitHub {item_type}.\n\n"
        f"Repository : {REPO}\n"
        f"{item_type} #{number}: \"{title}\"\n"
        f"State      : {state}\n"
        f"Labels     : {label_str}\n"
        f"URL        : {html_url}\n"
        f"\nDescription:\n---\n{body}\n---\n"
        f"\nRecent comments (oldest → newest, up to {CONTEXT_COMMENT_LIMIT}):\n"
        f"---\n{context_block}\n---\n"
        f"\nTriggering comment by @{trigger_author}:{path_info}\n"
        f"---\n{trigger_body}\n---\n"
        f"\nPlease analyse the request and take the appropriate action.\n"
        f"The GITHUB_TOKEN secret is available if you need to interact with the "
        f"GitHub API (fetch the PR diff, create commits, update labels, etc.).\n"
        f"When you are finished, summarise what you did clearly — that summary "
        f"will be posted back to the GitHub {item_type} as a comment."
    )


# ── Core event processing ──────────────────────────────────────────────────────

def _ensure_conversation(
    agent_url: str,
    api_key: str,
    conversations: dict[str, dict],
    conv_key: str,
    issue_number: int,
    is_pr: bool,
    html_url: str,
    prompt: str,
    comment: dict,
    item_type: str,
) -> tuple[str, bool]:
    """Create a new conversation or re-open a closed one.

    Returns ``(conv_id, resumed)`` where *resumed* is True when an existing
    closed conversation was successfully re-activated.
    Raises on unrecoverable errors so the caller can log and skip.
    """
    existing = conversations.get(conv_key)

    if existing and existing.get("status") == "closed":
        conv_id = existing["conversation_id"]
        author = (comment.get("user") or {}).get("login", "?")
        body_text = (comment.get("body") or "").strip()
        try:
            send_to_conversation(
                agent_url, api_key, conv_id,
                f"New request on GitHub {item_type} #{issue_number} by @{author}:\n\n{body_text}",
            )
            existing["status"] = "active"
            existing["last_activity"] = time.time()
            print(f"  Re-opened closed conversation {conv_id}")
            return conv_id, True
        except Exception as exc:
            print(f"  Closed conversation {conv_id} unreachable ({exc}) — creating new")

    conv_id = create_conversation(agent_url, api_key, prompt)
    conversations[conv_key] = {
        "conversation_id": conv_id,
        "issue_number": issue_number,
        "issue_type": "pr" if is_pr else "issue",
        "html_url": html_url,
        "status": "active",
        "last_activity": time.time(),
    }
    print(f"  Created conversation {conv_id}")
    return conv_id, False


def _post_acknowledgement(
    github_token: str,
    repo: str,
    issue_number: int,
    item_type: str,
    conv_url: str,
    resumed: bool,
) -> None:
    """Post an acknowledgement comment on the GitHub issue or PR."""
    if resumed:
        body = (
            f"🤖 **OpenHands is resuming work on this {item_type}.**\n\n"
            f"Picking up the existing conversation: {conv_url}\n\n"
            f"_This comment was posted by an AI agent (OpenHands) "
            f"in response to a '{TRIGGER_PHRASE}' mention._"
        )
    else:
        body = (
            f"🤖 **OpenHands is on it!**\n\n"
            f"I've started working on this {item_type}. "
            f"View the conversation here: {conv_url}\n\n"
            f"_This comment was posted by an AI agent (OpenHands) "
            f"in response to a '{TRIGGER_PHRASE}' mention._"
        )
    _post_github_comment(github_token, repo, issue_number, body)


def _process_trigger_comment(
    github_token: str,
    agent_url: str,
    api_key: str,
    openhands_url: str,
    repo: str,
    issue_number: int,
    comment: dict,
    event_type: str,
    conversations: dict[str, dict],
) -> None:
    """Handle a new trigger comment: create or resume a conversation."""
    conv_key = str(issue_number)
    print(f"  Trigger detected on #{issue_number} (comment {comment.get('id')})")

    # Fetch full issue/PR context.
    try:
        ctx = _get_issue_context(github_token, repo, issue_number)
    except Exception as exc:
        print(f"  Error fetching context for #{issue_number}: {exc}")
        return

    is_pr = ctx["is_pr"]
    item_type = "pull request" if is_pr else "issue"
    html_url = ctx["issue"].get("html_url", f"https://github.com/{repo}/issues/{issue_number}")

    existing = conversations.get(conv_key)

    # ── Case A: active conversation — forward the new comment ─────────────────
    if existing and existing.get("status") == "active":
        conv_id = existing["conversation_id"]
        print(f"  Forwarding to active conversation {conv_id}")
        author = comment.get("user", {}).get("login", "?")
        body = (comment.get("body") or "").strip()
        try:
            send_to_conversation(
                agent_url, api_key, conv_id,
                f"New comment on GitHub {item_type} #{issue_number} by @{author}:\n\n{body}",
            )
            existing["last_activity"] = time.time()
            return
        except Exception as exc:
            print(f"  Warning: could not forward to conversation {conv_id}: {exc} — creating new")
            # Fall through to create a new conversation.

    # ── Case B: closed or missing — create / re-open via helper ──────────────
    prompt = _build_initial_prompt(ctx, comment, event_type)
    try:
        conv_id, resumed = _ensure_conversation(
            agent_url, api_key, conversations, conv_key,
            issue_number, is_pr, html_url, prompt, comment, item_type,
        )
    except Exception as exc:
        print(f"  Error creating conversation for #{issue_number}: {exc}")
        return

    conv_url = f"{openhands_url}/conversations/{conv_id}"
    _post_acknowledgement(github_token, repo, issue_number, item_type, conv_url, resumed)


def _check_conversation_completion(
    conv_key: str,
    rec: dict,
    github_token: str,
    repo: str,
    agent_url: str,
    api_key: str,
) -> None:
    """Post a summary GitHub comment when a conversation reaches a terminal state."""
    if (time.time() - rec.get("last_activity", 0.0)) < DONE_DEBOUNCE:
        return

    conv_id = rec["conversation_id"]
    issue_number = rec["issue_number"]
    item_type = rec.get("issue_type", "issue")
    item_label = "pull request" if item_type == "pr" else "issue"

    try:
        status = conversation_status(agent_url, api_key, conv_id)
    except Exception as exc:
        print(f"  Warning: could not get status for {conv_id}: {exc}")
        return

    print(f"  #{issue_number} conversation {conv_id} → status={status}")

    if status not in ("idle", "finished", "error", "stuck"):
        return

    try:
        final = conversation_final_response(agent_url, api_key, conv_id)
    except Exception:
        final = ""

    if status in ("error", "stuck"):
        comment_body = (
            f"⚠️ **OpenHands encountered a problem** (status: `{status}`).\n\n"
            + (f"{final}\n\n" if final else "")
            + f"_This message was posted by an AI agent (OpenHands)._"
        )
    else:
        comment_body = (
            (f"✅ **OpenHands completed the task:**\n\n{final}\n\n" if final
             else f"✅ **OpenHands completed the task.** (No summary available.)\n\n")
            + f"_This summary was generated by an AI agent (OpenHands) "
            f"working on {item_label} #{issue_number}._"
        )

    _post_github_comment(github_token, repo, issue_number, comment_body)
    rec["status"] = "closed"
    print(f"  Posted summary for #{issue_number}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    state_path = _state_file_path()
    state = load_state(state_path)

    agent_url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    api_key = _get_env_key()

    github_token = _resolve_github_token()
    _verify_token_and_repo(github_token, REPO)

    try:
        openhands_url = get_secret("OPENHANDS_URL").rstrip("/") or DEFAULT_OPENHANDS_URL
    except Exception:
        openhands_url = DEFAULT_OPENHANDS_URL

    since = state.get("last_poll") or _default_since()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["last_poll"] = now_iso  # advance before processing so next run doesn't miss events

    conversations: dict[str, dict] = state.get("conversations", {})
    processed_ids: list[int] = state.get("processed_comment_ids", [])
    processed_set: set[int] = set(processed_ids)

    print(f"Polling {REPO} since {since}  (trigger: '{TRIGGER_PHRASE}'  types: {EVENT_TYPES})")

    # ── Collect new events ─────────────────────────────────────────────────────
    all_events: list[tuple[str, dict]] = []  # (event_type, comment)

    if "issue_comment" in EVENT_TYPES:
        try:
            comments = _poll_issue_comments(github_token, REPO, since)
            print(f"  issue_comment: {len(comments)} new comment(s)")
            for c in comments:
                all_events.append(("issue_comment", c))
        except Exception as exc:
            print(f"  Warning: could not poll issue comments: {exc}")

    if "pr_review_comment" in EVENT_TYPES:
        try:
            review_comments = _poll_pr_review_comments(github_token, REPO, since)
            print(f"  pr_review_comment: {len(review_comments)} new comment(s)")
            for c in review_comments:
                all_events.append(("pr_review_comment", c))
        except Exception as exc:
            print(f"  Warning: could not poll PR review comments: {exc}")

    # Sort all events by creation time so they are processed chronologically.
    all_events.sort(key=lambda x: x[1].get("created_at", ""))

    # ── Process trigger events ─────────────────────────────────────────────────
    for event_type, comment in all_events:
        comment_id: int = comment.get("id", 0)
        if comment_id in processed_set:
            continue

        if _is_bot_comment(comment):
            processed_set.add(comment_id)
            continue

        if not _has_trigger(comment, TRIGGER_PHRASE):
            processed_set.add(comment_id)
            continue

        issue_number = _extract_issue_number(comment, event_type)
        if issue_number is None:
            print(f"  Could not extract issue number from comment {comment_id} — skipping")
            processed_set.add(comment_id)
            continue

        _process_trigger_comment(
            github_token, agent_url, api_key, openhands_url,
            REPO, issue_number, comment, event_type, conversations,
        )
        processed_set.add(comment_id)

    # ── Check active conversations for completion ──────────────────────────────
    for conv_key, rec in list(conversations.items()):
        if rec.get("status") != "active":
            continue
        _check_conversation_completion(
            conv_key, rec, github_token, REPO, agent_url, api_key,
        )

    # Trim processed_ids rolling window.
    trimmed = sorted(processed_set)
    if len(trimmed) > MAX_PROCESSED_IDS:
        trimmed = trimmed[-MAX_PROCESSED_IDS:]
    state["processed_comment_ids"] = trimmed
    state["conversations"] = conversations

    save_state(state_path, state)
    print(f"State saved → {state_path}")


if __name__ == "__main__":
    try:
        main()
        fire_callback("COMPLETED")
    except Exception as exc:
        import traceback
        traceback.print_exc()
        fire_callback("FAILED", str(exc))
        sys.exit(1)
