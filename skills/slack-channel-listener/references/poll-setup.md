# Poll mode setup (cron + Slack Web API)

Use this path when the OpenHands automation backend is **not** reachable
from the public internet - laptops, hosts behind a corporate firewall, or
any deployment where you don't want to expose an inbound endpoint. The
automation runs on a schedule and polls Slack via outbound HTTPS.

## How it stays correct across runs

The script uses a **small SQLite database** as the source of truth for
"have I already processed this message?". For each matching message it
finds:

1. `state.claim(channel, ts)` does an `INSERT OR IGNORE` into
   `processed_messages`. If a row already exists, this call returns
   `False` and the message is skipped - either another concurrent runner
   has it in flight or a previous run completed it.
2. Run the agent.
3. On success, `state.mark_done(...)` updates the row's `status` to
   `done` and stamps `finished_at`. On exception,
   `state.mark_failed(channel, ts, error)` records the error.

The database lives at `$SLACK_STATE_DIR/slack-listener.sqlite3`
(default `$SLACK_STATE_DIR = /automation/storage/state`). This directory
must survive across automation runs - point it at whatever persistent
mount your runtime provides. If the path is missing or not writable the
script falls back to a tempdir and logs a warning; this is acceptable
for first-run dogfooding, but state will be lost between sandbox
restarts in that mode (the script will re-process recent messages and
double-reply).

Reactions are still available as **opt-in visual UX** via
`SLACK_REPLY_MODE=thread+reaction` - they leave a 👀 on start and a ✅
on success - but they no longer drive the control flow, so users
without `reactions:read` / `reactions:write` scopes can stick with
plain `thread` mode.

`SLACK_POLL_LOOKBACK_MINUTES` (default 15) bounds how far back the poller
looks; set it to comfortably exceed your cron interval so a delayed run
doesn't miss messages. Messages older than the lookback that have never
been seen will not be picked up unless you bump the lookback temporarily.

## Required scopes

| Scope | When you need it |
|---|---|
| `chat:write` | Always (post threaded replies). |
| `channels:history` | Scopes `single` / `list` / `all-public` for public channels. |
| `groups:history` | Private channels. |
| `reactions:write` | Only if `SLACK_REPLY_MODE=thread+reaction`. |
| `users:read` | If `SLACK_RESOLVE_USER_IDS=true` (default). |
| `search:read` | **Only** for scope `all-accessible`. Must be on a **user token** (`xoxp-...`), not a bot token. |

## Create the automation

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Slack poll listener (#${CHANNEL_NAME})\",
    \"trigger\": {
      \"type\": \"cron\",
      \"schedule\": \"* * * * *\",
      \"timezone\": \"UTC\"
    },
    \"tarball_path\": \"${TARBALL_PATH}\",
    \"entrypoint\": \"python agent_poll.py\",
    \"setup_script_path\": \"setup.sh\",
    \"timeout\": 600,
    \"env\": {
      \"SLACK_BOT_TOKEN\": \"xoxb-...\",
      \"SLACK_TRIGGER_PHRASES\": \"@thems-fightin-words\",
      \"SLACK_CHANNEL_SCOPE\": \"single\",
      \"SLACK_CHANNEL_ID\": \"${CHANNEL_ID}\",
      \"SLACK_REPLY_MODE\": \"thread\",
      \"SLACK_POLL_LOOKBACK_MINUTES\": \"15\",
      \"SLACK_STATE_DIR\": \"/automation/storage/state\"
    }
  }"
```

For `scope=all-accessible`, set `SLACK_BOT_TOKEN` to a user token (the
script uses `search.messages` which only works on user tokens) and ensure
`search:read` is granted.

## Cron cadence recommendations

| Trigger volume | Recommended cadence |
|---|---|
| Default (chat-like, sub-minute feel desired) | `* * * * *` |
| Rare (a few times per day, willing to wait) | `*/5 * * * *` or `*/15 * * * *` |
| Need sub-second latency | Use push mode instead - polling that fast burns sandbox time even when there's nothing to do. |

The script exits in well under a second when there are no matches, so a
busy cron schedule mostly just costs a few cron dispatches per day, not
LLM tokens. The LLM only runs when an actual match is processed, and the
SQLite store guarantees each message gets exactly one run regardless of
how often the cron fires.

## Catching up after downtime

If the automation was disabled or the host was offline for longer than
`SLACK_POLL_LOOKBACK_MINUTES`, messages from that gap will not be picked
up. To force a backfill, temporarily increase
`SLACK_POLL_LOOKBACK_MINUTES` (PATCH the automation), dispatch a manual
run, then revert.

## Inspecting the state database

The SQLite file is plain on disk; you can `sqlite3
$SLACK_STATE_DIR/slack-listener.sqlite3 'SELECT * FROM processed_messages
ORDER BY claimed_at DESC LIMIT 20'` to see recent processing history,
including any failures and their stored error messages.

## Disambiguating from push mode

If you have both push and poll automations on the same channel, you will
double-process messages. Pick one. The poll-mode reactions will not
prevent push-mode runs because push doesn't check reactions before
spinning up.
