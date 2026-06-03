# State File Schema

The automation maintains a JSON state file that persists across polling runs.
This file is the source of truth for which conversations are active, which
comment IDs have already been processed, and the timestamp of the last poll.

---

## File Location

```
{WORKSPACE_BASE_ROOT}/automation-state/github_poller_{automation_id}.json
```

`WORKSPACE_BASE_ROOT` is derived by going two levels up from the `WORKSPACE_BASE`
environment variable (stripping `automation-runs/{run_id}`).

Example on a local install:

```
~/.openhands/workspaces/automation-state/github_poller_abc12345-….json
```

The `automation_id` is read from the `AUTOMATION_EVENT_PAYLOAD` environment
variable (field `automation_id`).

---

## Top-Level Schema

```jsonc
{
  "version": 1,                          // schema version (integer)
  "repo": "owner/repo",                  // the monitored repository
  "last_poll": "2024-06-01T12:00:00Z",   // ISO 8601 UTC — used as ?since= on the
                                         // next GitHub API call; advanced to the
                                         // START of each run before processing
  "conversations": { ... },              // see ConversationRecord below
  "processed_comment_ids": [             // rolling list (max 5000) of GitHub
    12345678,                            // comment IDs already handled; prevents
    98765432                             // duplicate processing if the run overlaps
  ]
}
```

---

## `conversations` Map

Key: `"{issue_number}"` (string) — uniquely identifies an issue or PR in the repo.

Value: **ConversationRecord**

```jsonc
{
  // Required fields
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                                        // OpenHands conversation UUID
  "issue_number": 42,                   // GitHub issue or PR number (integer)
  "issue_type":   "issue",              // "issue" | "pr"
  "html_url":     "https://github.com/owner/repo/issues/42",
                                        // direct link to the issue/PR
  "status":       "active",            // "active" | "closed" (see below)
  "last_activity": 1716576060.0        // float Unix timestamp — last time a message
                                        // was sent to or created for this conversation
}
```

### `status` Values

| Value | Meaning |
|-------|---------|
| `active` | Conversation is running or awaiting more input; new trigger comments on the same issue/PR will be forwarded |
| `closed` | Summary has been posted to GitHub; a new trigger comment will attempt to re-open this conversation (or create a fresh one if it is unreachable) |

---

## `processed_comment_ids` List

A rolling list (max `MAX_PROCESSED_IDS = 5000` entries) of integer GitHub
comment IDs that have already been processed. This prevents:

- Duplicate processing caused by cron boundary overlap (the `last_poll`
  timestamp is advanced to the start of the current run, so the next run
  re-scans a small window of time).
- Accidental re-triggers if the state file is partially reset.

IDs are stored as integers and kept sorted; the oldest entries are pruned
when the list exceeds the maximum.

---

## Conversation Lifecycle

```
[trigger phrase detected in a new comment]
        │
        ▼
  ┌──────────────────────────────────────────────────┐
  │  status = "active"                                │
  │  last_activity = now                              │
  │  POST GitHub comment: "🤖 OpenHands is on it!"   │
  └──────────────────────────────────────────────────┘
        │
  (subsequent runs)
        │
  ┌─────┴────────────────────────────────────────────┐
  │  New trigger on same issue/PR                     │
  │  → send_to_conversation()                         │
  │  → last_activity = now                            │
  └──────────────────────────────────────────────────┘
        │
  (when time.time() - last_activity > DONE_DEBOUNCE
   AND conversation_status ∈ {idle, finished, error, stuck})
        │
        ▼
  POST GitHub comment: summary or error message
  status = "closed"
        │
  (if a NEW trigger comment arrives later)
        │
        ▼
  Try send_to_conversation() on closed conv_id
  ├── succeeds → status = "active"  (re-opened)
  └── fails (conv deleted) → create_conversation() → status = "active"
```

---

## Example State File

```json
{
  "version": 1,
  "repo": "acme-corp/backend",
  "last_poll": "2024-06-01T12:05:00Z",
  "conversations": {
    "42": {
      "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
      "issue_number": 42,
      "issue_type": "issue",
      "html_url": "https://github.com/acme-corp/backend/issues/42",
      "status": "active",
      "last_activity": 1717243502.3
    },
    "15": {
      "conversation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "issue_number": 15,
      "issue_type": "pr",
      "html_url": "https://github.com/acme-corp/backend/pull/15",
      "status": "closed",
      "last_activity": 1717240800.0
    }
  },
  "processed_comment_ids": [
    1234567890,
    9876543210
  ]
}
```
