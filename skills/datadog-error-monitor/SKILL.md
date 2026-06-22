---
name: datadog-error-monitor
description: >
  This skill should be used when the user asks to "monitor Datadog for errors",
  "watch Datadog logs for error spikes", "investigate Datadog errors automatically",
  "alert on new or recurring errors in Datadog", or "set up automated error
  monitoring with Datadog and Slack". Guides the user through creating a cron
  automation that polls Datadog logs every 15 minutes, maintains a library of
  known error patterns, and triggers an OpenHands investigation conversation when
  new or spiking errors are detected. The investigation agent categorizes unknown
  errors, investigates root causes in local codebases, optionally creates PRs,
  and posts a concise summary to Slack.
triggers:
  - /datadog-monitor:setup
---

# Datadog Error Monitor

Create a cron automation that polls Datadog logs every 15 minutes.

On each run the script:
1. Queries Datadog using a configured log filter (e.g. `service:(api OR worker) status:error`)
2. Matches log events against a library of known error patterns (regex-based, stored in a state file)
3. Tracks hit counts per pattern across runs
4. When **new/uncategorized logs** or a **significant count spike** is detected,
   starts a single OpenHands investigation conversation

When an investigation conversation runs it:
- Categorizes uncategorized logs into named patterns and writes them to the state file
- Investigates root causes in the configured local codebases
- Creates a PR only when highly confident of a code-level fix
- Posts a concise summary to the configured Slack channel

> **Local mode only.** Monitored code repositories must be cloned on the same
> machine running OpenHands.

---

## Prerequisites

### Required secrets

Verify all of the following are set in **OpenHands Settings → Secrets**:

| Secret name | Description |
|---|---|
| `DD_API_KEY` | Datadog API key |
| `DD_APP_KEY` | Datadog Application key (required for log search — distinct from the API key) |
| `SLACK_BOT_TOKEN` | Slack bot token with `chat:write` scope |

Check with:
```bash
[ -n "$DD_API_KEY" ]      && echo "DD_API_KEY is set"      || echo "DD_API_KEY is NOT set"
[ -n "$DD_APP_KEY" ]      && echo "DD_APP_KEY is set"      || echo "DD_APP_KEY is NOT set"
[ -n "$SLACK_BOT_TOKEN" ] && echo "SLACK_BOT_TOKEN is set" || echo "SLACK_BOT_TOKEN is NOT set"
```

If any are missing, inform the user and stop — the automation cannot function without them.

Git host token(s) are confirmed per-repository in Step 5.

### Optional secret

| Secret name | Default | Purpose |
|---|---|---|
| `OPENHANDS_URL` | `http://localhost:8000` | Base URL for conversation links |

---

## Setup Workflow

Follow these steps in order.

### Step 1 — Verify Datadog credentials

```bash
DD_SITE_TMP="datadoghq.com"
curl -s -X POST "https://api.${DD_SITE_TMP}/api/v2/logs/events/search" \
  -H "DD-API-KEY: $DD_API_KEY" \
  -H "DD-APPLICATION-KEY: $DD_APP_KEY" \
  -H "Content-Type: application/json" \
  -d '{"filter":{"query":"*","from":"now-1m","to":"now"},"page":{"limit":1}}' \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
if 'errors' in d:
    print('ERROR:', d['errors'])
elif 'data' in d:
    print('OK — credentials valid, got', len(d['data']), 'sample event(s)')
else:
    print('Unexpected response:', list(d.keys()))
"
```

- If `DD_API_KEY` or `DD_APP_KEY` is missing → tell the user and stop.
- If the API returns a 403 → tell the user to check both keys in Datadog:
  *Organization Settings → API Keys* (for `DD_API_KEY`) and
  *Organization Settings → Application Keys* (for `DD_APP_KEY`).

### Step 2 — Confirm Datadog site

Ask: *"What is your Datadog site?*
*(Press Enter for the default: `datadoghq.com`)*
*Other options: `datadoghq.eu`, `us3.datadoghq.com`, `us5.datadoghq.com`, `ap1.datadoghq.com`"*

Record as `DD_SITE`. Default: `"datadoghq.com"`.

Re-run the Step 1 credential check substituting the confirmed site.

### Step 3 — Collect the Datadog log query

Ask: *"What Datadog log query should be monitored? This filter runs every 15 minutes.*
*Example: `service:(deploy OR runtime-api) status:error`*
*Example: `service:payment-api (@http.status_code:5* OR status:error)`*
*Tip: develop and test your query in the Datadog Logs Explorer first."*

Run a test query to show the user what they will be monitoring:
```bash
USER_QUERY="REPLACE_WITH_USER_QUERY"
DD_SITE="REPLACE_WITH_DD_SITE"
curl -s -X POST "https://api.${DD_SITE}/api/v2/logs/events/search" \
  -H "DD-API-KEY: $DD_API_KEY" \
  -H "DD-APPLICATION-KEY: $DD_APP_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"filter\": {\"query\": \"${USER_QUERY}\", \"from\": \"now-15m\", \"to\": \"now\"},
    \"sort\": \"-timestamp\",
    \"page\": {\"limit\": 5}
  }" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if 'errors' in d:
    print('ERROR:', d['errors'])
    sys.exit(1)
events = d.get('data', [])
print(f'{len(events)} event(s) in the last 15 minutes (showing up to 5):')
for e in events:
    attrs = e.get('attributes', {})
    ts = attrs.get('timestamp', '')
    msg = (attrs.get('message') or attrs.get('error', {}).get('message') or '')[:120]
    svc = attrs.get('service', '')
    print(f'  [{ts}] [{svc}] {msg}')
"
```

Show the output to the user. If the query looks correct, record as `DD_QUERY`.
If they want to adjust it, iterate until they are satisfied.

### Step 4 — Collect Slack configuration

Ask: *"Which Slack channel should investigation summaries be posted to?*
*Provide the channel name (e.g. `#errors-alerts`) or ID (e.g. `C0123456789`)."*

Verify the bot token:
```bash
curl -s https://slack.com/api/auth.test \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('Bot:', d.get('user')) if d.get('ok') else print('ERROR:', d.get('error'))"
```

If the user provided a channel name, resolve it to an ID:
```bash
CHANNEL_NAME="REPLACE_WITH_NAME_WITHOUT_HASH"
curl -s "https://slack.com/api/conversations.list?types=public_channel,private_channel&limit=200&exclude_archived=true" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
if not data.get('ok'):
    print('ERROR:', data.get('error'))
    sys.exit(1)
for ch in data.get('channels', []):
    if ch['name'] == '${CHANNEL_NAME}'.lstrip('#'):
        print(ch['id'])
        break
else:
    print('Channel not found — provide the channel ID directly (right-click channel → Copy link)')
"
```

Record as `SLACK_CHANNEL_ID`.

### Step 5 — Collect monitored repositories

Ask: *"Which local code repositories should the investigation agent have access to?*
*These must already be cloned on this machine.*
*For each, provide the absolute path and the git host (GitHub / GitLab / Bitbucket).*
*Example: `/home/user/projects/my-api` (GitHub)"*

For each repository:

**a) Verify the path is a git repo:**
```bash
cd /path/to/repo && git remote -v && git log --oneline -1
```

**b) Confirm the git host token is available:**

| Host | Required secret | Verification |
|---|---|---|
| GitHub | `GITHUB_PERSONAL_ACCESS_TOKEN` | `curl -s https://api.github.com/user -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \| python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('login', d.get('message')))"` |
| GitLab | `GITLAB_TOKEN` | `curl -s https://gitlab.com/api/v4/user -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \| python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('username', d.get('message')))"` |
| Bitbucket | `BITBUCKET_TOKEN` | `curl -s https://api.bitbucket.org/2.0/user --user "$BITBUCKET_TOKEN" \| python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('username', d.get('error')))"` |

If the required token is missing, inform the user. The investigation agent
can still investigate code but will not be able to create PRs until the token
is added to OpenHands Settings → Secrets.

**c) Extract the remote identifier** from `git remote get-url origin`.

Build `REPO_CONFIGS` as a Python list literal:
```python
REPO_CONFIGS: list[dict] = [
    {"path": "/path/to/repo1", "host": "github",    "remote": "owner/repo1"},
    {"path": "/path/to/repo2", "host": "gitlab",    "remote": "owner/repo2"},
    {"path": "/path/to/repo3", "host": "bitbucket", "remote": "owner/repo3"},
]
```

### Step 6 — Tune parameters

Ask about the following settings. Offer the defaults and accept Enter to keep them:

| Parameter | Default | Prompt |
|---|---|---|
| `MAX_UNKNOWN_LOGS` | `100` | *"Max uncategorized log samples to send to the agent per run?"* |
| `EXAMPLES_PER_PATTERN` | `3` | *"How many example logs to keep per error pattern?"* |
| `SPIKE_MULTIPLIER` | `3.0` | *"Spike threshold — alert when count exceeds this multiple of the rolling 3-run average?"* |

### Step 7 — Dry run confirmation

Run the Step 3 query one final time with a 15-minute window and show the user:
- Total number of matching events
- The first 3 example log messages

Ask: *"This is what the automation will monitor every 15 minutes. Does it look right?*
*Shall I create the automation?"*

If the user wants changes, return to Step 3.

### Step 8 — Generate the automation script

Read `scripts/main.py` from this skill's directory and **copy it verbatim**.
Apply exactly the following constant substitutions near the top of the file:

> **Do not reimplement or hand-write a replacement script.** Only substitute the
> configuration constants below — all other logic must remain unchanged.

| Placeholder | Replace with |
|---|---|
| `DD_QUERY = "service:(deploy OR runtime-api) status:error"` | `DD_QUERY = "{dd_query}"` |
| `DD_SITE = "datadoghq.com"` | `DD_SITE = "{dd_site}"` |
| `SLACK_CHANNEL_ID = "C0123456789"` | `SLACK_CHANNEL_ID = "{channel_id}"` |
| `REPO_CONFIGS: list[dict] = []` | `REPO_CONFIGS: list[dict] = {repo_configs_literal}` |
| `MAX_UNKNOWN_LOGS = 100` | `MAX_UNKNOWN_LOGS = {max_unknown}` |
| `EXAMPLES_PER_PATTERN = 3` | `EXAMPLES_PER_PATTERN = {examples_per}` |
| `SPIKE_MULTIPLIER = 3.0` | `SPIKE_MULTIPLIER = {multiplier}` |
| `DEFAULT_OPENHANDS_URL = "http://localhost:8000"` | `DEFAULT_OPENHANDS_URL = "{url}"` (keep default if user has no preference) |

Write the script to a temporary build directory:
```bash
mkdir -p /tmp/dd-monitor-build
# copy and substitute scripts/main.py → /tmp/dd-monitor-build/main.py
```

Validate syntax and confirm substitutions:
```bash
python3 -m py_compile /tmp/dd-monitor-build/main.py && echo "Syntax OK"
grep -n 'DD_QUERY = '         /tmp/dd-monitor-build/main.py
grep -n 'DD_SITE = '          /tmp/dd-monitor-build/main.py
grep -n 'SLACK_CHANNEL_ID = ' /tmp/dd-monitor-build/main.py
grep -n 'REPO_CONFIGS'        /tmp/dd-monitor-build/main.py
grep -n 'def get_secret'      /tmp/dd-monitor-build/main.py
grep -n 'def main'            /tmp/dd-monitor-build/main.py
```

If any check fails, re-copy the template and redo the substitutions.

### Step 9 — Package and upload

Determine the Automation backend URL from the `<RUNTIME_SERVICES>` block in
your system context.

```bash
tar -czf /tmp/dd-monitor.tar.gz -C /tmp/dd-monitor-build .

OPENHANDS_HOST="<automation-url-from-runtime-services>"

TARBALL_PATH=$(curl -s -X POST \
  "${OPENHANDS_HOST}/api/automation/v1/uploads?name=datadog-error-monitor" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/gzip" \
  --data-binary @/tmp/dd-monitor.tar.gz \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['tarball_path'])")

echo "Uploaded: $TARBALL_PATH"
```

### Step 10 — Create the automation

```bash
curl -s -X POST "${OPENHANDS_HOST}/api/automation/v1" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Datadog Error Monitor\",
    \"trigger\": {\"type\": \"cron\", \"schedule\": \"*/15 * * * *\"},
    \"tarball_path\": \"$TARBALL_PATH\",
    \"entrypoint\": \"python3 main.py\",
    \"timeout\": 120
  }" | python3 -m json.tool
```

Record the returned `id`.

### Step 11 — Confirm and hand off

Tell the user:

> ✅ **Datadog Error Monitor** is running!
>
> - **Automation ID:** `{id}`
> - **Query:** `{dd_query}`
> - **Site:** `{dd_site}`
> - **Alert channel:** `{slack_channel}`
> - **Repos:** `{repo_paths}`
> - **Schedule:** every 15 minutes (`*/15 * * * *`)
> - **State file:** `~/.openhands/workspaces/automation-state/dd_monitor_{id}.json`
>
> **What happens next:**
> The first run will treat all matching logs as uncategorized and start an
> investigation conversation. The agent will build the initial pattern library.
> After a few runs, the system converges on a stable baseline and only alerts
> on new error types or significant spikes.
>
> You can inspect or edit the state file at any time to adjust patterns, remove
> stale ones, or reset the system entirely by deleting the file.

---

## Runtime Behaviour (per 15-min poll)

Each cron run executes `main.py` with a 120-second timeout:

1. **Loads state** — picks up any pattern updates written by the previous agent run
2. **Queries Datadog** — window: `[last_poll − 60 s overlap, now − 10 s]`
3. **Matches logs** — each event tested against `known_patterns` regexes
4. **Updates history** — appends counts to each pattern's `run_history` (capped at 20); refreshes `examples` and `last_seen`
5. **Checks active conversation** — if one is running, saves updated state and exits; spike evaluation is skipped until the investigation finishes
6. **Evaluates triggers:**
   - Unknown logs (count ≥ 1) → trigger
   - Pattern spike (`current > mean(last 3 runs) × SPIKE_MULTIPLIER`) → trigger
7. **If triggered:** builds the investigation prompt and starts one OpenHands conversation; records its ID in state
8. **Saves state** and fires the completion callback

The investigation agent (asynchronous):
- Categorizes unknown logs into named patterns → writes back to state file
- Investigates spiking patterns in the configured repos
- Creates PRs only if highly confident of a code-level fix
- Posts a Slack summary with findings

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Datadog API error 403` | `DD_APP_KEY` invalid or wrong site | Verify both keys in Datadog Org Settings; re-check `DD_SITE` |
| No events returned | Query too narrow, wrong site, or no recent errors | Test query in Datadog Logs Explorer UI |
| Agent creates very specific patterns | LLM being over-literal | Edit state file to merge narrow patterns; the regex quality rules in the prompt help prevent this |
| Spike keeps re-triggering | Pattern regex too broad (every log matches) | Tighten the regex in the state file; valid Python regex only |
| Investigation never finishes | Agent stuck on a complex codebase | View conversation in OpenHands UI; clear `active_conversation` in state file to unblock next run |
| Slack not receiving messages | `SLACK_BOT_TOKEN` missing `chat:write` or bot not in channel | Re-install app with correct scope; invite bot to channel |
| State file write conflict | Script and agent writing concurrently (rare) | At worst one count update is lost; recovers automatically next run |
