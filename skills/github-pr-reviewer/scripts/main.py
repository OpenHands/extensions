"""
GitHub Code Review Agent  -  OpenHands Automation Script

Polls a set of GitHub repositories on a fixed cron schedule (every 5 minutes).
For each open pull request that has not already been reviewed at its current
HEAD commit, it:

  1. Creates an OpenHands conversation pre-loaded with the PR metadata and
     instructions to perform a code review and post it back to GitHub.
  2. Posts a GitHub comment on the PR acknowledging that a review is in
     progress, with a link to the conversation.
  3. Records the PR's HEAD SHA so the same commit is never reviewed twice.

A PR is re-reviewed when its author pushes a new commit (i.e. the HEAD SHA
changes since the last recorded review).

Configuration constants are embedded at automation-creation time by the skill.
See SKILL.md for the full setup workflow.

Required secrets (set in OpenHands Settings → Secrets):
  GITHUB_PERSONAL_ACCESS_TOKEN  - Personal Access Token
                  Classic PAT:       'repo' scope (private) or 'public_repo' (public)
                  Fine-grained PAT:  Pull Requests: Read and Write

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
from datetime import datetime, timezone
from urllib.parse import urlencode

# ── Embedded configuration (filled in by the skill at creation time) ──────────
REPOS = ["owner/repo"]              # e.g. ["myorg/backend", "myorg/frontend"]
LABEL_FILTER = ""                   # only review PRs with this label; empty = all
SKIP_DRAFTS = True                  # skip draft PRs
REVIEW_TONE = "balanced"            # "balanced" | "roasted"
DEFAULT_OPENHANDS_URL = "http://localhost:8000"


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
    """Derive a persistent storage path from WORKSPACE_BASE."""
    workspace_base = os.environ.get("WORKSPACE_BASE", "")
    event_payload = json.loads(os.environ.get("AUTOMATION_EVENT_PAYLOAD", "{}"))
    automation_id = event_payload.get("automation_id", "default")

    if workspace_base:
        root = Path(workspace_base).resolve().parent.parent
    else:
        root = Path.home() / ".openhands" / "workspaces"

    state_dir = root / "automation-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return str(state_dir / f"pr_reviewer_{automation_id}.json")


def load_state(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: state file {path} unreadable ({exc}); starting fresh")
    return {
        "version": 1,
        "repos": REPOS,
        # reviewed[repo][str(pr_number)] = {head_sha, conversation_id, reviewed_at}
        "reviewed": {},
    }


def save_state(path: str, state: dict) -> None:
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def _pr_state(state: dict, repo: str, pr_number: int) -> dict | None:
    return state.get("reviewed", {}).get(repo, {}).get(str(pr_number))


def _set_pr_state(
    state: dict,
    repo: str,
    pr_number: int,
    head_sha: str,
    conversation_id: str,
) -> None:
    state.setdefault("reviewed", {}).setdefault(repo, {})[str(pr_number)] = {
        "head_sha": head_sha,
        "conversation_id": conversation_id,
        "reviewed_at": time.time(),
    }


# ── GitHub API helpers ─────────────────────────────────────────────────────────

def _github_request(
    token: str,
    method: str,
    path: str,
    params: dict | None = None,
    body: dict | None = None,
) -> tuple[dict | list, dict]:
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


def _verify_token(token: str) -> str:
    """Verify the token is valid. Returns the authenticated GitHub username."""
    try:
        user_data, user_headers = _github_request(token, "GET", "/user")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError(
                "GITHUB_PERSONAL_ACCESS_TOKEN is invalid or expired. "
                "Update it in OpenHands Settings → Secrets."
            )
        raise RuntimeError(f"GitHub /user check failed: {exc.code}")
    username: str = user_data.get("login", "?")
    scopes_header: str = user_headers.get("X-OAuth-Scopes", "") or ""
    scopes = {s.strip() for s in scopes_header.split(",") if s.strip()}
    print(f"Authenticated as: {username}  scopes: {scopes or '(fine-grained PAT)'}")
    return username


def _get_open_prs(token: str, repo: str) -> list[dict]:
    """Fetch all open pull requests for a repository."""
    return _github_paginate(
        token,
        f"/repos/{repo}/pulls",
        {"state": "open", "sort": "updated", "direction": "desc"},
    )


def _pr_has_label(pr: dict, label: str) -> bool:
    return any(
        lbl.get("name", "").lower() == label.lower()
        for lbl in pr.get("labels", [])
    )


def _post_github_comment(token: str, repo: str, pr_number: int, body: str) -> None:
    try:
        _github_request(
            token,
            "POST",
            f"/repos/{repo}/issues/{pr_number}/comments",
            body={"body": body},
        )
    except Exception as exc:
        print(f"  Warning: failed to post GitHub comment on PR #{pr_number}: {exc}")


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
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GET /api/settings failed: {exc.code}") from exc


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
        agent_settings = data.get("agent_settings", {})
        mcp_config = agent_settings.get("mcp_config")
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
    if not secrets_list:
        return {}
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


# ── Review prompt builder ──────────────────────────────────────────────────────

def _tone_instruction(tone: str) -> str:
    if tone == "roasted":
        return (
            "Be critical and direct. Point out every flaw, no matter how small. "
            "Use a frank, unsparing tone — the author wants honest, unfiltered feedback."
        )
    return (
        "Be balanced and constructive. Highlight both strengths and areas for improvement. "
        "Keep feedback actionable and respectful."
    )


def _build_review_prompt(
    repo: str,
    pr: dict,
    tone: str,
    label_filter: str,
    openhands_url: str,
) -> str:
    pr_number = pr["number"]
    pr_title = pr.get("title", "")
    pr_body = (pr.get("body") or "").strip()
    pr_html_url = pr.get("html_url", f"https://github.com/{repo}/pull/{pr_number}")
    head_sha = pr["head"]["sha"]
    base_branch = pr["base"]["ref"]
    head_branch = pr["head"]["ref"]
    author = (pr.get("user") or {}).get("login", "unknown")
    label_note = (
        f"\nThis PR carries the `{label_filter}` label that triggered this review."
        if label_filter
        else ""
    )

    return f"""You are performing an automated code review for a GitHub pull request.

Repository: {repo}
PR #{pr_number}: {pr_title}
Author: @{author}
Base branch: {base_branch}  ←  Head branch: {head_branch}
Head commit: {head_sha}
PR URL: {pr_html_url}{label_note}

PR description:
{pr_body or "(no description provided)"}

---

INSTRUCTIONS — follow these steps in order:

1. Fetch the list of changed files and their diffs:
   ```bash
   curl -s "https://api.github.com/repos/{repo}/pulls/{pr_number}/files" \\
     -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \\
     -H "Accept: application/vnd.github+json"
   ```

2. Fetch the PR commits for context:
   ```bash
   curl -s "https://api.github.com/repos/{repo}/pulls/{pr_number}/commits" \\
     -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \\
     -H "Accept: application/vnd.github+json"
   ```

3. Review the changes. Focus on:
   - Correctness: logic errors, off-by-one errors, unhandled edge cases
   - Security: injection risks, unsafe deserialization, credential exposure
   - Tests: missing or inadequate coverage for changed behaviour
   - Maintainability: overly complex code, poor naming, missing documentation

   Tone: {_tone_instruction(tone)}

4. Post the review to GitHub as a single API call using the /github-pr-review skill.
   - Use commit_id: {head_sha}
   - Bundle ALL inline comments into one review (never post them individually).
   - Include a brief overall summary in the top-level `body` field.

5. After posting the review, output a single line:
   REVIEW_COMPLETE: {pr_html_url}
"""


# ── Main polling loop ──────────────────────────────────────────────────────────

def review_new_prs(
    token: str,
    state: dict,
    agent_url: str,
    api_key: str,
    openhands_url: str,
) -> int:
    """Poll all configured repos and create review conversations for new/updated PRs.

    Returns the number of review conversations started.
    """
    started = 0

    for repo in REPOS:
        print(f"\nPolling {repo} for open PRs …")
        try:
            open_prs = _get_open_prs(token, repo)
        except Exception as exc:
            print(f"  Error fetching PRs for {repo}: {exc}")
            continue

        print(f"  Found {len(open_prs)} open PR(s)")

        for pr in open_prs:
            pr_number = pr["number"]
            head_sha = pr["head"]["sha"]
            pr_title = pr.get("title", f"PR #{pr_number}")
            is_draft = pr.get("draft", False)

            # Apply filters.
            if SKIP_DRAFTS and is_draft:
                print(f"  Skipping draft PR #{pr_number}: {pr_title}")
                continue

            if LABEL_FILTER and not _pr_has_label(pr, LABEL_FILTER):
                print(
                    f"  Skipping PR #{pr_number} (no '{LABEL_FILTER}' label): {pr_title}"
                )
                continue

            # Check if this exact commit has already been reviewed.
            existing = _pr_state(state, repo, pr_number)
            if existing and existing.get("head_sha") == head_sha:
                print(
                    f"  PR #{pr_number} already reviewed at {head_sha[:7]} — skipping"
                )
                continue

            print(f"  → Queuing review for PR #{pr_number}: {pr_title} ({head_sha[:7]})")

            prompt = _build_review_prompt(repo, pr, REVIEW_TONE, LABEL_FILTER, openhands_url)

            try:
                conv_id = create_conversation(agent_url, api_key, prompt)
            except Exception as exc:
                print(f"    Error creating conversation: {exc}")
                continue

            pr_html_url = pr.get(
                "html_url", f"https://github.com/{repo}/pull/{pr_number}"
            )
            conv_url = f"{openhands_url.rstrip('/')}/conversations/{conv_id}"
            comment_body = (
                f"🤖 **OpenHands Code Review in progress** — "
                f"[View conversation]({conv_url})\n\n"
                f"Reviewing commit {head_sha[:7]}. "
                f"A review will be posted when complete."
            )
            _post_github_comment(token, repo, pr_number, comment_body)

            _set_pr_state(state, repo, pr_number, head_sha, conv_id)
            print(f"    Conversation {conv_id} started. GitHub comment posted.")
            started += 1

    return started


def main() -> None:
    agent_url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    api_key = _get_env_key()

    if not agent_url:
        print("ERROR: AGENT_SERVER_URL is not set.", file=sys.stderr)
        fire_callback("FAILED", error="AGENT_SERVER_URL not set")
        sys.exit(1)

    state_path = _state_file_path()
    state = load_state(state_path)

    token = None
    try:
        token = _resolve_github_token()
        _verify_token(token)
    except RuntimeError as exc:
        msg = str(exc)
        print(f"ERROR: {msg}", file=sys.stderr)
        fire_callback("FAILED", error=msg)
        sys.exit(1)

    openhands_url = DEFAULT_OPENHANDS_URL
    try:
        openhands_url = get_secret("OPENHANDS_URL") or DEFAULT_OPENHANDS_URL
    except Exception:
        pass  # optional secret — fall back to default

    print(
        f"GitHub Code Review Agent starting.\n"
        f"  Repos:        {', '.join(REPOS)}\n"
        f"  Label filter: {LABEL_FILTER or '(none)'}\n"
        f"  Skip drafts:  {SKIP_DRAFTS}\n"
        f"  Review tone:  {REVIEW_TONE}\n"
        f"  State file:   {state_path}\n"
        f"  OpenHands UI: {openhands_url}"
    )

    started = review_new_prs(token, state, agent_url, api_key, openhands_url)
    save_state(state_path, state)

    print(f"\nDone. {started} review conversation(s) started.")
    fire_callback("COMPLETED")


if __name__ == "__main__":
    main()
