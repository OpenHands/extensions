# State File Schema

The automation maintains a JSON state file that persists across polling runs.
It is the source of truth for which trigger-label events have queued reviews
and which conversations are still active.

---

## File Location

```
{WORKSPACE_BASE_ROOT}/automation-state/github_pr_reviewer_label_event_{automation_id}.json
```

`WORKSPACE_BASE_ROOT` is derived by going two levels up from the `WORKSPACE_BASE`
environment variable, stripping `automation-runs/{run_id}`.

Example on a local install:

```
~/.openhands/workspaces/automation-state/github_pr_reviewer_label_event_abc12345-....json
```

The `automation_id` is read from the `AUTOMATION_EVENT_PAYLOAD` environment
variable, field `automation_id`.

---

## Top-Level Schema

```jsonc
{
  "version": 2,
  "repo": "owner/repo",
  "trigger_label": "openhands-review",
  "updated_at": 1717200000.0,
  "reviews": {},
  "prs": {}
}
```

---

## `reviews` Map

Key: `"{pr_number}:label:{label_event_id}"`. This makes the latest GitHub
`labeled` event the idempotency key. Re-applying the trigger label creates a new
GitHub event and therefore a new review request.

Value: **ReviewRecord**

```jsonc
{
  "pr_number": 42,
  "head_sha": "0123456789abcdef...",
  "trigger_label_event_id": 123456789,
  "trigger_label_event_created_at": "2026-06-12T00:00:00Z",
  "html_url": "https://github.com/owner/repo/pull/42",
  "status": "active",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "last_activity": 1717200000.0
}
```

`status` values:

| Status | Meaning |
|---|---|
| `active` | Review conversation is running or waiting to be collected |
| `closed` | Final result was posted, or the PR closed before collection |
| `stale` | PR head SHA changed before the review completed, so the result was suppressed |

When a review becomes stale, `stale_reason` records the old and new head SHAs.
When a review closes after posting, `completed_at` records the completion time.

---

## `prs` Map

Key: `"{pr_number}"`.

Value: latest PR snapshot observed during polling:

```jsonc
{
  "head_sha": "0123456789abcdef...",
  "label_present": true,
  "labels": ["openhands-review", "bug"],
  "last_seen": 1717200000.0
}
```

This snapshot is informational and helps diagnose whether a PR was skipped
because the trigger label was absent.

---

## Review Lifecycle

```
Trigger label applied on GitHub
        |
        v
[active]  - conversation created, acknowledgement comment posted
        |
        +-- PR closes/merges before collection --> [closed] without posting
        |
        +-- PR head SHA changes before collection --> [stale] without posting
        |
        v
[closed]  - final review comment posted
```

---

## Resetting State

To force the automation to reconsider previous label events, delete the state
file:

```bash
rm ~/.openhands/workspaces/automation-state/github_pr_reviewer_label_event_<id>.json
```

Usually, prefer removing and re-applying the trigger label. That preserves
history while creating a new review request.
