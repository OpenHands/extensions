---
name: jira-create-pr
description: >
  This skill should be used when the user asks to "set up a Jira automation to create pull requests",
  "poll Jira for create-pr issues", "automatically create GitHub PRs from Jira tickets",
  "deploy a Jira create-pr automation", "create a Jira to GitHub PR workflow",
  or mentions automating GitHub PR creation from a Jira label.
  Deploys a cron-based OpenHands automation that watches a Jira Cloud project for issues
  labeled with a configurable label (default: "create-pr") and spawns an agent conversation
  to create a GitHub pull request for each new issue found.
---

# Jira → GitHub PR Automation

Deploys a cron automation that polls a Jira Cloud instance for open issues carrying a
configurable label and, for each new issue, starts an OpenHands agent conversation that
clones a target GitHub repository, creates a branch, implements or placeholders the
requested change, and opens a pull request.

## How It Works

1. **Poll** - every N minutes, `POST /rest/api/3/search/jql` on the Jira Cloud instance
   to find open issues with the configured label.
2. **Deduplicate** - compare results against a KV-store-backed set of already-processed
   issue keys; skip anything already handled.
3. **Dispatch** - for each new issue, call `POST /api/conversations` on the agent server
   to start an independent agent conversation with a PR-creation prompt.
4. **Persist** - record the processed issue key immediately so re-runs never duplicate work.

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
| `github_repo` | `acme-org/backend` | `owner/repo` format |
| `jira_label` | `create-pr` | Label to watch for (optional, defaults to `create-pr`) |
| `cron_schedule` | `*/5 * * * *` | Polling frequency in cron syntax |

### Step 2 - Create config.json

Create `config.json` next to `scripts/main.py` when packaging:

```json
{
  "jira_base_url":     "https://acme.atlassian.net",
  "jira_email":        "alice@acme.com",
  "jira_token_secret": "JIRA_CLOUD_KEY",
  "github_repo":       "acme-org/backend",
  "jira_label":        "create-pr"
}
```

### Step 3 - Package the tarball

Copy `scripts/main.py` from this skill and package it with the `config.json`:

```bash
WORK=$(mktemp -d)
cp <skill-dir>/scripts/main.py "$WORK/main.py"
# write config.json into $WORK/config.json (see Step 2)
tar -czf /tmp/jira-create-pr.tar.gz -C "$WORK" .
python3 -m py_compile "$WORK/main.py"   # validate syntax before uploading
```

### Step 4 - Upload the tarball

```bash
TARBALL_PATH=$(curl -s -X POST \
  "http://localhost:8000/api/automation/v1/uploads?name=jira-create-pr" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/gzip" \
  --data-binary @/tmp/jira-create-pr.tar.gz \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tarball_path'])")
```

### Step 5 - Create the automation

```bash
curl -s -X POST "http://localhost:8000/api/automation/v1" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Jira create-pr Poller - acme-org/backend\",
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
- **KV store** - persists `{"processed_keys": [...]}` between runs; falls back to a local file in dev environments where `AUTOMATION_KV_TOKEN` is absent.
- **Jira API** - uses `POST /rest/api/3/search/jql` (the current non-deprecated endpoint).
- **Conversation dispatch** - calls `POST /api/conversations` on the agent server with the current user's LLM/agent settings forwarded to the new conversation.
- **Error transparency** - captures Jira HTTP response bodies in error messages for fast diagnosis.

## Additional Resources

- **`references/setup.md`** - Jira API token creation, GitHub token scopes, cron schedule reference, and troubleshooting guide.
