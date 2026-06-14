# State File Schema

The automation maintains a JSON state file that persists across polling runs.
This file is the source of truth for which conversations are active, which
timestamps have been processed, and which messages were posted by the bot.

---

## File Location

```
{WORKSPACE_BASE_ROOT}/automation-state/slack_poller_{automation_id}.json
```

Where `WORKSPACE_BASE_ROOT` is derived by going two levels up from the
`WORKSPACE_BASE` environment variable (stripping `automation-runs/{run_id}`).

Example on a local install:

```
~/.openhands/workspaces/automation-state/slack_poller_abc12345-….json
```

The `automation_id` is read from the `AUTOMATION_EVENT_PAYLOAD` environment
variable (field `automation_id`).

---

## Top-Level Schema

```jsonc
{
  "version": 1,                        // schema version (integer)
  "bot_user_id": "UBOTID123",          // Slack user_id of the bot/token owner
                                       // cached from auth.test; null until first run
  "last_poll": {
    "C0123456789": "1716576000.123456" // channel_id → float Unix timestamp (string)
                                       // set to (now - POLL_OVERLAP_SECONDS) at the
                                       // END of each run; pinned back if triggers fail
  },
  "conversations": { ... },            // see ConversationRecord below
  "bot_message_ts": [                  // rolling list of Slack 'ts' values for
    "1716576100.000200"                // messages THIS bot posted; used to skip
  ],                                   // self-messages during processing
  "processed_ts": [                    // rolling list of message ts values that have
    "1716576050.000100"                // already been fully handled (dedup across the
  ]                                    // overlap window between iterations)
}
```

---

## `conversations` Map

Key: `"{channel_id}:{thread_root_ts}"` - uniquely identifies a Slack thread.

Value: **ConversationRecord**

```jsonc
{
  // Required fields
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                                      // OpenHands conversation UUID
  "channel_id":      "C0123456789", // Slack channel ID
  "thread_ts":       "1716576000.000100",
                                      // Slack thread root timestamp
                                      // (= msg_ts for top-level trigger messages)
  "status":          "active",      // "active" | "watching" | "closed"
  "last_activity":   1716576060.0,   // float Unix timestamp of the last time the
                                      // script created, resumed, or summarized the
                                      // OpenHands conversation

  // Follow-up polling fields
  "last_seen_reply_ts": "1716576000.000100",
                                      // newest Slack reply ts observed for this thread
  "reply_poll_backoff_seconds": 5,   // current per-thread conversations.replies backoff
  "next_reply_poll_at": 1716576065.0,// next Unix timestamp when replies may be polled
  "watch_until": 1716576360.0,       // follow-up watch expiry for completed conversations

  // Present after expiry
  "closed_reason": "followup_watch_expired",
  "closed_at": 1716576360.0
}
```

### `status` values

| Value | Meaning |
|-------|---------|
| `active` | Conversation is running or awaiting completion; triggered replies are forwarded to it |
| `watching` | A summary has been posted and the thread remains open briefly for triggered follow-ups |
| `closed` | The follow-up watch expired; future triggered replies create a new conversation |

`watching` records use `watch_until` to avoid keeping every completed thread hot
forever. Quiet watched threads use exponential backoff for `conversations.replies`
polling, and each automation iteration polls at most one due thread.

---

## `bot_message_ts` List

A rolling list (max `MAX_BOT_TS = 2000` entries) of Slack `ts` values for
messages posted BY the bot. This prevents the script from treating its own
replies as user messages.

Entries are added when:
- The bot posts a conversation link (on trigger detection)
- The bot posts a summary (on conversation completion)

---

## `processed_ts` List

A rolling list (max `MAX_PROCESSED_TS = 2000` entries) of Slack `ts` values
for messages that have already been fully handled by this script.

Because `last_poll` is set to `(now - POLL_OVERLAP_SECONDS)` rather than
exactly `now`, messages near the boundary are re-fetched on the next iteration.
`processed_ts` provides a second deduplication layer that prevents these
re-fetched messages from being processed twice (e.g., triggering a duplicate
conversation or forwarding the same reply multiple times).

Entries are added when a message is either skipped (not human, already handled,
or an untriggered reply in a watched thread) or successfully processed (trigger
detected and conversation created, or triggered reply forwarded).

---

## Transition Diagram

```
[trigger detected]
        |
        v
  status = "active"
  last_activity = now
  follow-up poll fields initialized
        |
        | triggered Slack reply while active
        | -> send_to_conversation()
        | -> last_activity = now
        | -> watch window/backoff reset
        |
  (when time.time() - last_activity > DONE_DEBOUNCE
   AND conversation_status in {idle, finished, error, stuck})
        |
        v
  Post summary to Slack thread
  status = "watching"
  watch_until = now + THREAD_FOLLOWUP_WATCH_SECONDS
        |
        | triggered Slack reply before watch_until
        | -> send_to_conversation()
        | -> status = "active"
        |
        | no triggered reply before watch_until
        v
  status = "closed"
  closed_reason = "followup_watch_expired"
```

---

## Example State File

```json
{
  "version": 1,
  "bot_user_id": "U04AB1CDEF",
  "last_poll": {
    "C0123456789": "1716576060.000000",
    "C9876543210": "1716576060.000000"
  },
  "conversations": {
    "C0123456789:1716575900.000100": {
      "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
      "channel_id": "C0123456789",
      "thread_ts": "1716575900.000100",
      "status": "active",
      "last_activity": 1716575902.3,
      "last_seen_reply_ts": "1716575900.000100",
      "reply_poll_backoff_seconds": 5,
      "next_reply_poll_at": 1716575907.3,
      "watch_until": 1716576202.3
    },
    "C9876543210:1716570000.000500": {
      "conversation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "channel_id": "C9876543210",
      "thread_ts": "1716570000.000500",
      "status": "watching",
      "last_activity": 1716572100.0,
      "last_seen_reply_ts": "1716572050.000100",
      "reply_poll_backoff_seconds": 20,
      "next_reply_poll_at": 1716572120.0,
      "watch_until": 1716572400.0
    }
  },
  "bot_message_ts": [
    "1716575903.000200",
    "1716572105.000100"
  ],
  "processed_ts": [
    "1716575900.000100",
    "1716572000.000500"
  ]
}
```
