# Slack → Jira Monitor: Setup Reference

Detailed reference for configuring and deploying the automation. Consult this
alongside SKILL.md when something isn't obvious from the overview.

---

## Secrets Setup

### SLACK_BOT_TOKEN

Required Slack bot OAuth scopes:

| Scope | Used for |
|---|---|
| `channels:history` | Read message history from public channels |
| `channels:join` | Bot auto-joins the monitored channel on each run |
| `channels:read` | List channels to resolve name → ID |
| `chat:write` | Post thread replies |
| `reactions:write` | Add ✅ reaction to messages |
| `groups:history` | Read message history from private channels (if needed) |

To create the bot:
1. Go to https://api.slack.com/apps → **Create New App** → **From scratch**
2. Under **OAuth & Permissions** → **Bot Token Scopes**, add the scopes above
3. **Install to Workspace** and copy the `xoxb-…` token
4. Register it as a secret: `SLACK_BOT_TOKEN`

### JIRA_CLOUD_KEY

This is an Atlassian API token, **not** the account password.

To generate:
1. Visit https://id.atlassian.com/manage-api-tokens
2. Click **Create API token**, give it a label (e.g. `openhands-automation`)
3. Copy the token value immediately (it is shown only once)
4. Register it as a secret: `JIRA_CLOUD_KEY`

Authentication in the script uses HTTP Basic auth:
```
Authorization: Basic base64(your-email@example.com:ATATT3x…)
```

---

## Finding a Slack Channel ID

Channel IDs look like `C0BFL769U6Q` and are stable even if the channel is renamed.

**Option A — API call (recommended for automation)**
```bash
curl -s "https://slack.com/api/conversations.list?types=public_channel&limit=200" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  | python3 -c "
import json, sys
for c in json.load(sys.stdin).get('channels', []):
    print(c['id'], c['name'])
" | grep bugs   # replace 'bugs' with target channel name
```

**Option B — Slack UI**
Open the channel in Slack → right-click the channel name → **Copy link**. The URL ends with the channel ID: `https://app.slack.com/client/T.../C0BFL769U6Q`.

**Option C — Private channels**
Change `types=public_channel` to `types=private_channel` and ensure the bot token has the `groups:history` scope.

---

## Discovering Jira Issue Types

Every Jira project has its own issue type configuration. Fetch the list before setting `JIRA_ISSUE_TYPE`:

```bash
export JIRA_SITE="https://acme.atlassian.net"
export JIRA_EMAIL="you@example.com"
export JIRA_TOKEN="<your-api-token>"
export JIRA_PROJECT="KAN"

AUTH=$(python3 -c "
import base64, os
creds = f\"{os.environ['JIRA_EMAIL']}:{os.environ['JIRA_TOKEN']}\"
print('Basic ' + base64.b64encode(creds.encode()).decode())
")

curl -s "$JIRA_SITE/rest/api/3/project/$JIRA_PROJECT" \
  -H "Authorization: $AUTH" \
  -H "Accept: application/json" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('Project:', d.get('name'))
print('Issue types:', [t['name'] for t in d.get('issueTypes', [])])
"
```

Common types by project style:

| Project style | Typical types |
|---|---|
| Scrum | Epic, Story, Task, Bug, Subtask |
| Kanban | Epic, Feature, Task, Subtask |
| Bug tracker | Bug, Improvement, Task |
| Custom | Varies — always check |

---

## KV Store Behavior

The automation uses the automation service's built-in KV store to persist the last-processed Slack message timestamp across runs.

**Key name**: Set via `KV_KEY` in `main.py`. Use a unique name per deployment (e.g. `slack_jira_monitor_bugs`, `slack_jira_monitor_security`) to avoid collisions if multiple automations monitor different channels.

**First-run default**: When no KV entry exists, `last_ts` defaults to `time.time() - 300` (5 minutes ago). This avoids flooding Jira with historical messages on the first run while still catching messages that arrived just before deployment. To process older messages on first run, change `- 300` to a larger value (e.g. `- 86400` for the past 24 hours) or set `"0"` to process all history.

**Token lifetime**: `AUTOMATION_KV_TOKEN` is a short-lived JWT scoped to a single run. It is injected automatically by the automation service and should never be hardcoded or reused across runs.

**Resetting state**: To force reprocessing of a time window, update the KV value directly using the management API key:

```bash
curl -s -X PUT "http://localhost:18001/api/automation/v1/kv/slack_jira_monitor_bugs" \
  -H "Authorization: Bearer $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '"1783360000"'   # Unix timestamp to reset to
```

---

## Automation Management API

### Check automation status
```bash
curl -s "http://localhost:18001/api/automation/v1/$AUTOMATION_ID" \
  -H "Authorization: Bearer $OPENHANDS_AUTOMATION_API_KEY" | python3 -m json.tool
```

### List recent runs
```bash
curl -s "http://localhost:18001/api/automation/v1/$AUTOMATION_ID/runs?limit=10" \
  -H "Authorization: Bearer $OPENHANDS_AUTOMATION_API_KEY" \
  | python3 -c "
import json, sys
for r in json.load(sys.stdin).get('runs', []):
    print(r['id'][:8], r['status'], r.get('error_detail') or '')
"
```

### Pause / resume
```bash
# Pause
curl -s -X PATCH "http://localhost:18001/api/automation/v1/$AUTOMATION_ID" \
  -H "Authorization: Bearer $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Resume
curl -s -X PATCH "http://localhost:18001/api/automation/v1/$AUTOMATION_ID" \
  -H "Authorization: Bearer $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

### Delete
```bash
curl -s -X DELETE "http://localhost:18001/api/automation/v1/$AUTOMATION_ID" \
  -H "Authorization: Bearer $OPENHANDS_AUTOMATION_API_KEY"
```

---

## Cron Schedule Reference

| Schedule | Meaning |
|---|---|
| `*/5 * * * *` | Every 5 minutes (default) |
| `*/10 * * * *` | Every 10 minutes |
| `0 * * * *` | Every hour on the hour |
| `0 9-17 * * 1-5` | Every hour, 9am–5pm, weekdays only |
| `0 9 * * 1-5` | Once at 9am on weekdays |

All times are UTC unless `timezone` is set in the trigger config.

---

## Troubleshooting

### `not_in_channel` from Slack API
The bot has not joined the channel. The script calls `conversations.join` automatically on each run, but this requires the `channels:join` scope. Verify the scope is granted and re-install the app if you added it after the initial install.

### `Specify a valid issue type` from Jira
`JIRA_ISSUE_TYPE` does not exist in the project. Run the issue-type discovery command above and update `main.py`.

### `401 Unauthorized` from Jira
The `JIRA_CLOUD_KEY` secret or `JIRA_EMAIL` is incorrect. Verify the email exactly matches the Atlassian account that owns the API token.

### Run shows `COMPLETED` instantly with no messages processed
The KV `last_ts` is set to a time after all existing messages. The automation is working correctly and will pick up the next new message. To test immediately, post a message with the trigger phrase and dispatch a manual run.

### Run shows `FAILED` with a Python traceback
Retrieve the bash command output for the failing run:
```bash
SESSION_KEY=$(cat ~/.openhands/agent-canvas/api-key.txt)
RUN_BASH_ID=$(curl -s "http://localhost:18001/api/automation/v1/$AUTOMATION_ID/runs?limit=1" \
  -H "Authorization: Bearer $OPENHANDS_AUTOMATION_API_KEY" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['runs'][0]['bash_command_id'])")

curl -s "http://localhost:18000/api/bash/bash_events/$RUN_BASH_ID" \
  -H "X-Session-API-Key: $SESSION_KEY" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('command','')[-300:])"
```

---

## Extending the Automation

### Monitor multiple channels
Deploy separate automations with different `SLACK_CHANNEL_ID`, `KV_KEY`, and automation names. Each automation runs independently.

### Different trigger phrases
Change `TRIGGER_PHRASE`. Examples: `"!ticket"`, `"#feature"`, `"ALERT:"`, `"[bug]"`. The match is case-insensitive substring.

### Add Jira labels or priority
Extend the `create_jira_issue` payload's `"fields"` dict:
```python
"fields": {
    ...
    "labels":   ["slack-import", "needs-triage"],
    "priority": {"name": "High"},
}
```

### Notify a different Slack channel
Replace the `chat.postMessage` call's `"channel"` with a different channel ID to route replies elsewhere (e.g. a `#jira-tickets` digest channel).

### Custom reply format
Edit the `text` field in the `chat.postMessage` call. Slack mrkdwn reference: `*bold*`, `_italic_`, `<URL|text>`, `\n` for newlines.
