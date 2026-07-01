# Setup & Troubleshooting Reference

## Jira API Token

### Create a token

1. Log in to [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens).
2. Click **Create API token**.
3. Give it a label (e.g., `openhands-create-pr`) and click **Create**.
4. Copy the token value - it is shown only once.

### Store the token as an OpenHands secret

Navigate to **Settings → Secrets** in the OpenHands UI and add a new secret:

| Field | Value |
|---|---|
| Name | `JIRA_CLOUD_KEY` (or any name; set `jira_token_secret` in `config.json` to match) |
| Value | The API token copied above |

### How the script authenticates

The script constructs an HTTP Basic auth header:

```
Authorization: Basic base64(<jira_email>:<jira_token>)
```

The Jira Cloud REST API v3 requires this for all authenticated requests.

---

## GitHub Token

The spawned agent conversation clones the target repository, pushes a new branch, and
opens a pull request. The GitHub token must be stored as an OpenHands secret and must
have the following scopes:

| Scope | Required for |
|---|---|
| `repo` | Clone private repos, push branches, read/write PR content |
| `workflow` | Push changes that touch `.github/workflows/` files |

The token does **not** need to be referenced in `config.json` - the spawned conversation
inherits the user's configured secrets automatically through the agent server.

### Store the token

Navigate to **Settings → Secrets** and store the token under the name `GITHUB_TOKEN`
(or whatever name is expected by the agent's GitHub skill).

---

## config.json Field Reference

| Field | Required | Default | Description |
|---|---|---|---|
| `jira_base_url` | ✅ | - | Full URL of your Atlassian instance, e.g. `https://acme.atlassian.net` |
| `jira_email` | ✅ | - | Email address of the Atlassian account that owns the API token |
| `jira_token_secret` | ❌ | `"JIRA_CLOUD_KEY"` | Name of the OpenHands secret holding the Jira API token |
| `jira_label` | ❌ | `"create-pr"` | Jira issue label to watch for |

> **GitHub repo**: not a config field. The target repository is read from the body of each
> Jira ticket. Ticket authors must include the repo in `owner/repo` format or as a full
> GitHub URL (e.g. `https://github.com/acme-org/backend`).

---

## Cron Schedule Reference

| Schedule | Meaning |
|---|---|
| `*/5 * * * *` | Every 5 minutes |
| `*/15 * * * *` | Every 15 minutes |
| `0 * * * *` | Every hour |
| `0 9 * * 1-5` | Weekdays at 9 AM UTC |
| `0 9,17 * * *` | Daily at 9 AM and 5 PM UTC |

For high-frequency schedules (tighter than 15 minutes), consider that each run with new
issues spawns one conversation per issue. Set `timeout` on the automation to something
less than the interval to avoid overlapping runs - the KV store prevents double-processing
even if runs do overlap.

---

## Jira Search API Notes

The script uses `POST /rest/api/3/search/jql` - the current non-deprecated Jira Cloud
search endpoint. All older endpoints return 410 Gone:

| Removed endpoint | Returns |
|---|---|
| `GET /rest/api/2/search` | 410 Gone |
| `GET /rest/api/3/search` | 410 Gone |
| `POST /rest/api/3/search` | 410 Gone |

Reference: [Atlassian changelog CHANGE-2046](https://developer.atlassian.com/changelog/#CHANGE-2046)

The `POST /rest/api/3/search/jql` request body:

```json
{
  "jql":        "labels = \"create-pr\" AND statusCategory != Done",
  "fields":     ["key", "summary", "description", "status"],
  "maxResults": 50
}
```

The response is `SearchAndReconcileResults`; the script reads the `issues` array from it.

---

## Troubleshooting

### `Jira search failed 401`

- Wrong email in `jira_email` - must match the Atlassian account that owns the token.
- Token expired or revoked - create a new one at id.atlassian.com and update the secret.
- Token copied with extra whitespace - secrets are stored/retrieved with `.strip()`.

### `Jira search failed 403`

- The Atlassian account does not have **Browse Projects** permission on the target project.
- Grant the account project-level read access in Jira's project settings.

### `Jira search failed 400` with `"The value 'xxx' does not exist for the field 'labels'"`

- The label does not exist in Jira yet. Create at least one issue with that label first,
  or create the label explicitly in **Jira Settings → Issues → Labels**.

### Run completes but no conversation is started

- All matching issues are already in `processed_keys`. Clear state or add a new issue.
- The Jira project has issues with the label but all are in a Done status category.
  The JQL filter is `statusCategory != Done` - reopen or create a fresh issue.

### Conversation started but no PR appears

- The spawned conversation inherits the user's agent/LLM settings. Check the conversation
  in the OpenHands UI (it appears in the conversations list under the automation run).
- The GitHub token may lack `repo` scope to push or open PRs.
- The target repo's default branch may be protected; the token must have bypass permission,
  or the PR should be created against a different base branch.

### `fire_callback error` in output

- Non-fatal. The automation service callback URL is unavailable (common in local dev).
  This does not affect conversation dispatch.

### KV store not available (state falls back to local file)

- `AUTOMATION_KV_TOKEN` is not injected, meaning the deployment is not configured with a
  KV secret. State is written to a local file under `$WORKSPACE_BASE/../automation-state/`.
  This is lost between runs in cloud pod deployments - configure the KV store secret on
  the automation service to get persistent state.

---

## Multiple Deployments

To watch multiple Jira projects or multiple GitHub repos, deploy separate automations —
one per `config.json`. Each automation has its own KV-store namespace (keyed by
automation ID), so processed-key sets do not cross-contaminate.

Example: two automations, one per project:

| Automation name | `jira_base_url` | `jira_label` | GitHub repo (in ticket body) |
|---|---|---|---|
| `Jira issue-to-PR - frontend` | `https://acme.atlassian.net` | `create-pr` | `acme/frontend` (written by ticket author) |
| `Jira issue-to-PR - backend` | `https://acme.atlassian.net` | `create-pr-backend` | `acme/backend` (written by ticket author) |
