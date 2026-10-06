"""
Jira issue-to-PR poller — reads all configuration from config.json in the same directory.

config.json fields:
  jira_mcp_server        Settings name of the connected Atlassian Rovo MCP server. When set,
                         Jira is reached through it (OpenHands Cloud and Enterprise only)
                         and no Jira credential is configured here
  jira_cloud_id          Atlassian cloud id of the Jira site; required with jira_mcp_server
  jira_base_url          e.g. "https://yourcompany.atlassian.net"; without jira_mcp_server
  jira_email             Atlassian account email used for Basic auth; without jira_mcp_server
  jira_token_secret      Name of the OpenHands secret holding the Jira API token
  jira_label             Label to watch for (default: "create-pr")
  max_new_per_run        Max conversations dispatched per run (default: 5)

The target GitHub repository is NOT configured here. Each Jira ticket body must include
the repo in "owner/repo" format; the spawned agent extracts it from the ticket text.

Runs against a local agent server (AGENT_SERVER_URL is injected) or on OpenHands Cloud
(OPENHANDS_CLOUD_API_URL / OPENHANDS_API_KEY / SANDBOX_ID are injected instead).
"""
import base64, json, os, re, sys, tempfile, urllib.error, urllib.parse, urllib.request, uuid
from datetime import datetime, timezone
from pathlib import Path

# ── Load config ───────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent
with open(_HERE / "config.json") as _f:
    _cfg = json.load(_f)

# Jira is reached through this connected MCP server when it is named, and through
# Jira's REST API with an API token otherwise.
JIRA_MCP_SERVER    = _cfg.get("jira_mcp_server")
JIRA_CLOUD_ID      = _cfg["jira_cloud_id"] if JIRA_MCP_SERVER else None
JIRA_BASE_URL      = None if JIRA_MCP_SERVER else _cfg["jira_base_url"].rstrip("/")
JIRA_EMAIL         = None if JIRA_MCP_SERVER else _cfg["jira_email"]
JIRA_TOKEN_SECRET  = _cfg.get("jira_token_secret", "JIRA_CLOUD_KEY")
JIRA_LABEL         = _cfg.get("jira_label", "create-pr")
MAX_NEW_PER_RUN    = int(_cfg.get("max_new_per_run", 5))
# How often a conversation that OpenHands Cloud failed to start is started again.
MAX_START_ATTEMPTS = 3

# Only a local run is handed the agent server's URL.
IS_LOCAL = bool(os.environ.get("AGENT_SERVER_URL"))

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
    key = os.environ.get("SESSION_API_KEY") or os.environ.get("OH_SESSION_API_KEYS_0", "")
    if IS_LOCAL:
        url = f"{os.environ['AGENT_SERVER_URL'].rstrip('/')}/api/settings/secrets/{name}"
    else:
        # Cloud: the OpenHands Cloud API serves the secrets of this run's sandbox.
        cloud_url = os.environ.get("OPENHANDS_CLOUD_API_URL", "").rstrip("/")
        sandbox_id = os.environ.get("SANDBOX_ID", "")
        url = f"{cloud_url}/api/v1/sandboxes/{sandbox_id}/settings/secrets/{name}"
    with urllib.request.urlopen(urllib.request.Request(
        url, headers={"X-Session-API-Key": key}
    )) as r:
        return r.read().decode().strip()


def fire_callback(status="COMPLETED", error=None):
    url = os.environ.get("AUTOMATION_CALLBACK_URL", "")
    if not url:
        return
    body = {"status": status, "run_id": os.environ.get("AUTOMATION_RUN_ID", "")}
    if error:
        body["error"] = error
    # Cloud runs are not given a callback key; they authenticate with their API key.
    api_key = (os.environ.get("AUTOMATION_CALLBACK_API_KEY")
               or os.environ.get("OPENHANDS_API_KEY", ""))
    try:
        urllib.request.urlopen(urllib.request.Request(
            url, data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
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


def call_mcp_tool(name, arguments):
    """Call a tool on the connected MCP server and return its text output.

    OpenHands makes the call with the credentials the user stored when connecting
    the server, so this run holds no Jira credential of its own.
    """
    server = urllib.parse.quote(JIRA_MCP_SERVER, safe="")
    result = _cloud_request("POST", f"/api/v1/mcp/servers/{server}/call-tool", {
        "name": name, "arguments": arguments,
    })
    if result.get("is_error"):
        raise RuntimeError(f"{name} failed: {str(result.get('text'))[:500]}")
    return result.get("text") or ""


def fetch_labeled_issues(auth_header):
    """Return open Jira issues with JIRA_LABEL.

    Uses the connected MCP server's JQL search, or the current v3 search endpoint.
    """
    search = {
        "jql":        f'labels = "{JIRA_LABEL}" AND statusCategory != Done',
        "fields":     ["key", "summary", "description", "status", "updated"],
        "maxResults": 50,
    }
    if JIRA_MCP_SERVER:
        text = call_mcp_tool("searchJiraIssuesUsingJql", {"cloudId": JIRA_CLOUD_ID, **search})
        try:
            return json.loads(text).get("issues", [])
        except (ValueError, AttributeError) as exc:
            raise RuntimeError(f"Unexpected Jira search result: {text[:500]}") from exc
    url  = f"{JIRA_BASE_URL}/rest/api/3/search/jql"
    body = json.dumps(search).encode()
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


def post_jira_comment(issue_key, auth_header, text):
    """Post a plain-text comment on a Jira issue."""
    if JIRA_MCP_SERVER:
        try:
            call_mcp_tool("addCommentToJiraIssue", {
                "cloudId": JIRA_CLOUD_ID, "issueIdOrKey": issue_key, "commentBody": text,
            })
        except RuntimeError as exc:
            print(f"Warning: failed to post Jira comment on {issue_key}: {exc}")
        return
    url  = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/comment"
    body = json.dumps({
        "body": {
            "type":    "doc",
            "version": 1,
            "content": [{
                "type":    "paragraph",
                "content": [{"type": "text", "text": text}],
            }],
        }
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
            r.read()
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace")
        print(f"Warning: failed to post Jira comment on {issue_key} ({exc.code}): {body_text[:200]}")


def _cloud_request(method, path, body=None):
    """Call the OpenHands Cloud API with the API key this run was given."""
    cloud_url = os.environ.get("OPENHANDS_CLOUD_API_URL", "").rstrip("/")
    req = urllib.request.Request(
        f"{cloud_url}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {os.environ.get('OPENHANDS_API_KEY', '')}",
            "Content-Type":  "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace")
        raise RuntimeError(f"OpenHands API {method} {path} failed {exc.code}: {body_text[:500]}") from exc
    return json.loads(raw) if raw.strip() else {}


def start_cloud_conversation(title, prompt):
    """Ask the OpenHands Cloud API to start a conversation.

    OpenHands Cloud runs it in its own sandbox with the user's LLM, MCP servers,
    secrets and connected git provider (e.g. the native GitHub integration).

    The API answers with the task that starts the conversation, not with a
    started conversation, so this returns the conversation's URL and that task's
    id for a later run to confirm (settle_cloud_starts).
    """
    cloud_url       = os.environ.get("OPENHANDS_CLOUD_API_URL", "").rstrip("/")
    conversation_id = uuid.uuid4().hex
    task = _cloud_request("POST", "/api/v1/app-conversations", {
        "conversation_id": conversation_id,
        "title":           title,
        "initial_message": {"content": [{"type": "text", "text": prompt}]},
    })
    if task.get("status") == "ERROR":
        raise RuntimeError(f"Starting a conversation failed: {task.get('detail') or 'no detail'}")
    return f"{cloud_url}/canvas/conversations/{conversation_id}", task.get("id")


def settle_cloud_starts(state, processed_keys, auth_header):
    """Confirm the conversations earlier runs asked OpenHands Cloud to start.

    A start can still fail after the API accepted it, for instance when its
    sandbox does not come up. Such an issue is released so the next poll starts
    it again, MAX_START_ATTEMPTS times in all; after that the failure is posted
    on the issue instead, so it is neither lost silently nor retried forever.
    """
    pending = state.get("pending_starts") or {}
    if not pending:
        return
    query = "&".join(f"ids={entry['task_id']}" for entry in pending.values())
    try:
        tasks = _cloud_request("GET", f"/api/v1/app-conversations/start-tasks?{query}")
    except RuntimeError as exc:
        # Confirming earlier starts must not keep this run from polling Jira.
        print(f"Warning: could not confirm earlier conversation starts: {exc}")
        return
    if not isinstance(tasks, list):
        return  # not the answer expected; leave them for the next run
    by_id = {task["id"]: task for task in tasks if task}

    for key, entry in list(pending.items()):
        task = by_id.get(entry["task_id"])
        # A task OpenHands no longer has says nothing about a failure, so it is
        # settled like a started one rather than risk a second conversation.
        status = task["status"] if task else "READY"
        if status not in ("READY", "ERROR"):
            continue  # still starting
        del pending[key]
        if status == "READY":
            continue
        detail = task.get("detail") or "no detail given"
        if entry.get("attempts", 1) < MAX_START_ATTEMPTS:
            print(f"Conversation for {key} did not start ({detail}); it will be started again")
            processed_keys.discard(key)
            state.setdefault("start_attempts", {})[key] = entry.get("attempts", 1)
        else:
            print(f"Conversation for {key} did not start ({detail}); giving up")
            post_jira_comment(
                key, auth_header,
                f"OpenHands could not start a conversation for this issue: {detail}",
            )
    state["pending_starts"]  = pending
    state["processed_keys"] = list(processed_keys)


# ── Timestamp helpers ─────────────────────────────────────────────────────────
def _parse_ts(ts):
    """Parse an ISO-8601 timestamp, normalising +HHMM → +HH:MM for Python < 3.11."""
    normalized = re.sub(r'([+-])(\d{2})(\d{2})$', r'\1\2:\3', ts)
    return datetime.fromisoformat(normalized)


# ── Main ──────────────────────────────────────────────────────────────────────
try:
    # A cloud run starts in a fresh sandbox, so without the KV store the processed
    # issues (and the first-run baseline) would be forgotten after every run.
    if not IS_LOCAL and not kv_available():
        raise RuntimeError("The automation KV store is required on OpenHands Cloud, "
                           "but AUTOMATION_KV_TOKEN is not set for this run.")

    auth_header = None
    if not JIRA_MCP_SERVER:
        jira_token  = get_secret(JIRA_TOKEN_SECRET)
        auth_header = "Basic " + base64.b64encode(
            f"{JIRA_EMAIL}:{jira_token}".encode()
        ).decode()
    elif IS_LOCAL:
        # Only OpenHands Cloud and Enterprise call a connected MCP server for a run.
        raise RuntimeError("jira_mcp_server needs OpenHands Cloud or Enterprise; "
                           "a local run reaches Jira with jira_token_secret.")

    state          = load_state()
    processed_keys = set(state.get("processed_keys", []))

    # On the very first run there is no baseline timestamp.  Record one now so
    # that all pre-existing issues (created before this moment) are silently
    # skipped — preventing a thundering-herd of conversations on first deploy.
    if "first_run_at" not in state:
        state["first_run_at"] = datetime.now(timezone.utc).isoformat()
        save_state(state)
        print(f"First run — baseline recorded at {state['first_run_at']}; "
              "issues created before this timestamp will be skipped.")

    first_run_at = _parse_ts(state["first_run_at"])

    if not IS_LOCAL:
        settle_cloud_starts(state, processed_keys, auth_header)

    print(f"Polling {JIRA_BASE_URL or JIRA_MCP_SERVER} for issues labeled '{JIRA_LABEL}'…")
    issues = fetch_labeled_issues(auth_header)
    print(f"Total matching issues : {len(issues)}")

    new_issues = [
        i for i in issues
        if i["key"] not in processed_keys
        and _parse_ts(i["fields"]["updated"]) >= first_run_at
    ]
    print(f"New (unprocessed, after baseline) : {len(new_issues)}")

    if len(new_issues) > MAX_NEW_PER_RUN:
        print(f"Capping at {MAX_NEW_PER_RUN} per run "
              f"({len(new_issues)} available); remainder picked up on next run.")
        new_issues = new_issues[:MAX_NEW_PER_RUN]

    if not new_issues:
        save_state(state)
        fire_callback("COMPLETED")
        sys.exit(0)

    # Start one agent conversation per new issue: via the agent server HTTP API on a
    # local run, via the OpenHands Cloud API (start_cloud_conversation) on a cloud run.
    if IS_LOCAL:
        agent_url   = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
        session_key = os.environ.get("SESSION_API_KEY") or os.environ.get("OH_SESSION_API_KEYS_0", "")

        # Fetch settings with encrypted secrets so llm.api_key is a Fernet token
        # (starts with gAAAAA) rather than the masked "**********" placeholder.
        # The conversation payload must include secrets_encrypted: True so the
        # agent-server decrypts it server-side; we never handle the plaintext key.
        with urllib.request.urlopen(urllib.request.Request(
            f"{agent_url}/api/settings",
            headers={"X-Session-API-Key": session_key, "X-Expose-Secrets": "encrypted"},
        )) as r:
            settings = json.loads(r.read())

        agent_settings = settings.get("agent_settings", {})
        agent_settings.pop("schema_version", None)
        mcp_config = agent_settings.pop("mcp_config", None)
        ctx = agent_settings.setdefault("agent_context", {})
        ctx.update({"load_public_skills": True, "load_user_skills": True, "load_project_skills": True})
        max_iterations = (settings.get("conversation_settings") or {}).get("max_iterations") or 1000

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
1. Find the target GitHub repository in the Description above. Look for a reference in
   "owner/repo" format (e.g. "acme-org/backend") or a full GitHub URL
   (e.g. "https://github.com/acme-org/backend"). Use that repository.
   If no repository is mentioned, create a file `jira/{key}/notes.md` with the issue
   details and print a message explaining that no GitHub repo was found in the ticket.
2. Clone the repository (e.g. https://github.com/<owner>/<repo>).
3. Create branch `{branch}` from the default branch.
4. Implement the changes described in the issue.
   If the description is vague or missing, create `jira/{key}/notes.md`
   with the issue key, summary, and description as a placeholder.
5. Commit, push the branch, and open a Pull Request:
   - Title : [{key}] {summary}
   - Body  : Reference the Jira issue key and describe the changes made.
6. Print the PR URL when done.
"""
        if IS_LOCAL:
            workdir = tempfile.mkdtemp(prefix=f"jira-{key.lower()}-")
            payload = {
                "secrets_encrypted":   True,
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
            if mcp_config:
                payload["mcp_config"] = mcp_config

            conv_req = urllib.request.Request(
                f"{agent_url}/api/conversations",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", "X-Session-API-Key": session_key},
            )
            with urllib.request.urlopen(conv_req) as r:
                conv = json.loads(r.read())

            conv_id  = conv.get("id")
            conv_url = f"{agent_url}/conversations/{conv_id}"
            print(f"✓ Conversation started for {key}: id={conv_id}")
        else:
            conv_url, start_task_id = start_cloud_conversation(f"[{key}] {summary}", prompt)
            if start_task_id:
                attempts = state.setdefault("start_attempts", {}).pop(key, 0) + 1
                state.setdefault("pending_starts", {})[key] = {
                    "task_id": start_task_id, "attempts": attempts,
                }
            print(f"✓ Conversation requested for {key}: {conv_url}")

        post_jira_comment(key, auth_header, f"I'm on it: {conv_url}")

        processed_keys.add(key)
        state["processed_keys"] = list(processed_keys)
        save_state(state)

    fire_callback("COMPLETED")

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    import traceback; traceback.print_exc()
    fire_callback("FAILED", str(e))
    sys.exit(1)
