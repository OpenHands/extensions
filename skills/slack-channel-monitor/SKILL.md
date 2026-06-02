---
name: slack-channel-monitor
description: >
  This skill should be used when the user asks to "monitor a Slack channel",
  "watch Slack for messages", "create a Slack bot that responds to mentions",
  "set up an OpenHands Slack integration", "trigger OpenHands from Slack",
  "respond to @openhands in Slack", or "poll Slack channels for a trigger
  phrase". Guides the user through creating a cron automation that watches up
  to 10 Slack channels and starts an OpenHands conversation whenever a
  configurable trigger phrase is detected.
---

# Slack Channel Monitor

Create a custom-script cron automation that polls up to 10 Slack channels
every minute. The polling script checks Slack and persisted state first, then
only creates or resumes an OpenHands conversation when there is an actionable
trigger message or an update to an active tracked thread. When a message
containing the **trigger phrase** (default: `@openhands`) is detected it:

1. Adds a 👀 reaction to the triggering message.
2. Opens an OpenHands conversation with the message and recent channel context.
3. Posts a reply in the Slack thread with a link to the conversation.

On every subsequent run:
- If there are no matching messages, no replies for active tracked threads,
  and no active conversations to check, the script saves state, fires the
  completion callback, and exits without starting any OpenHands conversation
  or LLM-backed agent work.
- Replies in the thread are forwarded to the running conversation.
- When the conversation finishes (or errors), the agent's final response is
  posted back to the Slack thread.

> **Local mode only.** This automation targets the local OpenHands setup
> (`dev:automation` stack). A cloud/webhook-based variant is out of scope here.

---

## Prerequisites

### Required secrets

Verify that at least one of the following secrets is set in
**OpenHands Settings → Secrets** before proceeding:

| Secret name | Token type | Minimum scopes |
|---|---|---|
| `SLACK_BOT_TOKEN` | Bot (`xoxb-…`) | `channels:history`, `channels:read`, `reactions:write`, `chat:write` |
| `SLACK_USER_TOKEN` | User (`xoxp-…`) | Same as bot, plus `search:read` for multi-channel efficiency |

Check with:
```bash
# For bot token:
curl -s https://slack.com/api/auth.test -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('ok' if d.get('ok') else d.get('error'))"

# For user token:
curl -s https://slack.com/api/auth.test -H "Authorization: Bearer $SLACK_USER_TOKEN" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('ok' if d.get('ok') else d.get('error'))"
```

If neither token is present, inform the user and stop  -  the automation cannot
function without Slack credentials.

### Optional secret

| Secret name | Default | Purpose |
|---|---|---|
| `OPENHANDS_URL` | `http://localhost:8000` | Base URL used to build conversation links posted in Slack |

---

## Setup Workflow

Follow these steps in order.

### Step 1  -  Collect channels

Ask the user: *"Which Slack channels should be monitored? You can provide
channel names (e.g. `#general`) or IDs (e.g. `C0123456789`)."*

**If the user provides channel names**, resolve them to IDs:

```bash
SLACK_TOKEN="${SLACK_BOT_TOKEN:-$SLACK_USER_TOKEN}"
curl -s "https://slack.com/api/conversations.list?types=public_channel,private_channel&limit=200&exclude_archived=true" \
  -H "Authorization: Bearer $SLACK_TOKEN" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
if not data.get('ok'):
    print('ERROR:', data.get('error'))
    exit(1)
names = set(n.lstrip('#') for n in ['CHANNEL_NAMES_HERE'.split(',')])
for ch in data.get('channels', []):
    if ch['name'] in names:
        print(f\"{ch['name']} → {ch['id']}\")
"
```

Replace `CHANNEL_NAMES_HERE` with the comma-separated names the user provided.

**If `conversations.list` returns `missing_scope` or `not_authed`:**
Inform the user: *"The token doesn't have permission to list channels. Please
provide the channel IDs directly (right-click a channel in Slack → Copy link  - 
the last path segment starting with `C` is the ID)."*

**If the bot token lacks `channels:read`** for private channels, the user can
either invite the bot first (`/invite @botname`) or switch to a user token.

Collect up to 10 channel IDs. Record them as a Python list literal, e.g.:
```python
["C0123456789", "C9876543210"]
```

### Step 2  -  Collect trigger phrase

Ask the user: *"What trigger phrase should OpenHands respond to?
(Press Enter to use the default: `@openhands`)"*

Accepted values: any non-empty string unlikely to appear accidentally, e.g.
`@openhands`, `jazz hands`, `take-me-to-funky-town`.

### Step 3  -  Generate the automation script

Use the custom script path. Do **not** create this monitor through the prompt
preset: a prompt preset starts an agent conversation on every cron tick. This
script polls Slack first and starts a conversation only after a message or
tracked thread reply passes the actionability gates.

Read `scripts/main.py` from this skill's directory. Apply exactly three
constant substitutions near the top of the file:

| Placeholder | Replace with |
|---|---|
| `TRIGGER_PHRASE = "@openhands"` | `TRIGGER_PHRASE = "{user_phrase}"` |
| `CHANNEL_IDS: list[str] = []` | `CHANNEL_IDS: list[str] = {channel_id_list}` |
| `DEFAULT_OPENHANDS_URL = "http://localhost:8000"` | `DEFAULT_OPENHANDS_URL = "{url}"` (keep default if user has no preference) |

Write the customised script to a temporary directory:
```bash
mkdir -p /tmp/slack-monitor-build
# (write the customised main.py to /tmp/slack-monitor-build/main.py)
```

Validate syntax before packaging:
```bash
python3 -m py_compile /tmp/slack-monitor-build/main.py && echo "Syntax OK"
```

Fix any syntax errors before proceeding.

### Step 4  -  Package and upload

```bash
tar -czf /tmp/slack-monitor.tar.gz -C /tmp/slack-monitor-build .

# Determine the API host (use <HOST> from the system prompt, else localhost:8000)
OPENHANDS_HOST="http://localhost:8000"

TARBALL_PATH=$(curl -s -X POST \
  "${OPENHANDS_HOST}/api/automation/v1/uploads?name=slack-channel-monitor" \
  -H "Authorization: Bearer $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/gzip" \
  --data-binary @/tmp/slack-monitor.tar.gz \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['tarball_path'])")

echo "Uploaded: $TARBALL_PATH"
```

If the upload fails with a size error, the tarball must be under 1 MB.
`main.py` is under 15 KB so this should never trigger.

### Step 5  -  Create the automation

```bash
curl -s -X POST "${OPENHANDS_HOST}/api/automation/v1" \
  -H "Authorization: Bearer $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Slack Channel Monitor\",
    \"trigger\": {\"type\": \"cron\", \"schedule\": \"* * * * *\"},
    \"tarball_path\": \"$TARBALL_PATH\",
    \"entrypoint\": \"python3 main.py\",
    \"timeout\": 55
  }" | python3 -m json.tool
```

A 55-second timeout keeps runs well within the 60-second cron window.

Record the returned `id`  -  share it with the user as confirmation.

### Step 6  -  Confirm

Tell the user:

> ✅ **Slack Channel Monitor** is running!
>
> - Automation ID: `{id}`
> - Channels: `{channel list}`
> - Trigger phrase: `{phrase}`
> - Polling every minute via cron `* * * * *`
> - State file: `~/.openhands/workspaces/automation-state/slack_poller_{id}.json`
>
> Send a message containing `{phrase}` in any monitored channel to test it.
> The bot will react with 👀 and reply with a link to the new conversation.

---

## Runtime Behaviour (per poll)

Each cron run executes `main.py`, which:

1. **Loads state** from the JSON file (see `references/state-schema.md`).
2. **Resolves the Slack token**  -  checks `SLACK_USER_TOKEN` then `SLACK_BOT_TOKEN`.
3. **Fetches new messages before any conversation is started:**
   - User token + `search:read` + > 1 channel → single `search.messages` call
     (searches for the trigger phrase across all channels).
   - Otherwise → one `conversations.history` call per channel.
4. **Fetches thread replies**  -  one `conversations.replies` call per active thread.
5. **Processes messages** in chronological order:
   - Skips bot messages and any `ts` in `bot_message_ts`.
   - Reply in a tracked thread → forwards to the existing conversation.
   - Contains trigger phrase → 👀 reaction, create conversation, post link.
6. **If there are no trigger messages, tracked replies, or active conversations**, saves state, fires the completion callback, and exits without creating a conversation.
7. **Checks conversation statuses**  -  for each active conversation where
   `time.time() - last_activity > 15 s`:
   - If status is `idle`, `finished`, `error`, or `stuck` → fetch the agent's
     final response via `/api/conversations/{id}/agent_final_response` and post
     it to the Slack thread. Mark conversation `closed`.
8. **Saves state** and fires the completion callback.

---

## Additional Resources

### Reference Files

- **`references/slack-api.md`**  -  Slack token types, required scopes, API
  endpoint reference, rate limits, and common error codes.
- **`references/state-schema.md`**  -  State JSON schema, field definitions,
  example file, and conversation lifecycle diagram.

### Script Template

- **`scripts/main.py`**  -  The complete automation script. Customise the three
  constants at the top (`TRIGGER_PHRASE`, `CHANNEL_IDS`, `DEFAULT_OPENHANDS_URL`)
  before packaging.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Bot doesn't react to messages | Token missing or bot not in channel | Verify token with `auth.test`; `/invite @botname` |
| `not_in_channel` error in run logs | Bot token used but bot not a member | Invite bot or switch to user token |
| `missing_scope` error | Token lacks required scopes | Re-install Slack app with correct scopes (see `references/slack-api.md`) |
| No messages detected | `last_poll` timestamp is in the future | Delete the state file to reset; it will be recreated on next run |
| Conversation link 404 | `OPENHANDS_URL` points to wrong host | Set the `OPENHANDS_URL` secret to the correct base URL |
| Summary never posted | Conversation stuck in `running` state | Check conversation in the OpenHands UI; the agent may need intervention |
