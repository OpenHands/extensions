"""
GitHub PR Reviewer - OpenHands Automation Script

Cron-polls a GitHub repository for open pull requests carrying the configured
trigger label. A review is queued only when the latest matching GitHub `labeled`
event has not already been processed by this automation.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

REPO = "owner/repo"
TRIGGER_LABEL = "openhands-review"
REVIEW_TONE = "thorough"
REVIEW_STYLE_INSTRUCTIONS = ""
DEFAULT_OPENHANDS_URL = "http://localhost:8000"

DONE_DEBOUNCE = 15
TERMINAL_STATUSES = {"idle", "finished", "error", "stuck"}


def _get_env_key() -> str:
    return os.environ.get("SESSION_API_KEY") or os.environ.get("OH_SESSION_API_KEYS_0") or ""


def get_secret(name: str) -> str:
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


def _state_file_path() -> str:
    workspace_base = os.environ.get("WORKSPACE_BASE", "")
    event_payload = json.loads(os.environ.get("AUTOMATION_EVENT_PAYLOAD", "{}"))
    automation_id = event_payload.get("automation_id", "default")

    if workspace_base:
        root = Path(workspace_base).resolve().parent.parent
    else:
        root = Path.home() / ".openhands" / "workspaces"

    state_dir = root / "automation-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return str(state_dir / f"github_pr_reviewer_label_event_{automation_id}.json")


def load_state(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: state file {path} unreadable ({exc}); starting fresh")
    return {
        "version": 2,
        "repo": REPO,
        "trigger_label": TRIGGER_LABEL,
        "reviews": {},
        "prs": {},
    }


def save_state(path: str, state: dict) -> None:
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp_path, path)


def _github_request(
    token: str,
    method: str,
    path: str,
    params: dict | None = None,
    body: dict | None = None,
    accept: str = "application/vnd.github+json",
) -> tuple:
    url = f"https://api.github.com{path}"
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
        raw = r.read()
        return (json.loads(raw) if raw.strip() else {}), dict(r.headers)


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


def _verify_token_and_repo(token: str, repo: str) -> None:
    try:
        user_data, _ = _github_request(token, "GET", "/user")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError("GITHUB_PERSONAL_ACCESS_TOKEN is invalid or expired.") from exc
        raise RuntimeError(f"GitHub /user check failed: {exc.code}") from exc

    print(f"Authenticated as GitHub user: {user_data.get('login', '?')}")

    try:
        _github_request(token, "GET", f"/repos/{repo}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError(f"Repository '{repo}' is not accessible with the current token.") from exc
        raise RuntimeError(f"GitHub /repos/{repo} check failed: {exc.code}") from exc


def _list_open_prs(token: str, repo: str) -> list[dict]:
    return _github_paginate(
        token,
        f"/repos/{repo}/pulls",
        {"state": "open", "sort": "updated", "direction": "desc"},
    )


def _get_pr(token: str, repo: str, pr_number: int) -> dict:
    pr, _ = _github_request(token, "GET", f"/repos/{repo}/pulls/{pr_number}")
    return pr


def _get_issue_events(token: str, repo: str, pr_number: int) -> list[dict]:
    return _github_paginate(token, f"/repos/{repo}/issues/{pr_number}/events")


def _latest_trigger_label_event(token: str, repo: str, pr_number: int) -> dict | None:
    events = _get_issue_events(token, repo, pr_number)
    matching = [
        event for event in events
        if event.get("event") == "labeled"
        and (event.get("label") or {}).get("name", "").lower() == TRIGGER_LABEL.lower()
        and event.get("id") is not None
    ]
    if not matching:
        return None
    return max(matching, key=lambda event: (event.get("created_at") or "", int(event.get("id") or 0)))


def _post_github_comment(token: str, repo: str, pr_number: int, body: str) -> None:
    try:
        _github_request(
            token,
            "POST",
            f"/repos/{repo}/issues/{pr_number}/comments",
            body={"body": body},
        )
    except Exception as exc:
        print(f"  Warning: failed to post comment on PR #{pr_number}: {exc}")


def _oh_request(agent_url: str, api_key: str, method: str, path: str, body: dict | None = None) -> dict:
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
    req = urllib.request.Request(
        f"{agent_url}/api/settings",
        headers={"X-Session-API-Key": api_key, "X-Expose-Secrets": "plaintext"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


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
    secrets = {}
    for secret in _list_secret_names(agent_url, api_key):
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
    workspace_dir = os.environ.get("WORKSPACE_BASE", "/workspace")
    payload: dict = {
        "workspace": {"working_dir": workspace_dir},
        "agent": _get_agent_dict(agent_url, api_key),
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
    result = _oh_request(agent_url, api_key, "GET", f"/api/conversations/{conv_id}/agent_final_response")
    return result.get("response", "")


_TONE_INSTRUCTIONS = {
    "thorough": (
        "Provide a comprehensive review. Cover correctness, security vulnerabilities, "
        "missing or inadequate tests, code style, maintainability, and potential edge cases. "
        "Reference specific files and line numbers where relevant."
    ),
    "concise": (
        "Provide a brief, high-signal review. Focus only on important bugs, security problems, "
        "or significant design flaws. Omit minor style feedback."
    ),
    "friendly": (
        "Provide a constructive, encouraging review. Acknowledge what is done well before "
        "raising concerns while still noting real issues."
    ),
}


def _labels(pr: dict) -> list[str]:
    return [label.get("name", "") for label in pr.get("labels", [])]


def _has_trigger_label(pr: dict) -> bool:
    return any(label.lower() == TRIGGER_LABEL.lower() for label in _labels(pr))


def _head_sha(pr: dict) -> str:
    return ((pr.get("head") or {}).get("sha") or "").strip()


def _review_key(pr_number: int, label_event_id: int | str) -> str:
    return f"{pr_number}:label:{label_event_id}"


def _with_ai_disclosure(body: str) -> str:
    disclosure = "_This comment was posted by an AI agent (OpenHands)._"
    body = (body or "").strip()
    if disclosure.lower() in body.lower():
        return body
    return f"{body}\n\n{disclosure}" if body else disclosure


def _build_review_prompt(pr: dict, head_sha: str, label_event: dict) -> str:
    number = pr.get("number", "?")
    title = pr.get("title", "(no title)")
    body = (pr.get("body") or "").strip() or "(no description)"
    html_url = pr.get("html_url", "")
    author = (pr.get("user") or {}).get("login", "?")
    base_branch = (pr.get("base") or {}).get("ref", "?")
    head_branch = (pr.get("head") or {}).get("ref", "?")
    label_str = ", ".join(_labels(pr)) or "(none)"
    label_event_id = label_event.get("id", "?")
    label_event_created_at = label_event.get("created_at", "?")
    changed_files = pr.get("changed_files", "?")
    additions = pr.get("additions", "?")
    deletions = pr.get("deletions", "?")
    clone_url = f"https://github.com/{REPO}.git"
    tone = _TONE_INSTRUCTIONS.get(REVIEW_TONE, _TONE_INSTRUCTIONS["thorough"])
    extra = f"\n\nAdditional style instructions:\n{REVIEW_STYLE_INSTRUCTIONS}" if REVIEW_STYLE_INSTRUCTIONS.strip() else ""

    return (
        "You are an AI code reviewer. Review the GitHub pull request below and write "
        "a single review comment. Do not modify files, push commits, approve via the GitHub "
        "API, or request changes via the review API; only produce the final comment text.\n\n"
        f"Repository : {REPO}\n"
        f"Clone URL  : {clone_url}\n"
        f"PR #{number}: \"{title}\"\n"
        f"Author     : @{author}\n"
        f"Base → Head: {base_branch} ← {head_branch}\n"
        f"Head SHA   : {head_sha}\n"
        f"Trigger    : latest `{TRIGGER_LABEL}` labeled event {label_event_id} at {label_event_created_at}\n"
        f"Labels     : {label_str}\n"
        f"Changes    : +{additions} -{deletions} across {changed_files} file(s)\n"
        f"URL        : {html_url}\n"
        f"\nPR Description:\n---\n{body}\n---\n\n"
        "Required workflow:\n"
        "1. Clone the repository into a fresh working directory inside the workspace.\n"
        f"   Example: `git clone {clone_url} pr-review-{number}`.\n"
        "2. Check out the exact pull request branch by PR number, then verify HEAD matches the SHA above.\n"
        f"   Example: `git fetch origin pull/{number}/head:openhands-pr-{number}` followed by `git checkout openhands-pr-{number}`.\n"
        "3. Inspect the existing PR context before reviewing, including PR description, issue comments, review comments, changed files, and the diff.\n"
        "   Prefer `gh pr view`, `gh pr diff`, `gh pr checkout`, or GitHub REST API calls with `GITHUB_PERSONAL_ACCESS_TOKEN`; do not print secret values.\n"
        "4. Use the checked-out repository to inspect relevant files and surrounding code, not just the patch.\n"
        "5. Before producing the final review text, delete only the cloned repository directory created in step 1.\n"
        f"   Example: `rm -rf pr-review-{number}`. Do not delete any other files or directories.\n"
        "6. Write a high-signal review comment with specific findings. If there are no material issues, say so.\n"
        f"\nReview instructions:\n{tone}{extra}\n\n"
        "Output ONLY the review text — no preamble, no meta-commentary. "
        "This text will be posted verbatim as a comment on the pull request. "
        "End your review with a clear verdict on its own line: either `✅ APPROVED` "
        "or `🔄 CHANGES REQUESTED`."
    )

def _process_review_request(
    github_token: str,
    agent_url: str,
    api_key: str,
    openhands_url: str,
    pr: dict,
    label_event: dict,
    reviews: dict,
) -> str | None:
    number = pr["number"]
    head_sha = _head_sha(pr)
    label_event_id = label_event["id"]
    key = _review_key(number, label_event_id)
    title = pr.get("title", "(no title)")
    html_url = pr.get("html_url", "")

    print(f"  Queuing review for PR #{number} from `{TRIGGER_LABEL}` event {label_event_id} at {head_sha[:12]}: {title}")
    prompt = _build_review_prompt(pr, head_sha, label_event)

    try:
        conv_id = create_conversation(agent_url, api_key, prompt)
    except Exception as exc:
        print(f"  Error creating conversation for PR #{number}: {exc}")
        return None

    reviews[key] = {
        "pr_number": number,
        "head_sha": head_sha,
        "trigger_label_event_id": label_event_id,
        "trigger_label_event_created_at": label_event.get("created_at"),
        "html_url": html_url,
        "status": "active",
        "conversation_id": conv_id,
        "last_activity": time.time(),
    }
    print(f"  Created review conversation {conv_id}")

    conv_url = f"{openhands_url}/conversations/{conv_id}"
    _post_github_comment(
        github_token,
        REPO,
        number,
        _with_ai_disclosure(
            "🤖 **OpenHands is reviewing this PR.**\n\n"
            f"Trigger label: `{TRIGGER_LABEL}`\n"
            f"Label event: `{label_event_id}` at `{label_event.get('created_at', '?')}`\n"
            f"Head commit: `{head_sha}`\n"
            f"View the conversation: {conv_url}"
        ),
    )
    return conv_id

def _check_conversation_completion(
    rec: dict,
    latest_open_prs: dict[int, dict],
    github_token: str,
    agent_url: str,
    api_key: str,
) -> None:
    if (time.time() - rec.get("last_activity", 0.0)) < DONE_DEBOUNCE:
        return

    conv_id = rec["conversation_id"]
    pr_number = rec["pr_number"]
    reviewed_sha = rec.get("head_sha", "")
    current_pr = latest_open_prs.get(pr_number)

    if not current_pr:
        rec["status"] = "closed"
        print(f"  PR #{pr_number} closed/merged — skipping result post")
        return

    current_sha = _head_sha(current_pr)
    if current_sha and reviewed_sha and current_sha != reviewed_sha:
        rec["status"] = "stale"
        rec["stale_reason"] = f"head changed from {reviewed_sha} to {current_sha}"
        print(f"  PR #{pr_number} advanced to {current_sha[:12]} — suppressing stale review {conv_id}")
        return

    try:
        status = conversation_status(agent_url, api_key, conv_id)
    except Exception as exc:
        print(f"  Warning: could not get status for {conv_id}: {exc}")
        return

    print(f"  PR #{pr_number} conversation {conv_id} → status={status}")
    if status not in TERMINAL_STATUSES:
        return

    try:
        final = conversation_final_response(agent_url, api_key, conv_id)
    except Exception:
        final = ""

    if status in {"error", "stuck"}:
        comment_body = _with_ai_disclosure(
            f"⚠️ **OpenHands PR Reviewer encountered a problem** at commit `{reviewed_sha[:12]}` "
            f"(status: `{status}`).\n\n{final}".strip()
        )
    else:
        comment_body = _with_ai_disclosure(
            final
            or f"✅ **OpenHands completed the review for commit `{reviewed_sha[:12]}`.** No review text was produced."
        )

    _post_github_comment(github_token, REPO, pr_number, comment_body)
    rec["status"] = "closed"
    rec["completed_at"] = time.time()
    print(f"  Posted review for PR #{pr_number} at {reviewed_sha[:12]}")


def main() -> str | None:
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

    reviews: dict = state.setdefault("reviews", {})
    prs_state: dict = state.setdefault("prs", {})

    open_prs = _list_open_prs(github_token, REPO)
    latest_open_prs = {pr["number"]: pr for pr in open_prs}
    print(f"Found {len(open_prs)} open PR(s) in {REPO}")

    last_conversation_id = None

    for pr in open_prs:
        number = pr["number"]
        head_sha = _head_sha(pr)
        label_present = _has_trigger_label(pr)
        prs_state[str(number)] = {
            "head_sha": head_sha,
            "label_present": label_present,
            "labels": _labels(pr),
            "last_seen": time.time(),
        }

        if not label_present:
            continue
        if not head_sha:
            print(f"  PR #{number} has no head SHA; skipping")
            continue

        fresh_pr = _get_pr(github_token, REPO, number)
        fresh_head_sha = _head_sha(fresh_pr)
        if fresh_head_sha != head_sha:
            print(f"  PR #{number} head changed during poll ({head_sha[:12]} → {fresh_head_sha[:12]}); using latest PR metadata")
        if not _has_trigger_label(fresh_pr):
            print(f"  PR #{number} lost `{TRIGGER_LABEL}` during poll; skipping")
            continue

        label_event = _latest_trigger_label_event(github_token, REPO, number)
        if not label_event:
            print(f"  PR #{number} has `{TRIGGER_LABEL}` but no matching labeled event; skipping")
            continue

        key = _review_key(number, label_event["id"])
        if key in reviews:
            print(f"  PR #{number} label event {label_event['id']} already tracked ({reviews[key].get('status')})")
            continue

        conv_id = _process_review_request(github_token, agent_url, api_key, openhands_url, fresh_pr, label_event, reviews)
        if conv_id:
            last_conversation_id = conv_id

    for rec in list(reviews.values()):
        if rec.get("status") != "active":
            continue
        _check_conversation_completion(rec, latest_open_prs, github_token, agent_url, api_key)

    state["repo"] = REPO
    state["trigger_label"] = TRIGGER_LABEL
    state["updated_at"] = time.time()
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
