# State Schema

The automation maintains a JSON state document **per repository**, persisted
across polling runs. It is the source of truth for which trigger-label events
have already queued work, which conversations are still active, and which clones
are still on disk.

Each repository in `REPOS` gets its own document, so issue numbers from different
repositories never share a bucket.

The document holds only what a poll needs in order to decide what to do next.
Issue metadata that can be read back from GitHub is not mirrored here, so there
is nothing to drift.

---

## Storage

**Primary (cloud):** The state is stored in the automation service's built-in KV
store under the key `state:{owner}__{repo}` - for example
`state:OpenHands__extensions`. The KV store is available when
`AUTOMATION_KV_TOKEN` is injected into the run environment. Each automation has
its own isolated namespace.

**Fallback (local/dev):** When the KV store is not available, the state is
written to a local JSON file at:

```
{WORKSPACE_BASE_ROOT}/automation-state/github_issue_to_pr_{automation_id}_{owner}__{repo}.json
```

`WORKSPACE_BASE_ROOT` is derived by going two levels up from the `WORKSPACE_BASE`
environment variable, stripping `automation-runs/{run_id}`.

Example on a local install:

```
~/.openhands/workspaces/automation-state/github_issue_to_pr_abc12345-..._myorg__backend.json
```

The `automation_id` is read from the `AUTOMATION_EVENT_PAYLOAD` environment
variable, field `automation_id`.

---

## Top-Level Schema

```jsonc
{
  "version": 1,
  "repo": "owner/repo",
  "trigger_label": "openhands",
  "updated_at": 1717200000.0,
  "tasks": {}
}
```

---

## `tasks` Map

Key: `"{issue_number}:label:{label_event_id}"`. This makes the latest GitHub
`labeled` event the idempotency key. Re-applying the trigger label creates a new
GitHub event and therefore a new task, on a new branch.

Value: **TaskRecord**

```jsonc
{
  "issue_number": 42,
  "issue_title": "Retry uploads on a 502",
  "trigger_label_event_id": 123456789,
  "trigger_label_event_created_at": "2026-06-12T00:00:00Z",
  "html_url": "https://github.com/owner/repo/issues/42",
  "base_branch": "main",
  "base_sha": "0123456789abcdef...",
  "branch": "openhands/issue-42",
  "status": "active",
  "conversation_id": "conv_abc123",
  "workspace_dir": "/workspace/issue-to-pr/owner__repo/issue-42-123456789",
  "last_activity": 1717200000.0,
  "finalize_attempts": 1,
  "pull_request_url": "https://github.com/owner/repo/pull/57",
  "pull_request_number": 57,
  "completed_at": 1717203600.0,
  "expired_after": 7200.5,
  "error": "git push origin ... failed (128): ..."
}
```

| Field | Written when | Meaning |
|---|---|---|
| `issue_number` | claim | The issue being implemented |
| `issue_title` | claim | Used for the commit message and the pull request title |
| `trigger_label_event_id` | claim | The GitHub `labeled` event this task belongs to |
| `trigger_label_event_created_at` | claim | When that label was applied |
| `html_url` | claim | The issue URL |
| `base_branch` | claim | The repository's default branch at claim time |
| `base_sha` | start | The commit the clone starts from; commits are counted against it |
| `branch` | start | The branch the pull request is opened from |
| `status` | throughout | See the lifecycle below |
| `conversation_id` | start | The OpenHands conversation doing the work |
| `workspace_dir` | start | The clone. Removed, and the field dropped, once the task ends |
| `last_activity` | throughout | Drives the debounce, the two-hour abandonment, and the stalled-claim release |
| `finalize_attempts` | finalize | How many times pushing and opening the pull request has been tried |
| `pull_request_url` / `pull_request_number` | success | The pull request that was opened |
| `completed_at` | end | When the task reached a terminal status |
| `expired_after` | expiry | Seconds the conversation ran before being abandoned |
| `error` | failure | The last finalization error, after the retries ran out |

---

## Task Lifecycle

```
                    label event seen
                           │
                           ▼
                      "starting"   ── claim persisted before the slow work, so an
                           │           overlapping poll cannot start it twice.
                           │           Released after 15 minutes if the poll died.
                clone + conversation
                           │
                           ▼
                       "active"
                           │
     ┌─────────────┬───────┴────────┬──────────────┬─────────────────┐
     ▼             ▼                ▼              ▼                 ▼
"issue-closed"  "failed"      "no-changes"     "closed"          "expired"
 issue closed   conversation   agent produced   pull request      no terminal
 meanwhile      errored, or    no commits;      opened and        status within
                push/PR gave   its answer is    linked on the     two hours
                up after 3     posted on the    issue
                attempts       issue
```

Every terminal status releases the clone, but only once the conversation is
confirmed stopped. When that cannot be confirmed, `workspace_dir` stays in the
record and a later poll retries the removal.
