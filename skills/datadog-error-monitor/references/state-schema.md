# State File Schema

The monitor persists all state between cron runs in a single JSON file.

## Location

```
~/.openhands/workspaces/automation-state/dd_monitor_{automation_id}.json
```

The path is derived at runtime from the `WORKSPACE_BASE` environment variable
(two levels up, into `automation-state/`). The file is created on the first run
and is safe to delete — the monitor will rebuild from scratch, treating all logs
as uncategorized on the next run.

---

## Top-level Fields

| Field | Type | Description |
|---|---|---|
| `version` | `int` | Schema version (currently `1`) |
| `last_poll_timestamp` | `string` (ISO 8601 UTC) | Upper bound of the last successful Datadog query. The next query starts here (minus a 60 s overlap). |
| `active_conversation` | `object \| null` | The single in-flight OpenHands investigation conversation, or `null` if none is running. |
| `known_patterns` | `object` | Map of pattern UUID → pattern definition. Updated by the investigation agent between runs. |

---

## `active_conversation` Object

Present when an investigation is in progress; `null` otherwise. The script
checks conversation status on every run and clears this field when the
conversation reaches a terminal state (`idle`, `finished`, `error`, `stuck`).

While `active_conversation` is non-null, the script skips trigger evaluation —
logs are still fetched and pattern history is still updated, but no new
conversation is started.

| Field | Type | Description |
|---|---|---|
| `id` | `string` | OpenHands conversation ID |
| `started_at` | `string` (ISO 8601 UTC) | When the conversation was created |
| `trigger_summary` | `string` | Human-readable description of what triggered the investigation |
| `status` | `string` | Last known status (`"running"`) — updated by the script when it checks |

---

## `known_patterns` Object

Keys are UUIDs assigned when a pattern is first created (by the investigation
agent). Values are pattern definition objects.

**The investigation agent is responsible for adding new entries** to this object
when it categorizes uncategorized logs. The script reads the file at the start
of every run and picks up any patterns written by the agent.

### Pattern Definition

| Field | Type | Description |
|---|---|---|
| `name` | `string` | Concise human-readable label, e.g. `"Redis connection timeout in AuthService"` |
| `regex` | `string` | Python regex (`re.IGNORECASE \| re.DOTALL`) matched against the extracted log message. Must be broad enough to catch future occurrences — avoid encoding timestamps, request IDs, memory addresses, or UUIDs. |
| `run_history` | `list[int]` | Hit counts from the most recent runs (oldest first). Capped at 20 entries. Updated by the script every run, even when the count is 0. |
| `last_seen` | `string \| null` (ISO 8601 UTC) | Timestamp of the most recent matching log. `null` if never seen since pattern was added. |
| `examples` | `list[object]` | Most recent matching log snippets (up to `EXAMPLES_PER_PATTERN`, configurable). Oldest entries are dropped as new ones arrive. |

### Example Object (inside `examples`)

| Field | Type | Description |
|---|---|---|
| `timestamp` | `string` | Log event timestamp from Datadog |
| `message` | `string` | Truncated log message (max 500 chars), including a stack trace prefix if present |

---

## Agent Protocol for Writing New Patterns

When the investigation agent identifies a new error category, it **reads** the
current state file, adds the new pattern under `known_patterns`, and **writes**
the file back atomically. The agent must:

1. Generate a UUID for the pattern key (Python: `import uuid; str(uuid.uuid4())`)
2. Set `run_history` to a list containing the count from this investigation window
3. Set `last_seen` to the current UTC timestamp
4. Add up to `EXAMPLES_PER_PATTERN` examples

The agent must **not** overwrite any existing `known_patterns` entries, and must
preserve all other top-level fields (`last_poll_timestamp`, `active_conversation`).

### Concurrent Write Safety

The script runs every 15 minutes with a ~120 s timeout. The investigation agent
runs asynchronously and typically takes longer. Since the script completes well
before the agent finishes, write conflicts are unlikely. In the rare case of
overlap, the last writer wins on the state file — at worst, one run's pattern
count update is lost. This recovers automatically on the next poll.

---

## Annotated Example

```json
{
  "version": 1,
  "last_poll_timestamp": "2024-03-15T14:30:00Z",
  "active_conversation": null,
  "known_patterns": {
    "a1b2c3d4-e5f6-7890-abcd-ef1234567890": {
      "name": "Redis connection timeout in CacheService",
      "regex": "(?:redis|Redis).*(?:timeout|connection refused|ECONNREFUSED).*CacheService",
      "run_history": [0, 2, 0, 0, 1, 47, 39],
      "last_seen": "2024-03-15T14:28:41Z",
      "examples": [
        {
          "timestamp": "2024-03-15T14:28:41Z",
          "message": "Error: Redis connection refused at CacheService.get (cache.js:42)\n    at RedisClient.connect (redis.js:91)"
        },
        {
          "timestamp": "2024-03-15T14:15:03Z",
          "message": "Redis timeout after 5000ms at CacheService.set (cache.js:58)"
        }
      ]
    },
    "f0e1d2c3-b4a5-6789-0abc-def123456789": {
      "name": "Unhandled NullPointerException in PaymentService",
      "regex": "NullPointerException.*at.*PaymentService\\.(process|charge|refund)",
      "run_history": [3, 3, 4, 2, 3, 3, 4],
      "last_seen": "2024-03-15T14:27:19Z",
      "examples": [
        {
          "timestamp": "2024-03-15T14:27:19Z",
          "message": "java.lang.NullPointerException\n    at com.example.PaymentService.processPayment(PaymentService.java:127)"
        }
      ]
    }
  }
}
```

---

## Lifecycle Notes

- **First run:** `known_patterns` is empty. All logs are uncategorized. An
  investigation conversation is started unconditionally (assuming at least one
  log matches the query). The agent builds the initial pattern library.

- **Steady state:** The script matches logs, increments run_history, and only
  triggers if an unknown log appears or a pattern count spikes above the
  rolling baseline × `SPIKE_MULTIPLIER`.

- **Retired patterns:** Patterns are never automatically removed. A pattern with
  consistently zero counts for many runs is harmless — it just accumulates zeros
  in `run_history`. If a fixed bug no longer produces logs, its count drops to
  zero and stays there. You can manually remove patterns from the state file.

- **Resetting:** Delete the state file to reset everything. The next run will
  treat the system as fresh — all logs uncategorized, no baseline history.
