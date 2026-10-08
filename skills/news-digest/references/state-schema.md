# State Schema

The automation maintains a single JSON state document, persisted across runs.
It is the source of truth for which days have been handled, which stories have
already been reported, which conversation is still active, and which working
directory is still on disk.

---

## Storage

**Primary (cloud):** the automation service's KV store, key `state`, available
when `AUTOMATION_KV_TOKEN` is injected.

**Fallback (local/dev):**

```
{WORKSPACE_BASE_ROOT}/automation-state/news_digest_{automation_id}.json
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

  // Set on every run that actually read the feeds. A run that stopped at the
  // "today is done" check does not touch it.
  "last_checked": 1717200000.0,

  // What each selection stage left, from the same run. A digest that came out
  // empty is explained by whichever of these is zero.
  "last_funnel": { "fetched": 60, "unseen": 12, "fresh": 9 },

  // Up to ten feed failures from the last run that read them, each truncated
  // to 200 characters. Diagnostic only; nothing branches on it.
  "last_feed_errors": ["https://example.test/feed: HTTP Error 500: Internal Server Error"],

  // Story fingerprints already reported, oldest first, capped at 1000 - about
  // two per story, so roughly five hundred stories. See "Fingerprints" below.
  "seen": ["3f2a9c1b7d4e8a05", "…"],

  // The most recent digest, in one slot rather than one per day. Keeping every
  // digest here would overrun the value limit inside a fortnight.
  "last_digest": {
    "period": "2026-08-20",
    "conversation_url": "https://app.all-hands.dev/conversations/…",
    "written_at": 1717200000.0,
    "text": "…first 4000 characters…"
  },

  // One record per day, keyed `news:{YYYY-MM-DD}`, pruned to the last 14.
  "tasks": {}
}
```

---

## Task Record

```jsonc
"news:2026-08-20": {
  "period": "2026-08-20",
  "status": "active",
  "conversation_id": "6ceaa97a-…",
  "conversation_url": "https://…/conversations/6ceaa97a-…",  // set at finalize
  "workspace_dir": "/workspace/news-digest/2026-08-20",       // removed with the directory
  "item_keys": ["3f2a9c1b7d4e8a05", "…"],                     // dropped at finalize
  "item_count": 12,
  "last_activity": 1717200000.0,
  "completed_at": 1717203600.0,   // set once the conversation stopped
  "expired_after": 7213.4         // only on `expired`
}
```

### Statuses

| Status | Meaning | Stories remembered? |
|---|---|---|
| `starting` | The day is claimed; the conversation does not exist yet | no |
| `active` | The conversation is running | no |
| `completed` | A digest was produced and printed | **yes** |
| `empty` | The conversation stopped without writing anything | no |
| `failed` | The conversation ended `error` or `stuck` | no |
| `expired` | Never reached a terminal status within `MAX_ACTIVE_AGE` (2h) | no |

Only `completed` widens `seen`. That is the whole recovery story: because the
lookback window (48h) is wider than the schedule, every other outcome leaves its
stories to be picked up by the next run rather than losing them.

---

## Lifecycle

```
                 today already in tasks ──> stop (no feeds fetched)
                             │
   run starts ──> fetch feeds ──> select stories
                             │
              nothing new ───┴──> record last_checked, leave the day UNCLAIMED
                             │
              stories ───────┴──> write `starting` and PERSIST
                                        │
                                  create workspace + conversation
                                        │
                          success ──> `active`      failure ──> drop the claim,
                                        │                       remove the workspace
                    (a later run polls) │
                                        ▼
                          terminal ──> read digest.md, else the final message
                                        │
                        digest ─────────┴──> `completed`, widen `seen`,
                                             print it, remove the workspace
                        no digest ──────────> `empty`
                        error/stuck ────────> `failed`
                        never terminal ─────> `expired` after 2h
```

### Why the day is claimed before the slow work

State is otherwise written only at the end of a run. An overlapping run - a
retry, a manual dispatch landing on a cron tick - would read no record for today
and start a second conversation over the same stories. Writing `starting`
first closes that window. A claim left behind by a run that died before creating
its conversation is released after `STALLED_CLAIM_SECONDS` (15 minutes), which
is far longer than fetching a feed list.

### Why "nothing new" does not claim the day

A feed that has not published yet looks exactly like a feed with nothing to
say. Claiming the day on an empty result would mean the first run of the morning
silently cancels the rest of the day. Instead the day stays open: later runs
re-check, at the cost of one HTTP request per feed and no tokens at all.

---

## Fingerprints

Each story contributes up to two 16-character SHA-256 prefixes to `seen`:

1. the feed's own identifier (`guid` in RSS, `id` in Atom), and
2. its link, with the scheme and host lowercased, the fragment and any trailing
   slash removed, and `utm_*` parameters stripped.

A story is treated as already covered if **either** matches. Both are needed:
a feed whose links carry a per-fetch campaign tag is only recognisable by its
identifier, and two publishers syndicating the same article agree on nothing
*but* the link.

Hashes rather than the values themselves, because identifiers range from a short
guid to a long URL and the document has a size ceiling. They are one-way, so
`seen` cannot be read back to reconstruct what was covered - `last_digest` and
the conversations are where that is kept.

---

## Pruning

| Field | Cap | Rule |
|---|---|---|
| `seen` | 1000 fingerprints | Oldest evicted first |
| `tasks` | 14 records | Oldest evicted first, but never one that is `starting`/`active` or still holds a `workspace_dir` |
| `last_digest.text` | 4000 characters | Truncated |
| `last_feed_errors` | 10 entries, 200 characters each | Truncated |

A task still holding a `workspace_dir` is never pruned, because that record is
the only thing that knows a directory is waiting to be removed.
