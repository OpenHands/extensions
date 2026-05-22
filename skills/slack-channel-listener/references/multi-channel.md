# Multi-channel scope

The skill supports four scope modes via `SLACK_CHANNEL_SCOPE`:

| Scope | Means | Push viable? | Poll viable? |
|---|---|---|---|
| `single` | Exactly one channel. `SLACK_CHANNEL_ID` is the channel ID. | Yes - filter on `event.channel == 'C...'`. | Yes. |
| `list` | A specific set of channels. `SLACK_CHANNEL_IDS` is comma-separated. | Yes - filter on `contains(['C1','C2'], event.channel)`. | Yes. |
| `all-public` | Every public channel the **bot** is a member of. | Yes (bot must be invited to each channel for `message.channels` to fire there). | Yes (lists channels with `conversations.list` + `is_member`). |
| `all-accessible` | Every channel the **user token** can see (DMs included). | Not really - apps cannot self-join channels en masse; use poll. | Yes - uses `search.messages`. |

## How to grow the scope safely

- Start with `single` for the first dogfooding pass. The blast radius is
  contained and you'll catch surprises (deleted messages, edits,
  re-deliveries) on one channel before fanning out.
- Move to `list` once you know exactly which channels you want.
- `all-public` only makes sense for a workspace-wide assistant. Be aware
  the bot will only fire in channels it's been invited to; add a small
  helper to `conversations.join` every public channel if you want it
  everywhere, or rely on humans inviting it as needed.
- `all-accessible` is the right choice for a "personal assistant" pattern
  - "anything I can see, the agent can react to" - but it requires a user
  token, which is more sensitive than a bot token. Treat it accordingly.

## Push: inviting the bot in bulk

For `all-public` push, you can script the invites:

```bash
# Requires the bot token to have `channels:join` scope.
slack_token="$SLACK_BOT_TOKEN"
cursor=""
while :; do
  resp=$(curl -s -H "Authorization: Bearer $slack_token" \
    "https://slack.com/api/conversations.list?types=public_channel&limit=200&cursor=$cursor")
  echo "$resp" | jq -r '.channels[] | select(.is_member==false) | .id' | \
    while read -r ch; do
      curl -s -X POST -H "Authorization: Bearer $slack_token" \
        -d "channel=$ch" https://slack.com/api/conversations.join >/dev/null
    done
  cursor=$(echo "$resp" | jq -r '.response_metadata.next_cursor // ""')
  [ -z "$cursor" ] && break
done
```

New channels created after this runs won't auto-join. Subscribe to the
`channel_created` event in the Slack app and add a tiny automation that
calls `conversations.join` on each one if you need that.

## Poll: paging through results

- `conversations.history` pages per channel - the script keeps `limit=50`
  per channel per cron tick, which is plenty unless your channel volume
  exceeds 50 matches in `SLACK_POLL_LOOKBACK_MINUTES` (in which case you
  have bigger problems).
- `search.messages` is paginated; the script asks for `count=50` per
  trigger phrase per cron tick. Same logic.

## Cross-cutting: rate limits

The Slack Web API enforces per-method tiers. Most read methods are Tier 3
(~50 req/min). The poll script does roughly one `conversations.history`
per channel per cron tick and one `users.info` per unique mentioned user
(cached for the run). For typical scopes the load is negligible; for
hundreds of channels in `all-public`, consider a longer cron interval or
move to push.
