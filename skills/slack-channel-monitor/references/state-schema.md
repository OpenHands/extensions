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
                                       // updated at the START of each run so that
                                       // the NEXT run fetches everything after it
  },
  "conversations": { ... },            // see ConversationRecord below
  "bot_message_ts": [                  // rolling list of Slack 'ts' values for
    "1716576100.000200"                // messages THIS bot posted; used to skip
  ],                                   // self-messages during processing
  "known_threads": {                   // channel_id → {thread_ts → latest_reply_ts}
    "C0123456789": {                   // persisted thread parents so their
      "1716575900.000100": "1716576000.000300"  // replies remain pollable
    }                                  // even after the parent ages out of
  }                                    // the channel history window
}
```

---

## `conversations` Map

Key: `"{channel_id}:{thread_root_ts}"`  -  uniquely identifies a Slack thread.

Value: **ConversationRecord**

```jsonc
{
  // Required fields
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                                      // OpenHands conversation UUID
  "channel_id":      "C0123456789",  // Slack channel ID
  "thread_ts":       "1716576000.000100",
                                      // Slack thread root timestamp
                                      // (= msg_ts for top-level trigger messages)
  "status":          "active",        // "active" | "closed"
  "last_activity":   1716576060.0,    // float Unix timestamp of the last time the
                                      // script sent a message to this conversation
                                      // (creation time, or time a reply was forwarded)
}
```

### `status` values

| Value | Meaning |
|-------|---------|
| `active` | Conversation is running or awaiting more input; replies will be forwarded |
| `closed` | Summary has been posted to Slack; no further processing |

Closed conversations are retained in the map indefinitely (the map stays small
since there are < 10 channels and the trigger rate is typically low). If the
map grows unexpectedly, closed entries older than a configurable TTL can be
pruned.

---

## `bot_message_ts` List

A rolling list (max `MAX_BOT_TS = 2000` entries) of Slack `ts` values for
messages posted BY the bot. This prevents the script from treating its own
replies as user messages.

Entries are added when:
- The bot posts a conversation link (on trigger detection)
- The bot posts a summary (on conversation completion)

---

## `known_threads` Map

Tracks thread parents the poller has previously seen so their replies can be
polled on every run, even after the parent message ages out of the channel
history window.

- **Outer key**: channel_id.
- **Inner key**: thread root `ts` (the parent message's timestamp).
- **Value**: the most recent reply `ts` observed in that thread (used for
  recency-based pruning).

A thread is added when:
- A top-level message returned by `conversations.history` has `reply_count > 0`.
- A thread is being polled because it backs an active conversation (so it
  remains in the map after the conversation closes).

Each channel keeps at most `MAX_KNOWN_THREADS_PER_CHANNEL = 50` entries; the
oldest threads (lowest latest-reply timestamp) are dropped first. Entries for
channels no longer monitored are removed entirely. The cap doubles as a guard
against rate-limit pressure on `conversations.replies` (Slack Tier 3).

---

## Transition Diagram

```
[trigger detected]
        │
        ▼
  status = "active"
  last_activity = now
        │
  (next run or later runs)
        │
  ┌─────┴──────────────────────────────────────────┐
  │  User sends a reply in the thread               │
  │  → send_to_conversation() called               │
  │  → last_activity = now                         │
  └─────────────────────────────────────────────────┘
        │
  (when time.time() - last_activity > DONE_DEBOUNCE
   AND conversation_status ∈ {idle, finished, error, stuck})
        │
        ▼
  Post summary to Slack thread
  status = "closed"
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
      "last_activity": 1716575902.3
    },
    "C9876543210:1716570000.000500": {
      "conversation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "channel_id": "C9876543210",
      "thread_ts": "1716570000.000500",
      "status": "closed",
      "last_activity": 1716572100.0
    }
  },
  "bot_message_ts": [
    "1716575903.000200",
    "1716572105.000100"
  ],
  "known_threads": {
    "C0123456789": {
      "1716575900.000100": "1716576040.000400",
      "1716574500.000700": "1716574700.000800"
    },
    "C9876543210": {
      "1716570000.000500": "1716572050.000900"
    }
  }
}
```
