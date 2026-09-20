# State Schema

The automation maintains a JSON state document **per project**, persisted across
polling runs. It is the source of truth for which trigger-label events have
already queued work, which conversations are still active, and which clones are
still on disk.

Each project in `PROJECTS` gets its own document, so issue IIDs from different
projects never share a bucket.

The document holds only what a poll needs in order to decide what to do next.
Issue metadata that can be read back from GitLab is not mirrored here, so there
is nothing to drift.

---

## Storage

**Primary (cloud):** The state is stored in the automation service's built-in KV
store under the key `state:{group}__{project}` - for example
`state:gitlab-org__gitlab`. Subgroups keep their separators, so
`group/team/service` becomes `state:group__team__service`. The KV store is
available when `AUTOMATION_KV_TOKEN` is injected into the run environment. Each
automation has its own isolated namespace.

**Fallback (local/dev):** When the KV store is not available, the state is
written to a local JSON file at:

```
{WORKSPACE_BASE_ROOT}/automation-state/gitlab_issue_to_mr_{automation_id}_{group}__{project}.json
```

`WORKSPACE_BASE_ROOT` is derived by going two levels up from the `WORKSPACE_BASE`
environment variable, stripping `automation-runs/{run_id}`.

Example on a local install:

```
~/.openhands/workspaces/automation-state/gitlab_issue_to_mr_abc12345-..._myorg__backend.json
```

The `automation_id` is read from the `AUTOMATION_EVENT_PAYLOAD` environment
variable, field `automation_id`.

---

## Top-Level Schema

```jsonc
{
  "version": 1,
  "project": "group/project",
  "trigger_label": "openhands",
  "updated_at": 1717200000.0,
  "tasks": {}
}
```

---

## `tasks` Map

Key: `"{issue_iid}:label:{label_event_id}"`. This makes the latest GitLab
resource label event with `action: "add"` the idempotency key. Re-applying the
trigger label creates a new event and therefore a new task, on a new branch.

Value: **TaskRecord**

```jsonc
{
  "issue_iid": 42,
  "issue_title": "Retry uploads on a 502",
  "trigger_label_event_id": 123456789,
  "trigger_label_event_created_at": "2026-06-12T00:00:00Z",
  "web_url": "https://gitlab.com/group/project/-/issues/42",
  "base_branch": "main",
  "base_sha": "0123456789abcdef...",
  "branch": "openhands/issue-42",
  "status": "active",
  "conversation_id": "conv_abc123",
  "workspace_dir": "/workspace/issue-to-mr/group__project/issue-42-123456789",
  "last_activity": 1717200000.0,
  "finalize_attempts": 1,
  "merge_request_url": "https://gitlab.com/group/project/-/merge_requests/57",
  "merge_request_iid": 57,
  "completed_at": 1717203600.0,
  "expired_after": 7200.5,
  "error": "git push origin ... failed (128): ..."
}
```

| Field | Written when | Meaning |
|---|---|---|
| `issue_iid` | claim | The issue being implemented, by its project-scoped IID |
| `issue_title` | claim | Used for the commit message and the merge request title |
| `trigger_label_event_id` | claim | The GitLab label event this task belongs to |
| `trigger_label_event_created_at` | claim | When that label was applied |
| `web_url` | claim | The issue URL |
| `base_branch` | claim | The project's default branch at claim time |
| `base_sha` | start | The commit the clone starts from; commits are counted against it |
| `branch` | start | The branch the merge request is opened from |
| `status` | throughout | See the lifecycle below |
| `conversation_id` | start | The OpenHands conversation doing the work |
| `workspace_dir` | start | The clone. Removed, and the field dropped, once the task ends |
| `last_activity` | throughout | Drives the debounce, the two-hour abandonment, and the stalled-claim release |
| `finalize_attempts` | finalize | How many times pushing and opening the merge request has been tried |
| `merge_request_url` / `merge_request_iid` | success | The merge request that was opened |
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
 issue closed   conversation   agent produced   merge request     no terminal
 meanwhile      errored, or    no commits;      opened and        status within
                push/MR gave   its answer is    linked on the     two hours
                up after 3     posted on the    issue
                attempts       issue
```

Every terminal status releases the clone, but only once the conversation is
confirmed stopped. When that cannot be confirmed, `workspace_dir` stays in the
record and a later poll retries the removal.
