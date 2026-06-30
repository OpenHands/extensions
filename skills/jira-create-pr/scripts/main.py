"""
Jira create-pr poller — reads all configuration from config.json in the same directory.

config.json fields:
  jira_base_url          e.g. "https://yourcompany.atlassian.net"
  jira_email             Atlassian account email used for Basic auth
  jira_token_secret      Name of the OpenHands secret holding the Jira API token
  github_repo            "owner/repo" target for pull requests
  jira_label             Label to watch for (default: "create-pr")
"""
import base64, json, os, sys, tempfile, urllib.error, urllib.request
from pathlib import Path

# ── Load config ───────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent
with open(_HERE / "config.json") as _f:
    _cfg = json.load(_f)

JIRA_BASE_URL      = _cfg["jira_base_url"].rstrip("/")
JIRA_EMAIL         = _cfg["jira_email"]
JIRA_TOKEN_SECRET  = _cfg.get("jira_token_secret", "JIRA_CLOUD_KEY")
GITHUB_REPO        = _cfg["github_repo"]
JIRA_LABEL         = _cfg.get("jira_label", "create-pr")

# ── KV store helpers ──────────────────────────────────────────────────────────
_KV_TOKEN  = os.environ.get("AUTOMATION_KV_TOKEN", "")
_KV_BASE   = os.environ.get("AUTOMATION_API_URL", "").rstrip("/")
_STATE_KEY = "state"


def kv_available():
    return bool(_KV_TOKEN and _KV_BASE)


def kv_get(key):
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


def kv_set(key, value):
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


def _state_file_path():
    workspace_base = os.environ.get("WORKSPACE_BASE", "")
    root = (Path(workspace_base).resolve().parent.parent if workspace_base
            else Path.home() / ".openhands" / "workspaces")
    state_dir = root / "automation-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    payload       = json.loads(os.environ.get("AUTOMATION_EVENT_PAYLOAD", "{}"))
    automation_id = payload.get("automation_id", "default")
    return state_dir / f"jira_poller_{automation_id}.json"


def load_state():
    if kv_available():
        data = kv_get(_STATE_KEY)
        if data is not None:
            print("State loaded from KV store")
            return data
        return {"processed_keys": []}
    path = _state_file_path()
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception as exc:
            print(f"Warning: state file unreadable ({exc}); starting fresh")
    return {"processed_keys": []}


def save_state(state):
    if kv_available():
        kv_set(_STATE_KEY, state)
        print("State saved to KV store")
        return
    path = _state_file_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(path)
    print(f"State saved to {path}")


# ── Required stdlib helpers ───────────────────────────────────────────────────
def get_secret(name):
    url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    key = os.environ.get("SESSION_API_KEY") or os.environ.get("OH_SESSION_API_KEYS_0", "")
    with urllib.request.urlopen(urllib.request.Request(
        f"{url}/api/settings/secrets/{name}", headers={"X-Session-API-Key": key}
    )) as r:
        return r.read().decode().strip()


def fire_callback(status="COMPLETED", error=None):
    url = os.environ.get("AUTOMATION_CALLBACK_URL", "")
    if not url:
        return
    body = {"status": status, "run_id": os.environ.get("AUTOMATION_RUN_ID", "")}
    if error:
        body["error"] = error
    try:
        urllib.request.urlopen(urllib.request.Request(
            url, data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.environ.get('AUTOMATION_CALLBACK_API_KEY', '')}",
            }
        ))
    except Exception as e:
        print(f"Callback error (non-fatal): {e}")


# ── Jira helpers ──────────────────────────────────────────────────────────────
def extract_adf_text(adf):
    """Recursively extract plain text from Atlassian Document Format."""
    if not isinstance(adf, dict):
        return adf or ""
    parts = []
    for node in adf.get("content", []):
        if node.get("type") == "text":
            parts.append(node.get("text", ""))
        elif "content" in node:
            parts.append(extract_adf_text(node))
    return " ".join(p for p in parts if p).strip()


def fetch_labeled_issues(auth_header):
    """Return open Jira issues with JIRA_LABEL using the current v3 search endpoint."""
    url  = f"{JIRA_BASE_URL}/rest/api/3/search/jql"
    body = json.dumps({
        "jql":        f'labels = "{JIRA_LABEL}" AND statusCategory != Done',
        "fields":     ["key", "summary", "description", "status"],
        "maxResults": 50,
    }).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={
            "Authorization": auth_header,
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read()).get("issues", [])
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace")
        raise RuntimeError(f"Jira search failed {exc.code}: {body_text[:500]}") from exc


# ── Main ──────────────────────────────────────────────────────────────────────
try:
    jira_token  = get_secret(JIRA_TOKEN_SECRET)
    auth_header = "Basic " + base64.b64encode(
        f"{JIRA_EMAIL}:{jira_token}".encode()
    ).decode()

    state          = load_state()
    processed_keys = set(state.get("processed_keys", []))

    print(f"Polling {JIRA_BASE_URL} for issues labeled '{JIRA_LABEL}'…")
    issues = fetch_labeled_issues(auth_header)
    print(f"Total matching issues : {len(issues)}")

    new_issues = [i for i in issues if i["key"] not in processed_keys]
    print(f"New (unprocessed)     : {len(new_issues)}")

    if not new_issues:
        save_state(state)
        fire_callback("COMPLETED")
        sys.exit(0)

    # Start one agent conversation per new issue via the agent server HTTP API.
    agent_url   = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    session_key = os.environ.get("SESSION_API_KEY") or os.environ.get("OH_SESSION_API_KEYS_0", "")

    with urllib.request.urlopen(urllib.request.Request(
        f"{agent_url}/api/settings",
        headers={"X-Session-API-Key": session_key},
    )) as r:
        settings = json.loads(r.read())

    agent_settings = settings.get("agent_settings", {})
    agent_settings.pop("schema_version", None)
    ctx = agent_settings.setdefault("agent_context", {})
    ctx.update({"load_public_skills": True, "load_user_skills": True, "load_project_skills": True})
    max_iterations = (settings.get("conversation_settings") or {}).get("max_iterations") or 80

    for issue in new_issues:
        key         = issue["key"]
        summary     = issue["fields"]["summary"]
        description = extract_adf_text(issue["fields"].get("description"))
        branch      = f"jira/{key.lower()}"

        prompt = f"""Create a GitHub Pull Request for the following Jira issue.

Jira Issue : {key}
Summary    : {summary}
Description: {description or "No description provided."}

Steps:
1. Clone https://github.com/{GITHUB_REPO}
2. Create branch `{branch}` from the default branch.
3. Implement the changes described in the issue.
   If the description is vague or missing, create `jira/{key}/notes.md`
   with the issue key, summary, and description as a placeholder.
4. Commit, push the branch, and open a Pull Request:
   - Title : [{key}] {summary}
   - Body  : Reference the Jira issue key and describe the changes made.
5. Print the PR URL when done.
"""
        workdir = tempfile.mkdtemp(prefix=f"jira-{key.lower()}-")
        payload = {
            "agent_settings":      agent_settings,
            "workspace":           {"kind": "LocalWorkspace", "working_dir": workdir},
            "confirmation_policy": {"kind": "NeverConfirm"},
            "max_iterations":      max_iterations,
            "stuck_detection":     True,
            "autotitle":           True,
            "worktree":            False,
            "initial_message": {
                "role":    "user",
                "content": [{"type": "text", "text": prompt}],
                "run":     True,
            },
        }
        conv_req = urllib.request.Request(
            f"{agent_url}/api/conversations",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "X-Session-API-Key": session_key},
        )
        with urllib.request.urlopen(conv_req) as r:
            conv = json.loads(r.read())

        print(f"✓ Conversation started for {key}: id={conv.get('id')}")

        processed_keys.add(key)
        state["processed_keys"] = list(processed_keys)
        save_state(state)

    fire_callback("COMPLETED")

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    import traceback; traceback.print_exc()
    fire_callback("FAILED", str(e))
    sys.exit(1)
