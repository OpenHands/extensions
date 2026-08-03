---
name: jira-issue-to-pr
description: >
  This skill should be used when the user asks to "set up a Jira automation to create pull requests",
  "poll Jira for create-pr issues", "automatically create GitHub PRs from Jira tickets",
  "deploy a Jira issue-to-PR automation", "create a Jira to GitHub PR workflow",
  or mentions automating GitHub PR creation from a Jira label.
  Deploys a cron-based OpenHands automation that watches a Jira Cloud project for issues
  labeled with a configurable label (default: "create-pr") and spawns an agent conversation
  to create a GitHub pull request for each new issue found. The target GitHub repository
  is read from the body of the Jira ticket - no repo parameter is required at deploy time.
---

# Jira → GitHub PR Automation

Deploys a cron automation that polls a Jira Cloud instance for open issues carrying a
configurable label and, for each new issue, starts an OpenHands agent conversation that
clones the GitHub repository specified in the ticket body, creates a branch, implements
or placeholders the requested change, and opens a pull request. Once the conversation
starts, it also posts a comment on the Jira ticket: "I'm on it: &lt;conversation URL&gt;".

## How It Works

1. **Poll** - every N minutes, `POST /rest/api/3/search/jql` on the Jira Cloud instance
   to find open issues with the configured label.
2. **Deduplicate** - on the very first run the script records a `first_run_at` baseline
   timestamp in the KV store; any issue whose `updated` timestamp predates that baseline
   is skipped (no backfill blast on first deploy). Using `updated` rather than `created`
   means an old issue that has its label added after the automation is deployed will still
   be picked up. Subsequent runs filter by both `first_run_at` and a KV-backed set of
   already-processed issue keys. A `max_new_per_run` cap (default 5) limits conversations
   started per cron firing as additional defense-in-depth.
3. **Dispatch** - for each new issue, call `POST /api/conversations` on the agent server
   to start an independent agent conversation with a PR-creation prompt. The prompt
   instructs the agent to extract the target GitHub repository (`owner/repo`) from the
   ticket body.
4. **Comment** - immediately after the conversation is created, post a Jira comment on the
   issue: `I'm on it: <conversation URL>`.
5. **Persist** - record the processed issue key so re-runs never duplicate work.

The polling run is lightweight (stdlib only, no SDK install); LLM costs are incurred only
when new issues are actually found.

## Prerequisites

Before deploying, ensure the following are in place:

| Requirement | Details |
|---|---|
| **Jira API token** | Stored as an OpenHands secret (see [Jira API token setup](#jira-api-token)) |
| **GitHub token** | Must be stored as an OpenHands secret with `repo` + `workflow` scope so the spawned conversation can push branches and open PRs |
| **Jira label** | The label to watch for (default: `create-pr`) must exist in the Jira project |
| **GitHub repo** | The target repository must exist and the GitHub token must have write access |

## Deploying the Automation

### Step 1 - Collect parameters

Gather the following from the user before proceeding:

| Parameter | Example | Notes |
|---|---|---|
| `jira_base_url` | `https://acme.atlassian.net` | No trailing slash |
| `jira_email` | `alice@acme.com` | Atlassian account email for Basic auth |
| `jira_token_secret` | `JIRA_CLOUD_KEY` | Name of the OpenHands secret holding the API token |
| `jira_label` | `create-pr` | Label to watch for (optional, defaults to `create-pr`) |
| `max_new_per_run` | `5` | Max conversations dispatched per cron firing (optional, defaults to `5`) |
| `cron_schedule` | `*/5 * * * *` | Polling frequency in cron syntax |

> **Note**: The GitHub repository is not configured here. Each Jira ticket body must include
> a reference to the target GitHub repo in `owner/repo` format (e.g. `acme-org/backend`).
> The spawned agent extracts it from the ticket text.

### Step 2 - Create config.json

Create `config.json` next to `scripts/main.py` when packaging:

```json
{
  "jira_base_url":     "https://acme.atlassian.net",
  "jira_email":        "alice@acme.com",
  "jira_token_secret": "JIRA_CLOUD_KEY",
  "jira_label":        "create-pr",
  "max_new_per_run":   5
}
```

### Step 3 - Package the tarball

Copy `scripts/main.py` from this skill and package it with the `config.json`:

```bash
WORK=$(mktemp -d)
cp <skill-dir>/scripts/main.py "$WORK/main.py"
# write config.json into $WORK/config.json (see Step 2)
tar -czf /tmp/jira-issue-to-pr.tar.gz -C "$WORK" .
python3 -m py_compile "$WORK/main.py"   # validate syntax before uploading
```

### Step 4 - Upload the tarball

```bash
TARBALL_PATH=$(curl -s -X POST \
  "http://localhost:8000/api/automation/v1/uploads?name=jira-issue-to-pr" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/gzip" \
  --data-binary @/tmp/jira-issue-to-pr.tar.gz \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tarball_path'])")
```

### Step 5 - Create the automation

```bash
curl -s -X POST "http://localhost:8000/api/automation/v1" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Jira issue-to-PR Poller\",
    \"trigger\": {
      \"type\":     \"cron\",
      \"schedule\": \"*/5 * * * *\",
      \"timezone\": \"UTC\"
    },
    \"tarball_path\": \"$TARBALL_PATH\",
    \"entrypoint\":   \"python3 main.py\",
    \"timeout\":      540
  }" | python3 -m json.tool
```

Save the returned `id` - use it for updates and monitoring.

### Step 6 - Verify with a test dispatch

```bash
curl -s -X POST \
  "http://localhost:8000/api/automation/v1/<AUTOMATION_ID>/dispatch" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" | python3 -m json.tool

# After ~30 seconds, check the run status:
curl -s "http://localhost:8000/api/automation/v1/<AUTOMATION_ID>/runs?limit=1" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  | python3 -c "import sys,json; r=json.load(sys.stdin)['runs'][0]; print(r['status'], r.get('error_detail'))"
```

## Updating an Existing Deployment

To change configuration or update the script:

1. Edit `config.json` with new values.
2. Repackage and upload a new tarball (Steps 3-4 above).
3. PATCH the existing automation with the new `tarball_path`:

```bash
curl -s -X PATCH \
  "http://localhost:8000/api/automation/v1/<AUTOMATION_ID>" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"tarball_path\": \"<NEW_TARBALL_PATH>\"}"
```

## Resetting Processed State

To reprocess issues that were already handled (e.g., after testing), clear the KV store:

```bash
curl -s -X DELETE \
  "http://localhost:8000/api/automation/v1/<KV_BASE>/v1/kv/state" \
  -H "Authorization: Bearer $AUTOMATION_KV_TOKEN"
```

Or delete and recreate the automation to start with a clean state.

## Script Reference

The automation script lives at `scripts/main.py`. Key behaviors:

- **No SDK dependencies** - pure Python stdlib; no `setup.sh` or `uv` install needed.
- **Config file** - reads all parameters from `config.json` co-located with the script.
- **First-run baseline** - on the very first execution the script writes `first_run_at` (UTC timestamp) into the KV store and exits without dispatching; issues whose `updated` timestamp predates that baseline are skipped on all subsequent runs. Using `updated` (not `created`) means an old issue that has its label applied after deployment is correctly treated as new.
- **Per-run cap** - `max_new_per_run` (default 5) limits how many conversations are started per cron firing; any remaining new issues are dispatched on the next run.
- **KV store** - persists `{"processed_keys": [...], "first_run_at": "..."}` between runs; falls back to a local file in dev environments where `AUTOMATION_KV_TOKEN` is absent.
- **Jira API** - uses `POST /rest/api/3/search/jql` (the current non-deprecated endpoint).
- **Conversation dispatch** - calls `POST /api/conversations` on the agent server. Uses `X-Expose-Secrets: encrypted` to obtain the LLM `api_key` as a Fernet token that is decrypted server-side (`secrets_encrypted: True`), so the real key is never present in the network payload. `terminal` and `file_editor` tools are merged into `agent_settings` explicitly - without them the SDK Agent defaults to think+finish only and cannot clone repos or create files. User secrets are forwarded as `LookupSecret` references so the spawned conversation can access `GITHUB_TOKEN` and other secrets.
- **Error transparency** - captures Jira HTTP response bodies in error messages for fast diagnosis.

## Known Limitations

### Pre-existing issues updated after deployment

The deduplication filter compares each issue's `fields.updated` timestamp against
`first_run_at`. `updated` is Jira's last-modified timestamp for the issue as a whole —
it advances whenever **any** field changes (comments, priority, description, status, etc.),
not only when the `create-pr` label is applied.

This means a pre-existing issue that already carried the label at deployment time can
slip through the filter if it is later updated for an unrelated reason (e.g. someone adds
a comment), because its `updated` timestamp will have advanced past `first_run_at` while
its key is not yet in `processed_keys`.

**Workaround:** The only fully reliable way to detect exactly when a label was applied
is the Jira changelog API (`GET /rest/api/3/issue/{key}/changelog`), which requires an
extra HTTP call per issue. To avoid that overhead, keep the automation's scope narrow:
use a label that is exclusively added as a PR-creation signal and is not already present
on issues at the time of deployment.

Once an issue is successfully dispatched its key is written to `processed_keys` in the
KV store and is **permanently skipped on every future run** — regardless of subsequent
label changes, comments, or any other updates to the issue. The only way to re-trigger a
previously processed issue is to manually clear the KV store or delete and recreate the
automation. This means the risk window described above is finite: as soon as the
automation processes a pre-existing issue (even accidentally), it will never dispatch
that issue again.

## Additional Resources

- **`references/setup.md`** - Jira API token creation, GitHub token scopes, cron schedule reference, and troubleshooting guide.
