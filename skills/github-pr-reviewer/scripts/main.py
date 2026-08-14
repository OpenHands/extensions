"""
GitHub PR Reviewer - OpenHands Automation Script

Cron-polls one or more GitHub repositories for open pull requests carrying the
configured trigger label. A review is queued only when the latest matching
GitHub `labeled` event has not already been processed by this automation.

Each repository is polled independently and keeps its own state document, so
pull-request numbers never collide across repositories.

The script owns the repository checkout: it downloads the pull request's head
commit as a tarball, hands the agent that directory as its workspace, and
removes it once the review has finished. The agent never clones, checks out, or
deletes anything.
"""

import io
import json
import os
import shutil
import sys
import tarfile
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from urllib.parse import urlencode

REPOS = ["owner/repo"]
TRIGGER_LABEL = "openhands-review"
REVIEW_TONE = "thorough"
REVIEW_STYLE_INSTRUCTIONS = ""
DEFAULT_OPENHANDS_URL = "http://localhost:8000"

DONE_DEBOUNCE = 15
TERMINAL_STATUSES = {"idle", "finished", "error", "stuck"}
# A conversation that never reaches a terminal status would hold its checkout
# forever. After this long the review is abandoned so the disk can be reclaimed.
MAX_ACTIVE_AGE = 2 * 60 * 60
# A label event is claimed in the state document before its review starts, so an
# overlapping poll skips it. If the claiming poll dies before the conversation
# exists, the claim is released after this long - comfortably longer than
# fetching an archive and opening a conversation, short enough that a crash does
# not park the review until someone notices.
STALLED_CLAIM_SECONDS = 15 * 60

# Login of the token owner, filled in by _verify_token. Reviews are matched
# against it to answer "did we already publish a review for this commit", which
# is checked on GitHub rather than trusted from the agent.
_AUTH_LOGIN = ""


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


# ── State persistence (KV store with local-file fallback) ─────────────────────

_KV_TOKEN = os.environ.get("AUTOMATION_KV_TOKEN", "")
_KV_BASE = os.environ.get("AUTOMATION_API_URL", "").rstrip("/")
# Single-repository deployments of this script kept their state under a bare
# "state" key. It is adopted once, on first poll after an upgrade, so the
# switch to per-repository keys does not re-review every open labelled PR.
_LEGACY_STATE_KEY = "state"


def _repo_slug(repo: str) -> str:
    return repo.replace("/", "__")


def _state_key(repo: str) -> str:
    return f"state:{_repo_slug(repo)}"


def _kv_available() -> bool:
    return bool(_KV_TOKEN and _KV_BASE)


def _kv_get(key: str) -> dict | None:
    req = urllib.request.Request(
        f"{_KV_BASE}/v1/kv/{key}",
        headers={"Authorization": f"Bearer {_KV_TOKEN}"},
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())["value"]
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _kv_set(key: str, value: dict) -> None:
    req = urllib.request.Request(
        f"{_KV_BASE}/v1/kv/{key}",
        data=json.dumps(value).encode(),
        headers={
            "Authorization": f"Bearer {_KV_TOKEN}",
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    with urllib.request.urlopen(req) as r:
        r.read()


def _state_dir() -> Path:
    workspace_base = os.environ.get("WORKSPACE_BASE", "")
    if workspace_base:
        root = Path(workspace_base).resolve().parent.parent
    else:
        root = Path.home() / ".openhands" / "workspaces"
    state_dir = root / "automation-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def _automation_id() -> str:
    event_payload = json.loads(os.environ.get("AUTOMATION_EVENT_PAYLOAD", "{}"))
    return event_payload.get("automation_id", "default")


def _state_file_path(repo: str) -> str:
    name = f"github_pr_reviewer_label_event_{_automation_id()}_{_repo_slug(repo)}.json"
    return str(_state_dir() / name)


def _legacy_state_file_path() -> str:
    return str(_state_dir() / f"github_pr_reviewer_label_event_{_automation_id()}.json")


def _read_state_file(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  Warning: state file {path} unreadable ({exc}); starting fresh")
        return None


def _default_state(repo: str) -> dict:
    return {
        "version": 3,
        "repo": repo,
        "trigger_label": TRIGGER_LABEL,
        "reviews": {},
        "prs": {},
    }


def load_state(repo: str) -> dict:
    """Load this repository's state, adopting a pre-multi-repo document once."""
    if _kv_available():
        data = _kv_get(_state_key(repo))
        if data is not None:
            print(f"  State loaded from KV store ({_state_key(repo)})")
            return data
        legacy = _kv_get(_LEGACY_STATE_KEY)
        if legacy is not None and legacy.get("repo") == repo:
            print(f"  Adopted legacy KV state for {repo}")
            return legacy
        return _default_state(repo)

    data = _read_state_file(_state_file_path(repo))
    if data is not None:
        return data
    legacy = _read_state_file(_legacy_state_file_path())
    if legacy is not None and legacy.get("repo") == repo:
        print(f"  Adopted legacy state file for {repo}")
        return legacy
    return _default_state(repo)


def save_state(repo: str, state: dict) -> None:
    if _kv_available():
        _kv_set(_state_key(repo), state)
        print(f"  State saved to KV store ({_state_key(repo)})")
        return
    path = _state_file_path(repo)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp_path, path)
    print(f"  State saved to {path}")


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


def _verify_token(token: str) -> None:
    """Check the token once per run and remember who it belongs to."""
    global _AUTH_LOGIN
    try:
        user_data, _ = _github_request(token, "GET", "/user")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError("GITHUB_PERSONAL_ACCESS_TOKEN is invalid or expired.") from exc
        raise RuntimeError(f"GitHub /user check failed: {exc.code}") from exc

    _AUTH_LOGIN = user_data.get("login", "")
    print(f"Authenticated as GitHub user: {_AUTH_LOGIN or '?'}")


def _verify_repo(token: str, repo: str) -> None:
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


def _matching_review_exists(token: str, repo: str, pr_number: int, head_sha: str) -> bool:
    """Has this token's user already published a review for this exact commit?

    The agent is asked to report success, but a report is not evidence: reviews
    have been reported as posted when none existed. GitHub is the source of
    truth for whether the review landed.
    """
    if not head_sha or not _AUTH_LOGIN:
        return False
    try:
        reviews = _github_paginate(token, f"/repos/{repo}/pulls/{pr_number}/reviews")
    except Exception as exc:
        print(f"  Warning: could not list reviews for PR #{pr_number}: {exc}")
        return False
    for review in reviews:
        if (review.get("user") or {}).get("login", "").lower() != _AUTH_LOGIN.lower():
            continue
        if review.get("commit_id") == head_sha:
            return True
    return False


# ── Repository checkout ───────────────────────────────────────────────────────


def _checkouts_root() -> Path:
    return Path(os.environ.get("WORKSPACE_BASE", "/workspace")).resolve() / "repositories"


def _checkout_path(repo: str, pr_number: int, head_sha: str) -> Path:
    return _checkouts_root() / _repo_slug(repo) / f"pr-{pr_number}-{head_sha[:12]}"


def _prepare_repository(token: str, repo: str, pr_number: int, head_sha: str) -> Path:
    """Materialise the pull request's head commit as the agent's workspace.

    The commit is fetched as a tarball rather than cloned, so the directory
    holds exactly the reviewed tree with no history and no git remote for the
    agent to push to.
    """
    checkout = _checkout_path(repo, pr_number, head_sha)
    if checkout.exists():
        shutil.rmtree(checkout)
    checkout.mkdir(parents=True)

    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/tarball/{head_sha}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    skipped_links = 0
    try:
        with urllib.request.urlopen(req) as response:
            archive = tarfile.open(fileobj=io.BytesIO(response.read()), mode="r:gz")
        with archive:
            members = archive.getmembers()
            roots = {
                PurePosixPath(member.name).parts[0]
                for member in members
                if PurePosixPath(member.name).parts
            }
            if len(roots) != 1:
                raise RuntimeError("Repository archive has an unexpected layout")
            root = next(iter(roots))
            for member in members:
                path = PurePosixPath(member.name)
                if not path.parts or path.parts[0] != root:
                    raise RuntimeError("Repository archive contains an invalid path")
                relative = PurePosixPath(*path.parts[1:])
                if not relative.parts:
                    continue
                if relative.is_absolute() or ".." in relative.parts:
                    raise RuntimeError("Repository archive contains path traversal")
                if member.issym() or member.islnk() or member.isdev():
                    # Repositories legitimately contain symlinks. Reviewing does
                    # not need them, and materialising them risks escaping the
                    # checkout, so skip rather than reject the whole archive.
                    skipped_links += 1
                    continue
                destination = checkout.joinpath(*relative.parts)
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise RuntimeError(f"Could not read archive member {member.name}")
                with source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)
                destination.chmod(member.mode & 0o777)
    except Exception:
        shutil.rmtree(checkout, ignore_errors=True)
        raise

    if skipped_links:
        print(f"  Skipped {skipped_links} link/device entries while extracting")
    return checkout


def _release_checkout(rec: dict, agent_url: str, api_key: str) -> bool:
    """Remove a finished review's checkout. Returns True when nothing is left.

    The checkout is the conversation's working directory, so it is only removed
    once the conversation has stopped - deleting it under a running agent would
    pull the ground out from under it. When the status cannot be confirmed the
    directory is left alone and the next poll tries again.
    """
    workspace_dir = rec.get("workspace_dir")
    if not workspace_dir:
        return True

    conversation_id = rec.get("conversation_id")
    if conversation_id:
        try:
            status = conversation_status(agent_url, api_key, conversation_id)
        except urllib.error.HTTPError as exc:
            status = "finished" if exc.code == 404 else None
        except Exception:
            status = None
        if status is None:
            print(f"  Could not confirm conversation {conversation_id} has stopped; keeping {workspace_dir}")
            return False
        if status not in TERMINAL_STATUSES:
            print(f"  Conversation {conversation_id} is still '{status}'; keeping its checkout")
            return False

    path = Path(workspace_dir)
    root = _checkouts_root()
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    if resolved == root or not resolved.is_relative_to(root):
        # Never delete anything the script did not create under the checkout
        # root, whatever ended up recorded in state.
        print(f"  Refusing to remove {resolved}: outside {root}")
        rec.pop("workspace_dir", None)
        return True

    shutil.rmtree(resolved, ignore_errors=True)
    rec.pop("workspace_dir", None)
    print(f"  Removed checkout {resolved}")
    return True


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


def create_conversation(
    agent_url: str,
    api_key: str,
    initial_message: str,
    workspace_dir: Path,
) -> str:
    payload: dict = {
        "workspace": {"working_dir": str(workspace_dir)},
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


def _build_review_prompt(repo: str, pr: dict, head_sha: str, label_event: dict) -> str:
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
    tone = _TONE_INSTRUCTIONS.get(REVIEW_TONE, _TONE_INSTRUCTIONS["thorough"])
    extra = f"\n\nAdditional style instructions:\n{REVIEW_STYLE_INSTRUCTIONS}" if REVIEW_STYLE_INSTRUCTIONS.strip() else ""

    return (
        "You are an AI code reviewer. Review the GitHub pull request below and publish "
        "the review directly to GitHub. Do not modify files, push commits, or approve "
        "the pull request.\n\n"
        f"Repository : {repo}\n"
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
        "1. The workspace is already the repository root at the exact Head SHA above. "
        "Do not clone, fetch, check out, or delete the repository.\n"
        "2. Inspect the PR discussion, existing review comments, changed files, and the diff, "
        "together with the surrounding code in the workspace.\n"
        "   Use `gh` or GitHub REST API calls with `GITHUB_PERSONAL_ACCESS_TOKEN`; never print secret values.\n"
        "3. Ground every finding in the workspace code. Before using an inline location, verify that "
        "the path and line are part of this pull request's diff.\n"
        f"4. Publish one review with `POST /repos/{repo}/pulls/{number}/reviews`, using "
        "`commit_id` equal to the Head SHA above and `event: COMMENT`.\n"
        "   Put the overall assessment in `body`, and each line-specific finding in the `comments` "
        "array with `path`, `line`, `side: RIGHT`, and `body`.\n"
        "   Only create inline comments for actionable findings; do not open praise or nitpick threads.\n"
        "5. If a finding cannot be attached to a changed line, put it in the review body instead. "
        "If the API rejects the inline positions, retry with every finding in the body and no `comments` array.\n"
        "6. Begin the review body with this disclosure: "
        "`_This review was posted by an AI agent (OpenHands)._`\n"
        "7. End the review body with a verdict on its own line: either `✅ APPROVED` "
        "or `🔄 CHANGES REQUESTED`.\n"
        "8. If there are no material issues, still publish a review saying so, with the "
        "disclosure and the verdict.\n"
        f"\nReview instructions:\n{tone}{extra}\n\n"
        "After GitHub accepts the review, output exactly `GITHUB_REVIEW_POSTED`. "
        "If publishing still fails after the fallback in step 5, output the complete review text "
        "so it can be posted as a comment instead."
    )


def _process_review_request(
    github_token: str,
    agent_url: str,
    api_key: str,
    openhands_url: str,
    repo: str,
    pr: dict,
    label_event: dict,
    reviews: dict,
    persist: Callable[[], None],
) -> str | None:
    number = pr["number"]
    head_sha = _head_sha(pr)
    label_event_id = label_event["id"]
    key = _review_key(number, label_event_id)
    title = pr.get("title", "(no title)")
    html_url = pr.get("html_url", "")

    print(f"  Queuing review for PR #{number} from `{TRIGGER_LABEL}` event {label_event_id} at {head_sha[:12]}: {title}")

    # Claim the label event and persist it *before* the slow work below. State
    # is otherwise only written when the repository finishes polling, so a poll
    # starting while this one downloads an archive or spins up a conversation
    # would read no record for this event and review the same commit a second
    # time - two conversations, two "reviewing" comments, two reviews.
    reviews[key] = {
        "pr_number": number,
        "head_sha": head_sha,
        "trigger_label_event_id": label_event_id,
        "trigger_label_event_created_at": label_event.get("created_at"),
        "html_url": html_url,
        "status": "starting",
        "conversation_id": None,
        "workspace_dir": None,
        "last_activity": time.time(),
    }
    persist()

    workspace_dir = None
    try:
        workspace_dir = _prepare_repository(github_token, repo, number, head_sha)
        prompt = _build_review_prompt(repo, pr, head_sha, label_event)
        conv_id = create_conversation(agent_url, api_key, prompt, workspace_dir)
    except Exception as exc:
        # The claim is dropped so the next poll retries this label event. The
        # checkout goes with it rather than being left behind.
        if workspace_dir:
            shutil.rmtree(workspace_dir, ignore_errors=True)
        reviews.pop(key, None)
        persist()
        print(f"  Error starting review for PR #{number}: {exc}")
        return None

    reviews[key].update(
        {
            "status": "active",
            "conversation_id": conv_id,
            "workspace_dir": str(workspace_dir),
            "last_activity": time.time(),
        }
    )
    persist()
    print(f"  Created review conversation {conv_id}")

    conv_url = f"{openhands_url}/conversations/{conv_id}"
    _post_github_comment(
        github_token,
        repo,
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
    repo: str,
) -> None:
    age = time.time() - rec.get("last_activity", 0.0)
    if age < DONE_DEBOUNCE:
        return

    conv_id = rec["conversation_id"]
    pr_number = rec["pr_number"]
    reviewed_sha = rec.get("head_sha", "")
    current_pr = latest_open_prs.get(pr_number)

    if not current_pr:
        rec["status"] = "closed"
        print(f"  PR #{pr_number} closed/merged — skipping result post")
        _release_checkout(rec, agent_url, api_key)
        return

    current_sha = _head_sha(current_pr)
    if current_sha and reviewed_sha and current_sha != reviewed_sha:
        rec["status"] = "stale"
        rec["stale_reason"] = f"head changed from {reviewed_sha} to {current_sha}"
        print(f"  PR #{pr_number} advanced to {current_sha[:12]} — suppressing stale review {conv_id}")
        _release_checkout(rec, agent_url, api_key)
        return

    try:
        status = conversation_status(agent_url, api_key, conv_id)
    except Exception as exc:
        print(f"  Warning: could not get status for {conv_id}: {exc}")
        return

    print(f"  PR #{pr_number} conversation {conv_id} → status={status}")
    if status not in TERMINAL_STATUSES:
        if age > MAX_ACTIVE_AGE:
            rec["status"] = "expired"
            rec["expired_after"] = age
            print(f"  Review for PR #{pr_number} still '{status}' after {int(age)}s; abandoning it")
            _release_checkout(rec, agent_url, api_key)
        return

    try:
        final = conversation_final_response(agent_url, api_key, conv_id)
    except Exception:
        final = ""

    if status in {"error", "stuck"}:
        _post_github_comment(
            github_token,
            repo,
            pr_number,
            _with_ai_disclosure(
                f"⚠️ **OpenHands PR Reviewer encountered a problem** at commit `{reviewed_sha[:12]}` "
                f"(status: `{status}`).\n\n{final}".strip()
            ),
        )
    elif _matching_review_exists(github_token, repo, pr_number, reviewed_sha):
        print(f"  PR #{pr_number}: review confirmed on GitHub at {reviewed_sha[:12]}")
    else:
        # The agent was asked to publish the review itself; it did not, so the
        # work is not lost - post whatever it produced as a comment.
        _post_github_comment(
            github_token,
            repo,
            pr_number,
            _with_ai_disclosure(
                final
                or f"✅ **OpenHands completed the review for commit `{reviewed_sha[:12]}`.** No review text was produced."
            ),
        )
        print(f"  PR #{pr_number}: no review found on GitHub; posted the result as a comment")

    rec["status"] = "closed"
    rec["completed_at"] = time.time()
    _release_checkout(rec, agent_url, api_key)


def _process_repo(
    repo: str,
    github_token: str,
    agent_url: str,
    api_key: str,
    openhands_url: str,
) -> str | None:
    """Poll one repository end to end. Its state is loaded and saved here, so a
    failure in another repository cannot discard this one's progress."""
    print(f"\n=== {repo} ===")
    _verify_repo(github_token, repo)

    state = load_state(repo)
    reviews: dict = state.setdefault("reviews", {})
    prs_state: dict = state.setdefault("prs", {})

    def persist() -> None:
        state["version"] = 3
        state["repo"] = repo
        state["trigger_label"] = TRIGGER_LABEL
        state["updated_at"] = time.time()
        save_state(repo, state)

    open_prs = _list_open_prs(github_token, repo)
    latest_open_prs = {pr["number"]: pr for pr in open_prs}
    print(f"  Found {len(open_prs)} open PR(s)")

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

        fresh_pr = _get_pr(github_token, repo, number)
        fresh_head_sha = _head_sha(fresh_pr)
        if fresh_head_sha != head_sha:
            print(f"  PR #{number} head changed during poll ({head_sha[:12]} → {fresh_head_sha[:12]}); using latest PR metadata")
        if not _has_trigger_label(fresh_pr):
            print(f"  PR #{number} lost `{TRIGGER_LABEL}` during poll; skipping")
            continue

        label_event = _latest_trigger_label_event(github_token, repo, number)
        if not label_event:
            print(f"  PR #{number} has `{TRIGGER_LABEL}` but no matching labeled event; skipping")
            continue

        key = _review_key(number, label_event["id"])
        if key in reviews:
            print(f"  PR #{number} label event {label_event['id']} already tracked ({reviews[key].get('status')})")
            continue

        conv_id = _process_review_request(
            github_token, agent_url, api_key, openhands_url, repo, fresh_pr, label_event, reviews, persist
        )
        if conv_id:
            last_conversation_id = conv_id

    for rev_key, rec in list(reviews.items()):
        if rec.get("status") == "starting":
            # A claim this poll made has already moved to "active" or been
            # dropped, so one still sitting here belongs to a poll that died
            # between claiming and creating its conversation. Release it once it
            # is old enough that no live poll could still be working on it,
            # otherwise the label event would never be reviewed.
            age = time.time() - float(rec.get("last_activity") or 0)
            if age > STALLED_CLAIM_SECONDS:
                print(f"  Releasing a claim stalled for {int(age)}s: {rev_key}")
                reviews.pop(rev_key, None)
            continue
        if rec.get("status") == "active":
            _check_conversation_completion(rec, latest_open_prs, github_token, agent_url, api_key, repo)
        elif rec.get("workspace_dir"):
            # A checkout whose removal could not be confirmed on an earlier
            # poll, e.g. the agent was still running when its PR was closed.
            _release_checkout(rec, agent_url, api_key)

    persist()
    return last_conversation_id


def main() -> str | None:
    agent_url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    api_key = _get_env_key()

    github_token = _resolve_github_token()
    _verify_token(github_token)

    try:
        openhands_url = get_secret("OPENHANDS_URL").rstrip("/") or DEFAULT_OPENHANDS_URL
    except Exception:
        openhands_url = DEFAULT_OPENHANDS_URL

    last_conversation_id = None
    failures = []
    for repo in REPOS:
        # One repository failing must not stop the others from being polled.
        try:
            conv_id = _process_repo(repo, github_token, agent_url, api_key, openhands_url)
            if conv_id:
                last_conversation_id = conv_id
        except Exception as exc:
            print(f"Error processing {repo}: {exc}")
            failures.append(f"{repo}: {exc}")

    if failures and len(failures) == len(REPOS):
        # Every repository failed, so the run achieved nothing - report it as a
        # failed run rather than a successful no-op.
        raise RuntimeError("; ".join(failures))
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
