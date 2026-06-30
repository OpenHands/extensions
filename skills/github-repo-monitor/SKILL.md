---
name: github-repo-monitor
description: >
  This skill should be used when the user asks to "monitor a GitHub repository",
  "watch GitHub for issues or PRs", "respond to @OpenHands mentions on GitHub",
  "set up an OpenHands GitHub integration", "trigger OpenHands from a GitHub
  comment", or "poll a GitHub repo for a trigger phrase". Guides the user
  through creating a cron automation that polls a single repository and starts
  an OpenHands conversation whenever a configurable trigger phrase is detected
  in an issue or PR comment.
triggers:
  - /github-monitor:poll
---

# GitHub Repository Monitor

Create a cron automation that polls a single GitHub repository on a
configurable schedule (default: every minute).

When a comment on an issue or PR contains the **trigger phrase**
(default: `@OpenHands`) it:

1. Posts a GitHub comment acknowledging the request with a conversation link.
2. Creates an OpenHands conversation pre-loaded with the issue/PR title, body,
   labels, and recent comment history for full context.
3. Posts a summary GitHub comment when the conversation finishes.

On every subsequent run:
- New trigger comments on an already-tracked issue/PR are forwarded to the
  running conversation (or re-open a previously closed one).
- When a conversation goes idle/finished/error the agent's final response
  is posted back as a GitHub comment.

> **Local mode only.** This automation targets the local OpenHands setup
> (`dev:automation` stack). A cloud/webhook variant is out of scope here.

---

## Prerequisites

### Required secret

Verify that the following secret is set in **OpenHands Settings → Secrets**
before proceeding:

| Secret name | Token type | Minimum permissions |
|---|---|---|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Classic PAT | `repo` (private repos) or `public_repo` (public repos) |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Fine-grained PAT | Issues: Read and Write |

Check with any shell-appropriate HTTP client or a short Python script. The important part is to call `GET https://api.github.com/user` with `Authorization: Bearer <token>` and `Accept: application/vnd.github+json`, then read either the authenticated login or the error message.

Example Python snippet:
```python
import json
import urllib.request

token = "<GITHUB_PERSONAL_ACCESS_TOKEN>"
req = urllib.request.Request(
    "https://api.github.com/user",
    headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    },
)
with urllib.request.urlopen(req) as response:
    data = json.load(response)
print(data.get("login") or data.get("message"))
```

If the token is missing, inform the user and stop — the automation cannot
function without GitHub credentials.

### Optional secret

| Secret name | Default | Purpose |
|---|---|---|
| `OPENHANDS_URL` | `http://localhost:8000` | Base URL used to build conversation links in GitHub comments |

---

## Setup Workflow

Follow these steps in order.

### Step 1  -  Verify GITHUB_PERSONAL_ACCESS_TOKEN

Fetch the secret and run the `curl` check above.

- If the secret is absent: tell the user
  *"GITHUB_PERSONAL_ACCESS_TOKEN is not set. Please add it in OpenHands Settings → Secrets
  (classic PAT with `repo` or `public_repo` scope, or a fine-grained PAT
  with Issues: Read and Write)."* Then stop.

- If the API returns a non-200 or `{"message": "Bad credentials"}`:
  tell the user the token is invalid and ask them to update it.

### Step 2  -  Collect repository

Ask the user: *"Which GitHub repository should be monitored?
(Format: `owner/repo`, e.g. `microsoft/vscode`)"*

Validate access and write permissions with any shell-appropriate HTTP client or Python. The important part is to call `GET https://api.github.com/repos/{owner}/{repo}` with the same bearer token and inspect either `message` or `permissions`.

Example Python snippet:
```python
import json
import urllib.request

owner_repo = "{owner}/{repo}"
token = "<GITHUB_PERSONAL_ACCESS_TOKEN>"
req = urllib.request.Request(
    f"https://api.github.com/repos/{owner_repo}",
    headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    },
)
with urllib.request.urlopen(req) as response:
    data = json.load(response)
if "message" in data:
    print("ERROR:", data["message"])
else:
    print(f"Accessible. Private: {data.get('private')}. Permissions: {data.get('permissions', {})}")
```

- If `message: Not Found` or `message: Bad credentials` →
  inform the user and ask them to check the repo name and token.
- If the repo is private and `permissions.push` is `false` →
  inform the user the token does not have write access and comments will fail.
- If the check passes, record `REPO = "{owner}/{repo}"`.

### Step 3  -  Collect trigger phrase

Ask the user: *"What trigger phrase should OpenHands respond to?
(Press Enter to use the default: `@OpenHands`)"*

Accepted values: any non-empty string unlikely to appear by accident.

Record as `TRIGGER_PHRASE`. Default: `"@openhands"`.

### Step 4  -  Collect allowed GitHub logins

Ask the user: *"Which GitHub users may trigger this automation?
Press Enter to allow only the authenticated `GITHUB_PERSONAL_ACCESS_TOKEN` owner.
You may also provide comma-separated GitHub logins, or `*` to allow any
non-bot commenter on the monitored repository."*

Map the answer to `ALLOWED_GITHUB_LOGINS`:

| User answer | `ALLOWED_GITHUB_LOGINS` value |
|---|---|
| Empty/default | `["<TOKEN_OWNER>"]` |
| `enyst,tofarr` | `["enyst", "tofarr"]` |
| `*` | `["*"]` |

Default to token-owner-only unless the user explicitly chooses a broader
allowlist. Record as `ALLOWED_GITHUB_LOGINS`.

### Step 5  -  Collect event types

Ask the user: *"Which event types should be monitored?
Choose one or more:*
  *1. Issue and PR comments (default)*
  *2. PR inline review comments*
  *3. Both*
*(Press Enter to accept the default: issue and PR comments.)"*

Map the choice to the `EVENT_TYPES` list:

| Choice | `EVENT_TYPES` value |
|---|---|
| 1 (default) | `["issue_comment"]` |
| 2 | `["pr_review_comment"]` |
| 3 | `["issue_comment", "pr_review_comment"]` |

### Step 6  -  Collect cron schedule

Ask the user: *"How often should the automation poll GitHub?
(Press Enter for the default: every minute.
Use a cron expression for a different interval, e.g.:
`*/5 * * * *` = every 5 minutes,
`0 * * * *` = every hour)"*

Default: `* * * * *` (every minute).

Record as `CRON_SCHEDULE`.

### Step 7  -  Generate the automation script

Read `scripts/main.py` from this skill's directory. Apply exactly five
constant substitutions near the top of the file:

| Placeholder | Replace with |
|---|---|
| `REPO = "owner/repo"` | `REPO = "{owner_repo}"` |
| `TRIGGER_PHRASE = "@openhands"` | `TRIGGER_PHRASE = "{trigger_phrase_lower}"` |
| `EVENT_TYPES = ["issue_comment"]` | `EVENT_TYPES = {event_types_list}` |
| `ALLOWED_GITHUB_LOGINS = ["<TOKEN_OWNER>"]` | `ALLOWED_GITHUB_LOGINS = {allowed_logins_list}` |
| `DEFAULT_OPENHANDS_URL = "http://localhost:8000"` | `DEFAULT_OPENHANDS_URL = "{url}"` (keep default if the user has no preference) |

Write the customised script to a build directory under the system temporary
directory, for example `Path(tempfile.gettempdir()) / "github-monitor-build" / "main.py"`
in Python. Use the file editor or a short Python helper so the path works on
Windows, macOS, and Linux without leaving temp files in the repository.

Validate syntax before packaging using the current environment's Python launcher (`python`, `python3`, or `py`):
```text
<python-launcher> -m py_compile <build-dir>/main.py
```

Fix any syntax errors before proceeding.

### Step 8  -  Package and upload

Determine the Automation backend URL and auth from the `<RUNTIME_SERVICES>`
block in your system context:
- Use the **Automation backend** `url_from_agent` as `OPENHANDS_HOST`
- Auth: `X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY`

If no Automation backend is listed in `<RUNTIME_SERVICES>`, stop and tell
the user to start the full automation stack.

Prefer the reusable helper script at `scripts/package_upload.py`. It creates
the tarball under the system temporary directory and prints JSON containing the
remote `tarball_path` plus the local tarball path for debugging.

```text
<python-launcher> skills/github-repo-monitor/scripts/package_upload.py --build-dir <build-dir> --openhands-host <automation-url-from-runtime-services> --upload-name github-repo-monitor
```

Record the returned `tarball_path` as `TARBALL_PATH`.

### Step 9  -  Create the automation

Set `entrypoint` to the same launcher that worked in Step 7 (for example `python main.py`, `python3 main.py`, or `py -3 main.py`). Then call the reusable helper script at `scripts/create_automation.py`:

```text
<python-launcher> skills/github-repo-monitor/scripts/create_automation.py --openhands-host <automation-url-from-runtime-services> --name "GitHub Monitor: {owner}/{repo}" --schedule "{cron_schedule}" --tarball-path <TARBALL_PATH> --entrypoint "<python-launcher> main.py" --timeout 55
```

Use shell-appropriate quoting for arguments that contain spaces. Record the
returned `id`.

### Step 10  -  Confirm

Tell the user:

> ✅ **GitHub Repository Monitor** is running!
>
> - Automation ID: `{id}`
> - Repository: `{owner}/{repo}`
> - Trigger phrase: `{phrase}`
> - Event types: `{event_types}`
> - Allowed GitHub logins: `{allowed_logins}`
> - Polling schedule: `{cron_schedule}`
> - State file: `~/.openhands/workspaces/automation-state/github_poller_{id}.json`
>
> From an allowed GitHub login, post a comment containing `{phrase}` on any
> issue or PR in `{owner}/{repo}` to test it. OpenHands will acknowledge with
> a comment and a link to the new conversation.

---

## Runtime Behaviour (per poll)

Each cron run executes `main.py`, which:

1. **Loads state** from the JSON file (see `references/state-schema.md`).
2. **Resolves and validates GITHUB_PERSONAL_ACCESS_TOKEN** — aborts immediately if absent or invalid.
3. **Polls for new events** since the previous `last_poll` timestamp:
   - `GET /repos/{owner}/{repo}/issues/comments?since=…` for `issue_comment`
   - `GET /repos/{owner}/{repo}/pulls/comments?since=…` for `pr_review_comment`
4. **Processes matching comments** in chronological order:
   - Skips bot accounts (login ending in `[bot]`) to avoid feedback loops.
   - Skips already-processed comment IDs.
   - Skips comments from logins outside `ALLOWED_GITHUB_LOGINS`.
   - Checks body for the trigger phrase (case-insensitive).
   - Extracts the issue/PR number from the comment URL.
5. **For each trigger comment**, per issue/PR:
   - **Active conversation** → forwards the new comment directly.
   - **Closed conversation** → tries to re-open it; falls back to creating
     a new conversation if the old one is unreachable.
   - **No conversation** → fetches full context (title, body, labels, last
     10 comments) and creates a new conversation with a detailed prompt.
   - Posts a GitHub comment: *"🤖 OpenHands is on it! View progress: {url}"*
6. **Checks active conversations** for completion:
   - If `status ∈ {idle, finished, error, stuck}` and enough time has passed
     since creation (debounce), fetches the agent's final response and posts
     it as a GitHub comment. Marks the conversation `closed`.
7. **Saves state** and fires the completion callback.

---

## Additional Resources

### Reference Files

- **`references/state-schema.md`**  -  State JSON schema, field definitions,
  and conversation lifecycle diagram.
- **`references/github-api.md`**  -  GitHub API endpoint reference, token
  scopes, rate limits, and common error codes.

### Script Template

- **`scripts/main.py`**  -  The complete automation script. Customise the five
  constants at the top (`REPO`, `TRIGGER_PHRASE`, `EVENT_TYPES`,
  `ALLOWED_GITHUB_LOGINS`, `DEFAULT_OPENHANDS_URL`) before packaging.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Bot doesn't respond to comments | `GITHUB_PERSONAL_ACCESS_TOKEN` missing or wrong scopes | Verify token with `curl /user`; check scopes in Step 1 |
| "Bad credentials" in run logs | Token expired | Rotate token and update the secret in Settings |
| 404 on repo access | Repo name wrong or token has no access | Re-check `owner/repo` spelling; add token as collaborator |
| Comments posted but no conversation created | Agent server URL wrong | Check `OPENHANDS_URL` secret and `AGENT_SERVER_URL` env var |
| Same comment processed twice | `processed_comment_ids` cleared | State file was deleted; harmless but duplicate comment may appear |
| Summary never posted | Conversation stuck in `running` | Open the conversation in the OpenHands UI; agent may need input |
| No events detected after first run | `last_poll` in the future | Delete the state file to reset; it will be recreated on next run |
