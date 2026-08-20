# State Schema

The automation maintains a JSON state document **per repository**, persisted
across runs. It is the source of truth for which weeks have been handled, which
conversations are still active, and which clones are still on disk.

---

## Storage

**Primary (cloud):** the automation service's KV store, key
`state:{owner}__{repo}`, available when `AUTOMATION_KV_TOKEN` is injected.

**Fallback (local/dev):**

```
{WORKSPACE_BASE_ROOT}/automation-state/github_agents_md_{automation_id}_{owner}__{repo}.json
```

`WORKSPACE_BASE_ROOT` is two levels up from `WORKSPACE_BASE`, stripping
`automation-runs/{run_id}`; `automation_id` comes from `AUTOMATION_EVENT_PAYLOAD`.

---

## Top-Level Schema

```jsonc
{
  "version": 1,
  "repo": "owner/repo",
  "updated_at": 1717200000.0,
  "tasks": {},
  "skipped": { "2026-W35": "pull request still open" }
}
```

`skipped` records the weeks that were deliberately not worked, so a quiet month
can be explained without reading the run logs.

---

## `tasks` Map

Key: `"agents-md:{ISO year}-W{ISO week}"`, e.g. `agents-md:2026-W34`. The ISO
week is the idempotency key: a cron that fires more often, a retried run, or a
restarted service all resolve to the same key and do the work once.

Value: **TaskRecord**

```jsonc
{
  "period": "2026-W34",
  "agents_state": "present",
  "base_branch": "main",
  "base_sha": "0123456789abcdef...",
  "branch": "openhands/agents-md-2026-W34",
  "status": "active",
  "conversation_id": "conv_abc123",
  "workspace_dir": "/workspace/agents-md/owner__repo/2026-W34",
  "last_activity": 1717200000.0,
  "finalize_attempts": 1,
  "summary": "Refreshed the test command and added the lint step.",
  "opened_by": "agent",
  "pull_request_url": "https://github.com/owner/repo/pull/57",
  "pull_request_number": 57,
  "completed_at": 1717203600.0,
  "expired_after": 7200.5,
  "error": "git push ... failed (128): ..."
}
```

| Field | Written when | Meaning |
|---|---|---|
| `period` | claim | The ISO week this task belongs to |
| `agents_state` | claim | `present` or `missing` on the default branch; decides create vs update, and the pull request title |
| `base_branch` / `base_sha` | claim / start | What the clone starts from; commits are counted against the SHA |
| `branch` | start | The branch the pull request comes from |
| `status` | throughout | See the lifecycle below |
| `conversation_id` | start | The OpenHands conversation doing the work |
| `workspace_dir` | start | The clone. Removed, and the field dropped, once the task ends |
| `last_activity` | throughout | Drives the debounce, the two-hour abandonment, and the stalled-claim release |
| `finalize_attempts` | finalize | How many times pushing and opening the pull request has been tried |
| `summary` | end | The agent's closing message, capped, so a `no-changes` week still says why |
| `opened_by` | success | `agent` when the agent opened the pull request, `automation` when the script did |
| `pull_request_url` / `pull_request_number` | success | The pull request that was opened |
| `completed_at` / `expired_after` / `error` | end | When it finished, how long an abandoned one ran, and the last failure |

---

## Task Lifecycle

```
             a new ISO week, and no pull request of ours open
                                  │
                                  ▼
                             "starting"   ── claim persisted before the slow work.
                                  │           Released after 15 minutes if the run died.
                      clone + conversation
                                  │
                                  ▼
                              "active"
                                  │
          ┌───────────────┬───────┴────────┬──────────────────┐
          ▼               ▼                ▼                  ▼
      "closed"       "no-changes"      "failed"           "expired"
   pull request     AGENTS.md was   conversation        no terminal status
   opened, by the   already         errored, or         within two hours
   agent or by us   accurate        push/PR gave up
```

Every terminal status releases the clone, but only once the conversation is
confirmed stopped; when that cannot be confirmed, `workspace_dir` stays in the
record and a later run retries the removal.
