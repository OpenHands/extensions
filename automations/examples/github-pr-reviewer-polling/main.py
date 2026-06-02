"""
GitHub PR reviewer polling example - OpenHands automation script.

This example demonstrates the intended local-polling shape:
  1. Poll GitHub with normal HTTP requests.
  2. Compare results against persisted state.
  3. Exit after the completion callback when there is nothing to review.
  4. Only create an OpenHands conversation after a PR passes the actionability gate.

Customize the constants below before packaging this as a custom automation.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = "owner/repo"
IGNORE_DRAFTS = True
REQUIRED_LABELS: list[str] = []  # Example: ["ready-for-ai-review"]
MAX_CONVERSATIONS_PER_RUN = 3
INITIAL_LOOKBACK_SECONDS = 300
DEFAULT_OPENHANDS_URL = "http://localhost:8000"


def _session_api_key() -> str:
    return os.environ.get("SESSION_API_KEY") or os.environ.get("OH_SESSION_API_KEYS_0") or ""


def _callback_api_key() -> str:
    return os.environ.get("AUTOMATION_CALLBACK_API_KEY") or os.environ.get("OPENHANDS_API_KEY", "")


def get_secret(name: str) -> str:
    """Fetch a named secret from the agent server."""
    agent_url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    req = urllib.request.Request(
        f"{agent_url}/api/settings/secrets/{name}",
        headers={"X-Session-API-Key": _session_api_key()},
    )
    with urllib.request.urlopen(req) as response:
        return response.read().decode().strip()


def fire_callback(status: str = "COMPLETED", error: str | None = None) -> None:
    """Signal run completion to the automation service."""
    callback_url = os.environ.get("AUTOMATION_CALLBACK_URL", "")
    if not callback_url:
        return
    body = {"status": status, "run_id": os.environ.get("AUTOMATION_RUN_ID", "")}
    if error:
        body["error"] = error
    req = urllib.request.Request(
        callback_url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_callback_api_key()}",
        },
    )
    try:
        urllib.request.urlopen(req)
    except Exception as exc:
        print(f"Callback error (non-fatal): {exc}")


def _state_file_path() -> Path:
    workspace_base = os.environ.get("WORKSPACE_BASE", "")
    event_payload = json.loads(os.environ.get("AUTOMATION_EVENT_PAYLOAD", "{}"))
    automation_id = event_payload.get("automation_id", "default")
    if workspace_base:
        root = Path(workspace_base).resolve().parent.parent
    else:
        root = Path.home() / ".openhands" / "workspaces"
    state_dir = root / "automation-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / f"github_pr_reviewer_{automation_id}.json"


def _default_since() -> str:
    return (
        datetime.now(timezone.utc) - timedelta(seconds=INITIAL_LOOKBACK_SECONDS)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(path: Path) -> dict:
    if path.exists():
        try:
            with path.open() as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: state file {path} unreadable ({exc}); starting fresh")
    return {
        "version": 1,
        "repo": REPO,
        "last_poll": _default_since(),
        "reviewed_heads": {},  # PR number string -> last head SHA handed to agent
        "started_conversations": {},  # PR number string -> latest conversation metadata
    }


def save_state(path: Path, state: dict) -> None:
    with path.open("w") as f:
        json.dump(state, f, indent=2)


def _github_request(
    token: str,
    method: str,
    path: str,
    params: dict | None = None,
    body: dict | None = None,
) -> tuple[dict | list, dict]:
    url = f"https://api.github.com{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as response:
        raw = response.read()
        return (json.loads(raw) if raw.strip() else {}), dict(response.headers)


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


def _parse_github_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _labels_for_pr(token: str, repo: str, pr_number: int) -> set[str]:
    issue, _ = _github_request(token, "GET", f"/repos/{repo}/issues/{pr_number}")
    return {label.get("name", "") for label in issue.get("labels", [])}


def _matches_label_filter(token: str, pr: dict) -> bool:
    if not REQUIRED_LABELS:
        return True
    labels = _labels_for_pr(token, REPO, pr["number"])
    return all(required in labels for required in REQUIRED_LABELS)


def _poll_actionable_prs(token: str, state: dict) -> list[dict]:
    """Return PRs that should start a review conversation.

    This is the important gate: it runs before any OpenHands conversation or LLM
    setup. If this returns an empty list, the automation exits without starting
    an agent conversation.
    """
    since = _parse_github_timestamp(state.get("last_poll") or _default_since())
    reviewed_heads = state.setdefault("reviewed_heads", {})
    prs = _github_paginate(
        token,
        f"/repos/{REPO}/pulls",
        {"state": "open", "sort": "updated", "direction": "asc"},
    )

    actionable = []
    for pr in prs:
        if _parse_github_timestamp(pr.get("updated_at", "1970-01-01T00:00:00Z")) <= since:
            continue
        if IGNORE_DRAFTS and pr.get("draft"):
            continue
        head_sha = pr.get("head", {}).get("sha", "")
        pr_key = str(pr.get("number"))
        if not head_sha or reviewed_heads.get(pr_key) == head_sha:
            continue
        if not _matches_label_filter(token, pr):
            continue
        actionable.append(pr)
        if len(actionable) >= MAX_CONVERSATIONS_PER_RUN:
            break
    return actionable


def _agent_request(
    agent_url: str,
    api_key: str,
    method: str,
    path: str,
    body: dict | None = None,
) -> dict:
    url = f"{agent_url}{path}"
    headers = {"X-Session-API-Key": api_key, "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            raw = response.read()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode()
        raise RuntimeError(f"Agent API {method} {path} -> {exc.code}: {body_text}") from exc


def _get_agent_dict(agent_url: str, api_key: str) -> dict:
    """Fetch configured LLM settings only after the polling gate finds work."""
    req = urllib.request.Request(
        f"{agent_url}/api/settings",
        headers={"X-Session-API-Key": api_key, "X-Expose-Secrets": "plaintext"},
    )
    with urllib.request.urlopen(req) as response:
        settings = json.loads(response.read())
    llm = settings.get("agent_settings", {}).get("llm", {})
    return {
        "kind": "Agent",
        "llm": llm,
        "tools": [{"name": "terminal"}, {"name": "file_editor"}],
    }


def create_conversation(agent_url: str, api_key: str, initial_message: str) -> str:
    """Create an OpenHands conversation and return its ID."""
    workspace_dir = os.environ.get("WORKSPACE_BASE", "/workspace")
    agent = _get_agent_dict(agent_url, api_key)
    result = _agent_request(
        agent_url,
        api_key,
        "POST",
        "/api/conversations",
        {
            "workspace": {"working_dir": workspace_dir},
            "agent": agent,
            "initial_message": {"content": [{"text": initial_message}]},
        },
    )
    return result["id"]


def _build_review_prompt(pr: dict) -> str:
    number = pr["number"]
    title = pr.get("title", "(no title)")
    html_url = pr.get("html_url", "")
    head_sha = pr.get("head", {}).get("sha", "")
    base_ref = pr.get("base", {}).get("ref", "")
    head_ref = pr.get("head", {}).get("ref", "")
    author = pr.get("user", {}).get("login", "?")
    return f"""Review this GitHub pull request.

Repository: {REPO}
PR #{number}: {title}
URL: {html_url}
Author: @{author}
Base: {base_ref}
Head: {head_ref}
Head SHA: {head_sha}

Use the GITHUB_TOKEN secret to fetch the diff, changed files, checks, and discussion.
Focus on correctness, security, missing tests, and concrete next steps. If you post a
review or comment back to GitHub, include a brief note that it was generated by an
AI agent (OpenHands) on behalf of the user.
"""


def main() -> None:
    state_path = _state_file_path()
    state = load_state(state_path)
    state["repo"] = REPO

    github_token = get_secret("GITHUB_TOKEN")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"Polling {REPO} for PRs updated since {state.get('last_poll')}")

    actionable_prs = _poll_actionable_prs(github_token, state)
    if not actionable_prs:
        state["last_poll"] = now_iso
        save_state(state_path, state)
        print("No actionable PRs found; exiting without starting a conversation")
        return

    agent_url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    api_key = _session_api_key()
    openhands_url = DEFAULT_OPENHANDS_URL
    try:
        openhands_url = get_secret("OPENHANDS_URL").rstrip("/") or DEFAULT_OPENHANDS_URL
    except Exception:
        pass

    for pr in actionable_prs:
        pr_key = str(pr["number"])
        head_sha = pr.get("head", {}).get("sha", "")
        prompt = _build_review_prompt(pr)
        conv_id = create_conversation(agent_url, api_key, prompt)
        state.setdefault("reviewed_heads", {})[pr_key] = head_sha
        state.setdefault("started_conversations", {})[pr_key] = {
            "conversation_id": conv_id,
            "head_sha": head_sha,
            "pr_url": pr.get("html_url", ""),
            "conversation_url": f"{openhands_url}/conversations/{conv_id}",
            "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        print(f"Started review conversation {conv_id} for PR #{pr_key}")

    state["last_poll"] = now_iso
    save_state(state_path, state)


if __name__ == "__main__":
    try:
        main()
        fire_callback("COMPLETED")
    except Exception as exc:
        import traceback
        traceback.print_exc()
        fire_callback("FAILED", str(exc))
        sys.exit(1)
