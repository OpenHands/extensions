# State Schema

The automation keeps one JSON document **per repository**, persisted across runs.
It records which file contents are already clean and which conversation, if any,
is still working on the repository.

---

## Storage

**Primary (cloud):** the automation service's KV store, available when
`AUTOMATION_KV_TOKEN` is injected. A cloud run without it fails rather than starting
over every week.

The KV store rejects any single value over 64 KB, and `files` grows with the
repository, so the document is split across keys:

| Key | Holds |
|---|---|
| `state:{owner}__{repo}` | Everything below except `files`, plus `file_keys` listing the chunk keys |
| `state:{owner}__{repo}:files:{generation}:{n}` | A slice of `files`, at most 48 KB each |

Each save writes its chunks under a new generation, then the head key, then deletes the
previous generation's chunks, so a run that dies part way leaves the head pointing at a
complete set. A version 1 document, which kept `files` inline in the head key, is read
and rewritten in this layout on the next save. State is saved before the conversation
starts, so a run that cannot store its state fails without starting one.

**Fallback (local/dev):**

```
{WORKSPACE_BASE_ROOT}/automation-state/comment_cleanup_{automation_id}_{owner}__{repo}.json
```

`WORKSPACE_BASE_ROOT` is two levels up from `WORKSPACE_BASE`, stripping
`automation-runs/{run_id}`; `automation_id` comes from `AUTOMATION_EVENT_PAYLOAD`.

---

## Top-Level Schema

```jsonc
{
  "version": 2,
  "repo": "owner/repo",
  "files": {
    "src/app.py": {"at": "2026-10-28", "fp": ["<original sha>", "<cleaned sha>"]}
  },
  "pending": null,          // or the conversation started by the last run, below
  "pull_request": null,     // or {"number": 12, "url": "..."} while its pull request is open
  "runs": [],               // the last 20 run summaries
  "updated_at": "2026-10-28T09:00:00+00:00"
}
```

### `files`

A fingerprint is a git blob SHA: the value `git hash-object`, `git ls-tree`, and the
GitHub pull request files API all report. A file is skipped while its current
fingerprint is in `fp`, without being read.

| `fp` holds | Written when |
|---|---|
| `[original]` | The file has no comments, or the agent examined it and changed nothing |
| `[original, cleaned]` | The cleanup pull request changed it |

Keeping both means the file stays clean whether the pull request is merged (the
default branch now holds `cleaned`) or closed (it still holds `original`). Any other
edit produces a new fingerprint and the file is queued again, ahead of files never
examined. Entries for paths no longer on the default branch are pruned each run.

Modification times are not used: a fresh clone stamps every file with the time of
the clone, while a blob SHA changes exactly when the content does.

### `pending`

```jsonc
{
  "conversation_id": "...",
  "branch": "openhands/comment-cleanup/2026-10-28-a1b2c3",
  "started_at": "2026-10-28T09:00:05+00:00",
  "started_ts": 1793178005.0,
  "files": {"src/app.py": "<original sha>"},   // exactly what the agent was given
  "workspace_dir": null                        // the clone, on a local Agent Canvas only
}
```

The next run finalizes it once the conversation has stopped:

| Outcome | Recorded |
|---|---|
| A pull request exists for `branch` | Each file's original fingerprint, plus its cleaned one from the pull request |
| The agent ended with `CLEANUP_RESULT: NO_CHANGES` | Each file's original fingerprint |
| Anything else | Nothing; the files are queued again |

When a pull request is found it is also stored in `pull_request`, and later runs
skip the repository until GitHub reports it closed or merged.

A conversation still running after three days is abandoned without recording
anything. On a local Agent Canvas the clone in `workspace_dir` is removed once the
conversation has stopped.

### `runs`

```jsonc
{
  "at": "2026-10-28T09:00:00+00:00",
  "finalized": "pull request https://github.com/owner/repo/pull/12",
  "skipped": "cleanup pull request still open: ...",
  "auto_cleared": 12,
  "queued": 40,
  "deferred": 3,
  "conversation_id": "..."
}
```

Every key except `at` is present only when it applies.

---

## Resetting

Delete the repository's KV keys (`state:{owner}__{repo}` and its `:files:` chunks), or
its state file, to examine every file again.
