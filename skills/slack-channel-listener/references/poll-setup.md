# Poll mode setup (cron + Slack Web API)

Use this path when the OpenHands automation backend is **not** reachable
from the public internet - laptops, hosts behind a corporate firewall, or
any deployment where you don't want to expose an inbound endpoint. The
automation runs on a schedule and polls Slack via outbound HTTPS.

## How it stays correct across runs

The script uses **message reactions as persistent state**. For each matching
message it finds:

1. Check whether the bot has already added the `ack_reaction` (default
   `eyes` 👀). If yes → skip; another run has claimed (or completed) it.
2. Add `ack_reaction` to claim the message.
3. Run the agent. On success → add `done_reaction` (default `white_check_mark`
   ✅). On failure → add `fail_reaction` (default `warning` ⚠️) and post a
   short error reply to the thread.

This makes the poller idempotent and concurrent-safe: re-running the cron
job at any frequency cannot double-process a message, and the state is
visible to humans in Slack itself - no external store needed.

`SLACK_POLL_LOOKBACK_MINUTES` (default 15) bounds how far back the poller
looks; set it to comfortably exceed your cron interval so a delayed run
doesn't miss messages.

## Required scopes

| Scope | When you need it |
|---|---|
| `chat:write` | Always (post threaded replies). |
| `reactions:read`, `reactions:write` | Always (state machine). |
| `channels:history` | Scopes `single` / `list` / `all-public` for public channels. |
| `groups:history` | Private channels. |
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
      \"schedule\": \"*/2 * * * *\",
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
      \"SLACK_REPLY_MODE\": \"thread+reaction\",
      \"SLACK_POLL_LOOKBACK_MINUTES\": \"15\"
    }
  }"
```

For `scope=all-accessible`, set `SLACK_BOT_TOKEN` to a user token (the
script uses `search.messages` which only works on user tokens) and ensure
`search:read` is granted.

## Cron cadence recommendations

| Trigger volume | Recommended cadence |
|---|---|
| Rare (a few times per day) | `*/15 * * * *` |
| Active channel (chat-bot-like) | `*/2 * * * *` |
| Need < 1 min latency | Use push mode instead - polling that fast burns sandbox time even when there's nothing to do. |

The script exits in well under a second if there are no matches, so a
busy cron schedule mostly just costs a few cron dispatches per day, not
LLM tokens. The LLM runs only when an actual match is processed.

## Catching up after downtime

If the automation was disabled or the host was offline for longer than
`SLACK_POLL_LOOKBACK_MINUTES`, messages from that gap will not be picked
up. To force a backfill, temporarily increase
`SLACK_POLL_LOOKBACK_MINUTES` (PATCH the automation), dispatch a manual
run, then revert.

## Disambiguating from push mode

If you have both push and poll automations on the same channel, you will
double-process messages. Pick one. The poll-mode reactions will not
prevent push-mode runs because push doesn't check reactions before
spinning up.
