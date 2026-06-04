#!/usr/bin/env python3
"""
GitHub PR Review Polling Automation

Polls a GitHub repository every 5 minutes for open pull requests that carry a
specific label and were created since the previous automation run.  For each
matching PR a new OpenHands conversation is started that performs a code review
using the configured skill.

Required secret (set in OpenHands Settings -> Secrets):
  GITHUB_PERSONAL_ACCESS_TOKEN  - Classic or fine-grained PAT
                                   Classic scope:       repo (private) / public_repo (public)
                                   Fine-grained scope:  Pull requests: Read and Write

Behaviour on first run:
  Records the current timestamp as the baseline and exits cleanly (exit code 0).
  No PRs are reviewed on the first run - this prevents a flood of reviews for
  all open PRs that existed before the automation was created.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

# ── Embedded configuration (filled in by the SKILL onboarding workflow) ───────
REPO = "owner/repo"                 # e.g. "myorg/myrepo"
LABEL = "needs-review"              # GitHub label to filter PRs
CODE_REVIEW_SKILL = (               # URL to the code-review skill
    "https://github.com/OpenHands/extensions/tree/main/skills/code-review"
)

# Maximum number of PR numbers to retain in the reviewed-PR deduplication list.
_MAX_REVIEWED_PRS = 1000
_REVIEWED_PRS_TRIM = 500


# ── State management ───────────────────────────────────────────────────────────

def _state_path(automation_id: str) -> str:
    workspace = os.environ.get("WORKSPACE_BASE", "/workspace")
    state_dir = os.path.join(workspace, "automation-state")
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, f"github_pr_poller_{automation_id}.json")


def _load_state(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as exc:
            print(f"WARNING: Could not parse state file {path}: {exc}. Starting fresh.")
    return {}


def _save_state(path: str, state: dict) -> None:
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


# ── Stdlib helpers ─────────────────────────────────────────────────────────────

def _session_key() -> str:
    return (
        os.environ.get("SESSION_API_KEY")
        or os.environ.get("OH_SESSION_API_KEYS_0")
        or ""
    )


def get_secret(name: str) -> str:
    """Fetch a named secret stored in the agent server."""
    url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    key = _session_key()
    req = urllib.request.Request(
        f"{url}/api/settings/secrets/{name}",
        headers={"X-Session-API-Key": key},
    )
    with urllib.request.urlopen(req) as r:
        return r.read().decode().strip()


def fire_callback(status: str = "COMPLETED", error: str | None = None) -> None:
    """Signal run completion to the automation service. Call on every exit path."""
    url = os.environ.get("AUTOMATION_CALLBACK_URL", "")
    if not url:
        return
    body: dict = {
        "status": status,
        "run_id": os.environ.get("AUTOMATION_RUN_ID", ""),
    }
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


# ── GitHub API helpers ─────────────────────────────────────────────────────────

def _gh_request(url: str, token: str) -> list | dict:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"GitHub API {url} -> {exc.code}: {body}") from exc


def get_new_prs(token: str, since_iso: str) -> list[dict]:
    """Return open PRs carrying LABEL that were created or updated since since_iso.

    The GitHub /issues endpoint supports ?since= (updated_at) and ?labels= together.
    We filter for items that have a pull_request key (i.e. actual PRs, not plain issues)
    and whose created_at is strictly after since_iso so we avoid re-reviewing PRs that
    were merely updated (e.g. by a comment) after the baseline.
    """
    owner, repo_name = REPO.split("/", 1)
    url = (
        f"https://api.github.com/repos/{owner}/{repo_name}/issues"
        f"?state=open&labels={LABEL}&since={since_iso}"
        f"&per_page=50&sort=created&direction=asc"
    )
    items = _gh_request(url, token)
    if not isinstance(items, list):
        raise RuntimeError(f"Unexpected GitHub response type: {type(items)}")

    return [
        item
        for item in items
        if "pull_request" in item and item.get("created_at", "") > since_iso
    ]


# ── OpenHands conversation helpers ─────────────────────────────────────────────

def _oh_request(method: str, path: str, body: dict | None = None) -> dict:
    agent_url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    api_key = _session_key()
    url = f"{agent_url}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers: dict[str, str] = {"X-Session-API-Key": api_key}
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace")
        raise RuntimeError(f"Agent API {method} {path} -> {exc.code}: {body_text}") from exc


def _get_agent_config() -> dict:
    """Fetch LLM settings from the agent server and build the agent config."""
    data = _oh_request("GET", "/api/settings")
    llm = data.get("agent_settings", {}).get("llm", {})
    return {
        "kind": "Agent",
        "llm": llm,
        "tools": [{"name": "terminal"}, {"name": "file_editor"}],
    }


def _build_review_prompt(pr: dict) -> str:
    pr_number = pr.get("number", "?")
    pr_title = pr.get("title", "(no title)")
    pr_url = (pr.get("pull_request") or {}).get("html_url") or pr.get("html_url", "")
    pr_body = (pr.get("body") or "")[:2000]
    labels = ", ".join(
        lbl.get("name", "") for lbl in (pr.get("labels") or [])
    )

    return (
        f"Please perform a thorough code review of the following GitHub pull request "
        f"in the {REPO} repository.\n\n"
        f"PR #{pr_number}: {pr_title}\n"
        f"URL: {pr_url}\n"
        f"Labels: {labels}\n\n"
        f"PR Description:\n{pr_body}\n\n"
        f"Code review skill to use: {CODE_REVIEW_SKILL}\n\n"
        f"Load and apply the instructions from that skill URL to conduct the review, "
        f"then post your findings as inline review comments and a summary review "
        f"directly on the pull request via the GitHub API."
    )


def start_review_conversation(pr: dict, agent_config: dict) -> str:
    """Create an OpenHands conversation for reviewing the given PR and return its ID."""
    workspace_dir = os.environ.get("WORKSPACE_BASE", "/workspace")
    result = _oh_request("POST", "/api/conversations", {
        "workspace": {"working_dir": workspace_dir},
        "agent": agent_config,
        "initial_message": {"content": [{"text": _build_review_prompt(pr)}]},
    })
    return result["id"]


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    event_payload = json.loads(os.environ.get("AUTOMATION_EVENT_PAYLOAD", "{}"))
    automation_id = event_payload.get("automation_id", "default")

    state_path = _state_path(automation_id)
    state = _load_state(state_path)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── First run: record baseline timestamp and exit cleanly ──────────────────
    if "last_run_ts" not in state:
        print(
            f"First run for automation {automation_id}. "
            f"Recording baseline timestamp {now_iso} and exiting. "
            f"Code reviews will begin on the next run."
        )
        state["last_run_ts"] = now_iso
        state["reviewed_prs"] = []
        _save_state(state_path, state)
        fire_callback("COMPLETED")
        sys.exit(0)

    last_run_ts: str = state["last_run_ts"]
    reviewed_prs: list[int] = state.get("reviewed_prs", [])

    print(
        f"Polling {REPO} for open PRs with label '{LABEL}' "
        f"created since {last_run_ts}"
    )

    # ── Fetch GitHub PAT ───────────────────────────────────────────────────────
    try:
        token = get_secret("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not token:
            raise ValueError("Secret value is empty")
    except Exception as exc:
        msg = f"Cannot fetch GITHUB_PERSONAL_ACCESS_TOKEN: {exc}"
        print(f"ERROR: {msg}", file=sys.stderr)
        fire_callback("FAILED", msg)
        sys.exit(1)

    # ── Poll GitHub for new PRs ────────────────────────────────────────────────
    try:
        new_prs = get_new_prs(token, last_run_ts)
    except Exception as exc:
        msg = f"GitHub API error: {exc}"
        print(f"ERROR: {msg}", file=sys.stderr)
        fire_callback("FAILED", msg)
        sys.exit(1)

    print(f"Found {len(new_prs)} new PR(s) matching criteria.")

    if not new_prs:
        state["last_run_ts"] = now_iso
        _save_state(state_path, state)
        fire_callback("COMPLETED")
        return

    # ── Fetch agent config once for all conversations ──────────────────────────
    try:
        agent_config = _get_agent_config()
    except Exception as exc:
        msg = f"Failed to fetch agent configuration: {exc}"
        print(f"ERROR: {msg}", file=sys.stderr)
        fire_callback("FAILED", msg)
        sys.exit(1)

    # ── Start a review conversation for each new PR ────────────────────────────
    for pr in new_prs:
        pr_number = pr.get("number")
        pr_title = pr.get("title", "")

        if pr_number in reviewed_prs:
            print(f"Skipping PR #{pr_number} — already reviewed in a previous run.")
            continue

        print(f"Starting code review conversation for PR #{pr_number}: {pr_title}")
        try:
            conv_id = start_review_conversation(pr, agent_config)
            reviewed_prs.append(pr_number)
            print(f"  -> Conversation {conv_id} started for PR #{pr_number}")
        except Exception as exc:
            print(
                f"WARNING: Failed to start conversation for PR #{pr_number}: {exc}",
                file=sys.stderr,
            )

    # ── Trim deduplication list to avoid unbounded growth ──────────────────────
    if len(reviewed_prs) > _MAX_REVIEWED_PRS:
        reviewed_prs = reviewed_prs[-_REVIEWED_PRS_TRIM:]

    # ── Persist state and signal completion ────────────────────────────────────
    state["last_run_ts"] = now_iso
    state["reviewed_prs"] = reviewed_prs
    _save_state(state_path, state)

    fire_callback("COMPLETED")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        fire_callback("FAILED", str(exc))
        sys.exit(1)
