# Slack API Reference

Reference material for the `slack-channel-monitor` skill. Consult this file
when resolving token issues, diagnosing permission errors, or adjusting the
polling strategy.

---

## Token Types

| Type | Prefix | Typical source | Relevant scopes |
|------|--------|---------------|-----------------|
| **Bot token** | `xoxb-` | OAuth install / Slack App → Install App | `channels:history`, `channels:read`, `reactions:write`, `chat:write` |
| **User token** | `xoxp-` | OAuth flow on behalf of a workspace member | Same as bot + `search:read` for multi-channel search |

### Choosing a token

- **Prefer a bot token** for single-channel monitoring or when `search:read` is
  unavailable. One `conversations.history` call per channel per minute is fine
  for < 10 channels.
- **Use a user token** with `search:read` when monitoring multiple channels, to
  reduce API calls by querying all channels in a single `search.messages` request.

### Checking token type at runtime

The script detects token type by checking which secret name is set:

1. `SLACK_USER_TOKEN` (checked first  -  user token preferred for multi-channel)
2. `SLACK_BOT_TOKEN`

Set the appropriate secret in **OpenHands Settings → Secrets**.

---

## Required Scopes

### Bot token (`xoxb-`)

| Scope | Used for |
|-------|----------|
| `channels:history` | Read messages from public channels |
| `groups:history` | Read messages from private channels (if monitoring any) |
| `channels:read` | Resolve channel names → IDs |
| `reactions:write` | Add 👀 reaction to trigger messages |
| `chat:write` | Post conversation links and summaries back to Slack |

### User token (`xoxp-`)  -  additional scope

| Scope | Used for |
|-------|----------|
| `search:read` | `search.messages` across multiple channels in one request |

---

## Relevant API Endpoints

### `conversations.history`
Fetch messages from a single channel newer than a timestamp.

```
GET https://slack.com/api/conversations.history
  ?channel=CHANNEL_ID
  &oldest=UNIX_TIMESTAMP        (exclusive  -  messages strictly after this)
  &limit=100
  &inclusive=false
```

Returns a `messages` array. Each message has `ts`, `user`, `text`, `thread_ts`
(present if the message is in a thread or is a threaded reply).

**Bot must be invited to the channel** (or the token must have `channels:history`
for public channels without joining).

---

### `conversations.replies`
Fetch replies inside a specific thread newer than a timestamp.

```
GET https://slack.com/api/conversations.replies
  ?channel=CHANNEL_ID
  &ts=THREAD_ROOT_TS
  &oldest=UNIX_TIMESTAMP
  &limit=100
  &inclusive=false
```

The first item in `messages` is always the parent message  -  the script drops it
when comparing `ts == thread_root_ts`.

---

### `search.messages`
Search for messages matching a query across channels (user token only).

```
GET https://slack.com/api/search.messages
  ?query=QUERY_STRING
  &count=100
  &sort=timestamp
  &sort_dir=asc
```

**Query syntax used by this skill:**

```
"@openhands" in:<#C0123456> in:<#C9876543> after:2026-01-01
```

- `in:<#CHANNEL_ID>`  -  restrict to a channel (channel ID or name both work)
- `after:YYYY-MM-DD`  -  date-level precision only (the script post-filters by
  precise Unix timestamp)
- Phrase in quotes  -  exact match

**Limitations:**
- Date-only precision for `after:`  -  cannot filter to the minute
- Results sorted by relevance by default; use `sort=timestamp` to get chronological order
- `count` max is 100 per page (pagination supported via `page` parameter)
- Requires `search:read` scope  -  not available to bot tokens

---

### `reactions.add`
Add an emoji reaction to a message.

```
POST https://slack.com/api/reactions.add
{
  "channel": "CHANNEL_ID",
  "name":    "eyes",
  "timestamp": "MESSAGE_TS"
}
```

Error `already_reacted` is safe to ignore.

---

### `chat.postMessage`
Post a message to a channel, optionally within a thread.

```
POST https://slack.com/api/chat.postMessage
{
  "channel":   "CHANNEL_ID",
  "text":      "Message text",
  "thread_ts": "THREAD_ROOT_TS"   // omit for top-level messages
}
```

Returns `ts` of the posted message  -  **store this in `bot_message_ts`** in the
state file to prevent the bot from processing its own messages.

---

### `conversations.list`
List channels visible to the token (used to resolve names → IDs during setup).

```
GET https://slack.com/api/conversations.list
  ?types=public_channel,private_channel
  &limit=200
  &exclude_archived=true
```

Supports cursor-based pagination via the `response_metadata.next_cursor` field.

---

### `auth.test`
Verify a token and retrieve the associated user/bot ID.

```
GET https://slack.com/api/auth.test
```

Returns `user_id` (used by the script to detect and skip its own messages).

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `not_in_channel` | Bot hasn't been invited | `/invite @botname` in the channel |
| `missing_scope` | Token lacks a required scope | Re-install the Slack app with the correct scopes |
| `channel_not_found` | Channel ID is wrong | Use `conversations.list` to verify the ID |
| `ratelimited` | Too many API calls | Slack allows ~50 requests/min per token; < 10 channels is well within limits |
| `invalid_auth` | Token expired or revoked | Regenerate the token and update the secret |

---

## Rate Limits

Slack applies per-method rate limits (Tier 2 = ~20 req/min, Tier 3 = ~50 req/min).
With < 10 channels polled every minute:

| Method | Tier | Calls/min | Headroom |
|--------|------|-----------|---------|
| `conversations.history` | Tier 3 | ≤ 10 | Comfortable |
| `conversations.replies` | Tier 3 | ≤ 1 due tracked thread per iteration | Throttled with per-thread backoff |
| `search.messages` | Tier 2 | 1 | Fine |
| `reactions.add` | Tier 2 | ≤ triggers/min | Fine |
| `chat.postMessage` | Tier 3 | ≤ triggers + summaries | Fine |

The script surfaces Slack HTTP 429 responses with `Retry-After`. Thread reply
polling catches that signal, delays the affected thread, and increases its
per-thread backoff. Other Slack methods still fail fast so the next cron tick can
retry with the persisted state.
