---
name: auto-triage-bugs-from-slack
description: This skill should be used when the user asks to "monitor a Slack channel and create Jira issues", "automatically file Jira tickets from Slack messages", "create a Jira bug from Slack", "watch a channel for bugs and open tickets", "set up a Slack to Jira automation", or "turn Slack messages into Jira issues". Deploys a cron-based polling automation that watches a Slack channel for messages containing a trigger phrase, creates a Jira issue for each match, posts the Jira ticket link as a thread reply, and adds a ✅ reaction to the original message.
---

# Slack → Jira Monitor Automation

Deploys a cron-based automation that polls a Slack channel on a schedule. For every new parent message containing a configurable trigger phrase, it:

1. Creates a Jira issue (Task or other type) in the specified project
2. Replies to the Slack thread with a link to the new Jira ticket
3. Adds a ✅ (`white_check_mark`) reaction to the original message

State is tracked in the automation KV store so messages are never double-processed.

---

## Required Secrets

Two secrets must be registered in the agent server before deploying:

| Secret name | What it is |
|---|---|
| `SLACK_BOT_TOKEN` | Slack bot OAuth token (`xoxb-…`). Bot must have scopes: `channels:history`, `channels:join`, `chat:write`, `reactions:write`. |
| `JIRA_CLOUD_KEY` | Atlassian API token (generate at https://id.atlassian.com/manage-api-tokens). Used with Basic auth as `email:token`. |

Verify both secrets are accessible before proceeding:

```bash
SESSION_KEY=$(cat ~/.openhands/agent-canvas/api-key.txt)
curl -s http://localhost:18000/api/settings/secrets/SLACK_BOT_TOKEN -H "X-Session-API-Key: $SESSION_KEY"
curl -s http://localhost:18000/api/settings/secrets/JIRA_CLOUD_KEY   -H "X-Session-API-Key: $SESSION_KEY"
```

---

## Information to Gather from the User

Before generating the automation, collect these five values:

| Parameter | Example | Notes |
|---|---|---|
| Slack channel name or ID | `#bugs` / `C0BFL769U6Q` | Name is resolved to ID automatically |
| Trigger phrase | `#bug` | Case-insensitive substring match |
| Jira site URL | `https://acme.atlassian.net` | No trailing slash |
| Jira account email | `alice@example.com` | Must match the API token owner |
| Jira project key | `KAN` | The short key shown in project settings |

The cron schedule defaults to `*/5 * * * *` (every 5 minutes). Ask the user if they want a different interval.

---

## Setup Workflow

### 1 — Resolve the Slack channel ID

If the user provides a channel name, convert it to an ID:

```bash
curl -s "https://slack.com/api/conversations.list?types=public_channel&limit=200" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  | python3 -c "
import json,sys
for c in json.load(sys.stdin).get('channels',[]):
    if c['name'] == 'bugs':          # replace with target channel name
        print(c['id'], c['name'])
"
```

### 2 — Discover valid Jira issue types

Not all projects have a "Bug" type. Fetch the list and choose the most appropriate:

```bash
AUTH=$(python3 -c "import base64; print('Basic '+base64.b64encode(b'EMAIL:TOKEN').decode())")
curl -s "https://SITE/rest/api/3/project/PROJECT_KEY" \
  -H "Authorization: $AUTH" -H "Accept: application/json" \
  | python3 -c "import json,sys; print([t['name'] for t in json.load(sys.stdin).get('issueTypes',[])])"
```

Use `"Bug"` if available; otherwise use `"Task"` or the closest available type.

### 3 — Customize and package `scripts/main.py`

Copy `scripts/main.py` and fill in the `── CONFIGURATION ──` block at the top:

```python
SLACK_CHANNEL_ID  = "C0BFL769U6Q"       # resolved in step 1
TRIGGER_PHRASE    = "#bug"
KV_KEY            = "slack_jira_monitor_bugs"   # unique key per channel
JIRA_BASE_URL     = "https://acme.atlassian.net"
JIRA_EMAIL        = "alice@example.com"
JIRA_PROJECT      = "KAN"
JIRA_ISSUE_TYPE   = "Task"               # from step 2
CRON_SCHEDULE     = "*/5 * * * *"
```

### 4 — Build and upload the tarball

```bash
mkdir -p /tmp/skill-deploy
cp scripts/main.py /tmp/skill-deploy/
cd /tmp && tar -czf automation.tar.gz -C skill-deploy main.py

UPLOAD=$(curl -s -X POST \
  "http://localhost:18001/api/automation/v1/uploads?name=slack-jira-monitor" \
  -H "Authorization: Bearer $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/gzip" \
  --data-binary @automation.tar.gz)

TARBALL_PATH=$(echo $UPLOAD | python3 -c "import json,sys; print(json.load(sys.stdin)['tarball_path'])")
echo "Uploaded: $TARBALL_PATH"
```

### 5 — Create the automation

```bash
curl -s -X POST "http://localhost:18001/api/automation/v1" \
  -H "Authorization: Bearer $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Slack → Jira: #bugs\",
    \"trigger\": {\"type\": \"cron\", \"schedule\": \"*/5 * * * *\", \"timezone\": \"UTC\"},
    \"tarball_path\": \"$TARBALL_PATH\",
    \"entrypoint\": \"python3 main.py\"
  }" | python3 -m json.tool
```

### 6 — Verify with a test dispatch

```bash
AUTOMATION_ID="<id from step 5 response>"

curl -s -X POST "http://localhost:18001/api/automation/v1/$AUTOMATION_ID/dispatch" \
  -H "Authorization: Bearer $OPENHANDS_AUTOMATION_API_KEY"

# Check result after ~15 seconds
sleep 15 && curl -s "http://localhost:18001/api/automation/v1/$AUTOMATION_ID/runs?limit=1" \
  -H "Authorization: Bearer $OPENHANDS_AUTOMATION_API_KEY" \
  | python3 -c "import json,sys; r=json.load(sys.stdin)['runs'][0]; print(r['status'], r.get('error_detail') or '')"
```

---

## How the Automation Works

- **Polling**: Fetches messages from the channel using `conversations.history` with `oldest=<last_ts>`. Only parent messages (not thread replies) that are not system events are considered.
- **State**: The high-water timestamp of the last processed message is stored in the KV store under `KV_KEY`. On the first run, it defaults to `time.time() - 300` (5 minutes ago).
- **Jira auth**: Basic authentication with `base64(email:api_token)` against the Jira REST API v3 endpoint.
- **Issue format**: Summary is extracted from the message (trigger phrase stripped, first sentence taken, max 120 chars). Description includes reporter user ID, date, and the full original message in ADF format.
- **Slack reply**: Posted as a threaded message with a clickable Jira link in Slack mrkdwn format: `*<URL|KEY>*`.
- **Reaction**: `white_check_mark` is added to the parent message. Duplicate reactions (`already_reacted`) are silently ignored.
- **Idempotency**: The `conversations.join` call runs on every execution so the bot self-heals if removed from the channel.

---

## Updating a Deployed Automation

To update the script after deployment:

```bash
# 1. Upload the new tarball (same as step 4)
NEW_TARBALL="oh-internal://uploads/<new-id>"

# 2. Patch the automation
curl -s -X PATCH "http://localhost:18001/api/automation/v1/$AUTOMATION_ID" \
  -H "Authorization: Bearer $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"tarball_path\": \"$NEW_TARBALL\"}"
```

---

## Additional Resources

- **`scripts/main.py`** — Fully parameterized automation script ready to customize and deploy
- **`references/setup-guide.md`** — Detailed reference: secret scopes, Jira token setup, KV store behavior, troubleshooting
