# State File Schema

The automation maintains a JSON state file that persists across polling runs.
This file tracks which HEAD SHA has been reviewed for each PR so the same
commit is never reviewed twice.

---

## File Location

```
{WORKSPACE_BASE_ROOT}/automation-state/pr_reviewer_{automation_id}.json
```

`WORKSPACE_BASE_ROOT` is derived by going two levels up from the `WORKSPACE_BASE`
environment variable (stripping `automation-runs/{run_id}`).

Example on a local install:

```
~/.openhands/workspaces/automation-state/pr_reviewer_abc12345-….json
```

The `automation_id` is read from the `AUTOMATION_EVENT_PAYLOAD` environment
variable (field `automation_id`).

---

## Top-Level Schema

```jsonc
{
  "version": 1,                   // schema version (integer)
  "repos": ["owner/repo"],        // monitored repositories
  "reviewed": {                   // see ReviewedMap below
    "owner/repo": {
      "42": { ... }
    }
  }
}
```

---

## `reviewed` Map

Structure: `reviewed[repo][str(pr_number)] = ReviewedRecord`

### `ReviewedRecord`

```jsonc
{
  "head_sha":        "abc123def456…",  // HEAD commit SHA at time of review
  "conversation_id": "550e8400-…",     // OpenHands conversation UUID
  "reviewed_at":    1716576060.0       // Unix timestamp (float) of when review was queued
}
```

A PR is **eligible for a new review** when its current HEAD SHA differs from
the `head_sha` recorded here, or when it does not appear in the map at all.

---

## Lifecycle

```
open PR detected
      │
      ├── head_sha in state AND matches current HEAD?
      │       └── YES → skip (already reviewed this commit)
      │
      └── NO (new PR or new commit)
              │
              ├── apply filters (label, draft)
              │       └── filtered out → skip
              │
              └── passed
                      │
                      ├── create OpenHands conversation
                      ├── post "review in progress" GitHub comment
                      └── save {head_sha, conversation_id, reviewed_at}
                              │
                      (next run: head_sha still matches → skip)
                              │
                      (PR author pushes new commit → head_sha changes → review again)
```

---

## Example State File

```json
{
  "version": 1,
  "repos": ["acme-corp/backend", "acme-corp/frontend"],
  "reviewed": {
    "acme-corp/backend": {
      "42": {
        "head_sha": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "reviewed_at": 1717243502.3
      },
      "15": {
        "head_sha": "f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5",
        "conversation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        "reviewed_at": 1717240800.0
      }
    },
    "acme-corp/frontend": {}
  }
}
```

---

## Resetting State

To force re-review of all currently open PRs, delete the state file:

```bash
# find the file path in the automation run logs, then:
rm ~/.openhands/workspaces/automation-state/pr_reviewer_<automation_id>.json
```

The next cron run will review all open eligible PRs fresh. Existing open PRs
will receive a new "review in progress" comment and a new conversation.
