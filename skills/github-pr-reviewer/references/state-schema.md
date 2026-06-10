# State File Schema

The automation maintains a JSON state file that persists across polling runs.
It is the source of truth for which PRs have been reviewed and which
conversations are still active.

---

## File Location

```
{WORKSPACE_BASE_ROOT}/automation-state/github_pr_reviewer_{automation_id}.json
```

`WORKSPACE_BASE_ROOT` is derived by going two levels up from the `WORKSPACE_BASE`
environment variable (stripping `automation-runs/{run_id}`).

Example on a local install:

```
~/.openhands/workspaces/automation-state/github_pr_reviewer_abc12345-….json
```

The `automation_id` is read from the `AUTOMATION_EVENT_PAYLOAD` environment
variable (field `automation_id`).

---

## Top-Level Schema

```jsonc
{
  "version": 1,          // schema version (integer)
  "repo": "owner/repo",  // the monitored repository
  "conversations": { }   // see ConversationRecord below
}
```

---

## `conversations` Map

Key: `"{pr_number}"` (string) — uniquely identifies a PR in the repo.

Value: **ConversationRecord**

```jsonc
{
  // Always present
  "pr_number":    42,                                      // GitHub PR number (integer)
  "html_url":     "https://github.com/owner/repo/pull/42", // PR URL
  "status":       "active",  // "active" | "closed" | "skipped"
  "last_activity": 1717200000.0,  // Unix timestamp of last state change

  // Present when status is "active" or "closed"
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                     // OpenHands conversation UUID

  // Present when status is "skipped"
  "reason": "diff too large (6000 lines)"
}
```

---

## Conversation Lifecycle

```
PR opened on GitHub
        │
        ▼
[active]  ── conversation created, acknowledgement comment posted
        │
        ▼ (on a later cron run, when conversation reaches terminal status)
[closed]  ── review posted to PR as GitHub comment
        │
        ▼ (if PR is merged/closed before review is ready)
[closed]  ── no comment posted (silently closed)

── or ──

PR diff too large
        │
        ▼
[skipped] ── explanatory comment posted, PR never re-queued
```

---

## Resetting State

To force a re-review of all PRs (e.g. after changing the review tone):

1. Delete the state file:
   ```bash
   rm ~/.openhands/workspaces/automation-state/github_pr_reviewer_<id>.json
   ```
2. The next cron run will treat all open PRs as new and queue reviews for each.
