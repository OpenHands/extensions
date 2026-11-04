# State Schema

The automation maintains a single JSON state document, persisted across runs.
It is the source of truth for which days have been handled, which conversation
is still active, and which working directory is still on disk.

---

## Storage

**Primary (cloud):** the automation service's KV store, key `state`, available
when `AUTOMATION_KV_TOKEN` is injected.

**Fallback (local/dev):**

```
{WORKSPACE_BASE_ROOT}/automation-state/dad_joke_{automation_id}.json
```

`WORKSPACE_BASE_ROOT` is two levels up from `WORKSPACE_BASE`, stripping
`automation-runs/{run_id}`; `automation_id` comes from `AUTOMATION_EVENT_PAYLOAD`.

The KV store caps a value at 64 KB. Everything below is bounded so the document
stays comfortably inside it however long the automation runs - which matters
here more than for a weekly automation, because a daily key writes a record a
day forever.

---

## Top-Level Schema

```jsonc
{
  "version": 1,
  "updated_at": 1717200000.0,

  // The most recent joke set, in one slot rather than one per day. Keeping
  // every joke set here would overrun the value limit inside a fortnight.
  "last_jokes": {
    "period": "2026-08-20",
    "conversation_url": "https://app.all-hands.dev/conversations/…",
    "written_at": 1717200000.0,
    "text": "…first 4000 characters…"
  },

  // One record per day, keyed `jokes:{YYYY-MM-DD}`, pruned to the last 14.
  "tasks": {}
}
```

---

## Task Record

```jsonc
"jokes:2026-08-20": {
  "period": "2026-08-20",
  "status": "active",
  "conversation_id": "6ceaa97a-…",
  "conversation_url": "https://…/conversations/6ceaa97a-…",  // set at finalize
  "workspace_dir": "/workspace/dad-joke/2026-08-20",          // removed with the directory
  "suggestion_count": 3,
  "last_activity": 1717200000.0,
  "completed_at": 1717200300.0,   // set once the conversation stopped
  "expired_after": 3614.4         // only on `expired`
}
```

### Statuses

| Status | Meaning |
|---|---|
| `starting` | The day is claimed; the conversation does not exist yet |
| `active` | The conversation is running |
| `completed` | A joke set was produced and printed |
| `empty` | The conversation stopped without writing anything |
| `failed` | The conversation ended `error` or `stuck` |
| `expired` | Never reached a terminal status within `MAX_ACTIVE_AGE` (1h) |

---

## Lifecycle

```
                 today already in tasks ──> stop (no conversation started)
                             │
   run starts ──> write `starting` and PERSIST
                             │
                       create workspace + conversation
                             │
                 success ──> `active`      failure ──> drop the claim,
                             │                          remove the workspace
               (a later run polls) │
                                     ▼
                       terminal ──> read jokes.md, else the final message
                             │
                     jokes ──────────┴──> `completed`, keep their opening,
                                          print them, remove the workspace
                     no jokes ───────────> `empty`
                     error/stuck ────────> `failed`
                     never terminal ─────> `expired` after 1h
```

### Why the day is claimed before the slow work

State is otherwise written only at the end of a run. An overlapping run - a
retry, a manual dispatch landing on a cron tick - would read no record for today
and start a second conversation over the same suggestions. Writing `starting`
first closes that window. A claim left behind by a run that died before creating
its conversation is released after `STALLED_CLAIM_SECONDS` (15 minutes), which
is far longer than starting a conversation.

---

## Pruning

| Field | Cap | Rule |
|---|---|---|
| `tasks` | 14 records | Oldest evicted first, but never one that is `starting`/`active` or still holds a `workspace_dir` |
| `last_jokes.text` | 4000 characters | Truncated |

A task still holding a `workspace_dir` is never pruned, because that record is
the only thing that knows a directory is waiting to be removed.
