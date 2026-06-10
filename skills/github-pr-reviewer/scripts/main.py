"""
GitHub PR Reviewer  -  OpenHands Automation Script

Polls a GitHub repository on a cron schedule. For each open pull request
that has not yet been reviewed it:
  1. Fetches the PR metadata and diff.
  2. Creates an OpenHands conversation with a targeted review prompt.
  3. When the conversation completes, posts the AI review as a GitHub comment.

On subsequent runs:
  - Already-reviewed PRs are skipped (tracked in the state file).
  - Active conversations are checked for completion and results posted.

Configuration constants are embedded at automation-creation time by the skill.
See SKILL.md for the full setup workflow.

Required secret (set in OpenHands Settings → Secrets):
  GITHUB_PERSONAL_ACCESS_TOKEN  - Personal Access Token
                  Classic PAT:       'repo' scope (private) or 'public_repo' (public)
                  Fine-grained PAT:  Pull requests: Read and Write

Optional secret:
  OPENHANDS_URL - base URL for conversation links (default: http://localhost:8000)
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

# ── Embedded configuration (filled in by the skill at creation time) ──────────
REPO = "owner/repo"           # e.g. "myorg/backend"
REVIEW_TONE = "thorough"      # "thorough" | "concise" | "friendly"
REVIEW_STYLE_INSTRUCTIONS = ""  # extra free-form persona / style notes
DEFAULT_OPENHANDS_URL = "http://localhost:8000"

# Max diff lines to include in the review prompt (avoids token overrun).
MAX_DIFF_LINES = 500

# PRs whose diff exceeds this many lines are skipped with an explanatory comment.
MAX_DIFF_LINES_SKIP = 5000

# Prevent posting summaries in the same run that created the conversation.
DONE_DEBOUNCE = 15


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


def fire_callback(
    status: str = "COMPLETED",
    error: str | None = None,
    conversation_id: str | None = None,
) -> None:
    """Signal run completion to the automation service."""
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
    return str(state_dir / f"github_pr_reviewer_{automation_id}.json")


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
        "conversations": {},  # pr_number (str) → ConversationRecord
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
    accept: str = "application/vnd.github+json",
) -> tuple:
    """Low-level GitHub API call. Returns (parsed_body, response_headers)."""
    base = "https://api.github.com"
    url = f"{base}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as r:
        resp_headers = dict(r.headers)
        raw = r.read()
        if accept == "application/vnd.github.diff":
            return raw.decode("utf-8", errors="replace"), resp_headers
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
    try:
        token = get_secret("GITHUB_PERSONAL_ACCESS_TOKEN")
        if token:
            return token
    except Exception:
        pass
    raise RuntimeError(
        "GITHUB_PERSONAL_ACCESS_TOKEN secret is not set. "
        "Go to OpenHands Settings → Secrets and add your GitHub Personal Access Token."
    )


def _verify_token_and_repo(token: str, repo: str) -> str:
    """Verify token validity and repo access. Returns the authenticated GitHub username."""
    try:
        user_data, _ = _github_request(token, "GET", "/user")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError(
                "GITHUB_PERSONAL_ACCESS_TOKEN is invalid or expired. "
                "Update it in OpenHands Settings → Secrets."
            )
        raise RuntimeError(f"GitHub /user check failed: {exc.code}")

    username: str = user_data.get("login", "?")
    print(f"Authenticated as GitHub user: {username}")

    try:
        _github_request(token, "GET", f"/repos/{repo}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError(
                f"Repository '{repo}' not found or not accessible with the current token."
            )
        raise RuntimeError(f"GitHub /repos/{repo} check failed: {exc.code}")

    print(f"Repository '{repo}' accessible.")
    return username


def _list_open_prs(token: str, repo: str) -> list[dict]:
    """Fetch all open pull requests, oldest first."""
    return _github_paginate(
        token,
        f"/repos/{repo}/pulls",
        {"state": "open", "sort": "created", "direction": "asc"},
    )


def _get_pr_diff(token: str, repo: str, pr_number: int) -> str:
    """Fetch the unified diff for a pull request."""
    diff, _ = _github_request(
        token, "GET", f"/repos/{repo}/pulls/{pr_number}",
        accept="application/vnd.github.diff",
    )
    return diff


def _post_github_comment(token: str, repo: str, pr_number: int, body: str) -> None:
    """Post a comment on a pull request."""
    try:
        _github_request(
            token, "POST",
            f"/repos/{repo}/issues/{pr_number}/comments",
            body={"body": body},
        )
    except Exception as exc:
        print(f"  Warning: failed to post comment on PR #{pr_number}: {exc}")


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


def _fetch_settings(agent_url: str, api_key: str) -> dict:
    url = f"{agent_url}/api/settings"
    headers = {"X-Session-API-Key": api_key, "X-Expose-Secrets": "plaintext"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def _get_agent_dict(agent_url: str, api_key: str) -> dict:
    data = _fetch_settings(agent_url, api_key)
    agent_settings = data.get("agent_settings", {})
    llm = agent_settings.get("llm", {})
    return {
        "kind": "Agent",
        "llm": llm,
        "tools": [{"name": "terminal"}, {"name": "file_editor"}],
    }


def _get_mcp_config(agent_url: str, api_key: str) -> dict | None:
    try:
        data = _fetch_settings(agent_url, api_key)
        mcp_config = data.get("agent_settings", {}).get("mcp_config")
        if isinstance(mcp_config, dict) and mcp_config.get("mcpServers"):
            return mcp_config
    except Exception as exc:
        print(f"Warning: could not fetch MCP config: {exc}")
    return None


def _list_secret_names(agent_url: str, api_key: str) -> list[dict]:
    try:
        result = _oh_request(agent_url, api_key, "GET", "/api/settings/secrets")
        return result.get("secrets", [])
    except Exception as exc:
        print(f"Warning: could not list secrets: {exc}")
        return []


def _build_secrets_payload(agent_url: str, api_key: str) -> dict:
    secrets_list = _list_secret_names(agent_url, api_key)
    secrets: dict = {}
    for secret in secrets_list:
        name = secret.get("name", "")
        if not name:
            continue
        lookup: dict = {
            "kind": "LookupSecret",
            "url": f"/api/settings/secrets/{name}",
        }
        if api_key:
            lookup["headers"] = {"X-Session-API-Key": api_key}
        desc = secret.get("description")
        if desc:
            lookup["description"] = desc
        secrets[name] = lookup
    return secrets


def create_conversation(agent_url: str, api_key: str, initial_message: str) -> str:
    """Create an OpenHands conversation and return its ID."""
    workspace_dir = os.environ.get("WORKSPACE_BASE", "/workspace")
    agent = _get_agent_dict(agent_url, api_key)
    payload: dict = {
        "workspace": {"working_dir": workspace_dir},
        "agent": agent,
        "initial_message": {"content": [{"text": initial_message}]},
    }
    secrets = _build_secrets_payload(agent_url, api_key)
    if secrets:
        payload["secrets"] = secrets
    mcp_config = _get_mcp_config(agent_url, api_key)
    if mcp_config:
        payload["mcp_config"] = mcp_config
    result = _oh_request(agent_url, api_key, "POST", "/api/conversations", payload)
    return result["id"]


def conversation_status(agent_url: str, api_key: str, conv_id: str) -> str:
    result = _oh_request(agent_url, api_key, "GET", f"/api/conversations/{conv_id}")
    return result.get("execution_status", "unknown")


def conversation_final_response(agent_url: str, api_key: str, conv_id: str) -> str:
    result = _oh_request(
        agent_url, api_key, "GET",
        f"/api/conversations/{conv_id}/agent_final_response",
    )
    return result.get("response", "")


# ── Prompt building ────────────────────────────────────────────────────────────

_TONE_INSTRUCTIONS: dict[str, str] = {
    "thorough": (
        "Provide a comprehensive review. Cover correctness, security vulnerabilities, "
        "missing or inadequate tests, code style, maintainability, and potential edge "
        "cases. Reference specific files and line numbers where relevant."
    ),
    "concise": (
        "Provide a brief, high-signal review. Focus only on the most important issues — "
        "bugs, security problems, or significant design flaws. Omit minor style feedback."
    ),
    "friendly": (
        "Provide a constructive, encouraging review. Acknowledge what is done well before "
        "raising concerns. Be positive and supportive while still noting real issues."
    ),
}


def _build_review_prompt(pr: dict, diff: str, diff_truncated: bool) -> str:
    number = pr.get("number", "?")
    title = pr.get("title", "(no title)")
    body = (pr.get("body") or "").strip() or "(no description)"
    html_url = pr.get("html_url", "")
    author = (pr.get("user") or {}).get("login", "?")
    base_branch = (pr.get("base") or {}).get("ref", "?")
    head_branch = (pr.get("head") or {}).get("ref", "?")
    labels = [lb["name"] for lb in (pr.get("labels") or [])]
    label_str = ", ".join(labels) if labels else "(none)"
    changed_files = pr.get("changed_files", "?")
    additions = pr.get("additions", "?")
    deletions = pr.get("deletions", "?")

    tone = _TONE_INSTRUCTIONS.get(REVIEW_TONE, _TONE_INSTRUCTIONS["thorough"])
    extra = (
        f"\n\nAdditional style instructions:\n{REVIEW_STYLE_INSTRUCTIONS}"
        if REVIEW_STYLE_INSTRUCTIONS.strip()
        else ""
    )
    truncation_note = (
        f"\n\n⚠️  The diff below has been truncated to the first {MAX_DIFF_LINES} lines. "
        "Review what is available and note that the full diff is larger."
    ) if diff_truncated else ""

    return (
        f"You are an AI code reviewer. Review the following GitHub pull request "
        f"and write a review comment.\n\n"
        f"Repository : {REPO}\n"
        f"PR #{number}: \"{title}\"\n"
        f"Author     : @{author}\n"
        f"Base → Head: {base_branch} ← {head_branch}\n"
        f"Labels     : {label_str}\n"
        f"Changes    : +{additions} -{deletions} across {changed_files} file(s)\n"
        f"URL        : {html_url}\n"
        f"\nPR Description:\n---\n{body}\n---\n"
        f"{truncation_note}"
        f"\nDiff:\n```diff\n{diff}\n```\n"
        f"\nReview instructions:\n{tone}{extra}\n\n"
        f"Output ONLY the review text — no preamble, no meta-commentary. "
        f"This text will be posted verbatim as a comment on the pull request.\n"
        f"End your review with a clear verdict on its own line: "
        f"either `✅ APPROVED` or `🔄 CHANGES REQUESTED`."
    )


# ── Core logic ─────────────────────────────────────────────────────────────────

def _process_new_pr(
    github_token: str,
    agent_url: str,
    api_key: str,
    openhands_url: str,
    pr: dict,
    conversations: dict,
) -> str | None:
    """Start a review conversation for a PR not yet seen. Returns the conversation ID."""
    number = pr["number"]
    title = pr.get("title", "(no title)")
    html_url = pr.get("html_url", "")
    print(f"  New PR #{number}: \"{title}\"")

    try:
        diff = _get_pr_diff(github_token, REPO, number)
    except Exception as exc:
        print(f"  Warning: could not fetch diff for PR #{number}: {exc}")
        return None

    diff_lines = diff.splitlines()

    if len(diff_lines) > MAX_DIFF_LINES_SKIP:
        print(f"  Skipping PR #{number}: diff too large ({len(diff_lines)} lines)")
        conversations[str(number)] = {
            "pr_number": number,
            "html_url": html_url,
            "status": "skipped",
            "reason": f"diff too large ({len(diff_lines)} lines)",
            "last_activity": time.time(),
        }
        _post_github_comment(
            github_token, REPO, number,
            f"⚠️ **OpenHands PR Reviewer**: This PR's diff is too large to review "
            f"automatically ({len(diff_lines):,} lines). Consider splitting it into "
            f"smaller PRs.\n\n_This message was posted by an AI agent (OpenHands)._",
        )
        return None

    diff_truncated = len(diff_lines) > MAX_DIFF_LINES
    if diff_truncated:
        diff = "\n".join(diff_lines[:MAX_DIFF_LINES])

    prompt = _build_review_prompt(pr, diff, diff_truncated)

    try:
        conv_id = create_conversation(agent_url, api_key, prompt)
    except Exception as exc:
        print(f"  Error creating conversation for PR #{number}: {exc}")
        return None

    conversations[str(number)] = {
        "pr_number": number,
        "html_url": html_url,
        "status": "active",
        "conversation_id": conv_id,
        "last_activity": time.time(),
    }
    print(f"  Created review conversation {conv_id}")

    conv_url = f"{openhands_url}/conversations/{conv_id}"
    _post_github_comment(
        github_token, REPO, number,
        f"🤖 **OpenHands is reviewing this PR.**\n\n"
        f"View the conversation: {conv_url}\n\n"
        f"_This comment was posted by an AI agent (OpenHands)._",
    )
    return conv_id


def _check_conversation_completion(
    rec: dict,
    github_token: str,
    agent_url: str,
    api_key: str,
) -> None:
    """Post the review result and close the conversation record once it finishes."""
    if (time.time() - rec.get("last_activity", 0.0)) < DONE_DEBOUNCE:
        return

    conv_id = rec["conversation_id"]
    pr_number = rec["pr_number"]

    try:
        status = conversation_status(agent_url, api_key, conv_id)
    except Exception as exc:
        print(f"  Warning: could not get status for {conv_id}: {exc}")
        return

    print(f"  PR #{pr_number} conversation {conv_id} → status={status}")

    if status not in ("idle", "finished", "error", "stuck"):
        return

    try:
        final = conversation_final_response(agent_url, api_key, conv_id)
    except Exception:
        final = ""

    if status in ("error", "stuck"):
        comment_body = (
            f"⚠️ **OpenHands PR Reviewer encountered a problem** (status: `{status}`).\n\n"
            + (f"{final}\n\n" if final else "")
            + "_This message was posted by an AI agent (OpenHands)._"
        )
    else:
        comment_body = (
            final if final
            else (
                "✅ **OpenHands completed the review.** (No review text was produced.)\n\n"
                "_This message was posted by an AI agent (OpenHands)._"
            )
        )

    _post_github_comment(github_token, REPO, pr_number, comment_body)
    rec["status"] = "closed"
    print(f"  Posted review for PR #{pr_number}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> str | None:
    """Run one polling cycle. Returns the last conversation ID created, if any."""
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

    conversations: dict = state.get("conversations", {})

    try:
        open_prs = _list_open_prs(github_token, REPO)
    except Exception as exc:
        raise RuntimeError(f"Failed to list open PRs for {REPO}: {exc}") from exc

    print(f"Found {len(open_prs)} open PR(s) in {REPO}")

    open_pr_numbers = {str(pr["number"]) for pr in open_prs}

    last_conversation_id: str | None = None

    # Queue reviews for PRs not yet in state.
    for pr in open_prs:
        key = str(pr["number"])
        if key in conversations:
            continue
        conv_id = _process_new_pr(
            github_token, agent_url, api_key, openhands_url, pr, conversations,
        )
        if conv_id:
            last_conversation_id = conv_id

    # Check active conversations for completion.
    for key, rec in list(conversations.items()):
        if rec.get("status") != "active":
            continue
        if key not in open_pr_numbers:
            # PR was closed/merged before review completed — mark closed silently.
            rec["status"] = "closed"
            print(f"  PR #{rec.get('pr_number')} closed/merged — skipping result post")
            continue
        _check_conversation_completion(rec, github_token, agent_url, api_key)

    state["conversations"] = conversations
    save_state(state_path, state)
    print(f"State saved → {state_path}")
    return last_conversation_id


if __name__ == "__main__":
    try:
        conversation_id = main()
        fire_callback("COMPLETED", conversation_id=conversation_id)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        fire_callback("FAILED", str(exc))
        sys.exit(1)
