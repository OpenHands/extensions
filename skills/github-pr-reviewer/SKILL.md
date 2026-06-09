---
name: github-pr-reviewer
description: >
  Create an automation that reviews GitHub pull requests when they are opened
  or updated. Inspects the diff, changed files, tests, and existing discussion
  via GitHub MCP, then posts a concise review highlighting risks, security
  issues, missing tests, and next steps.
triggers:
  - /pr-reviewer:setup
---

# GitHub PR Reviewer Automation

Set up a cron or event-triggered automation that reviews GitHub pull requests.

---

## Prerequisites

### Required integration

- **GitHub MCP** must be installed in Settings → MCP.

### Information to collect

Ask the user for:

1. **Repositories** — which repos should be watched (e.g. `myorg/backend`, `myorg/frontend`)
2. **Trigger type** — event-based (reacts to `pull_request.opened` / `pull_request.synchronize`) or cron-based polling
3. **Review tone** — thorough, concise, or friendly
4. **Auto-post or draft** — should reviews be posted as GitHub comments automatically, or saved as draft artifacts for human approval first?
5. **Filters** — any label, branch, or author filters (e.g. skip drafts, only review PRs with `needs-review` label)

---

## Setup Workflow

### Step 1 — Verify GitHub MCP access

Confirm the GitHub MCP integration is working:
```
Use the GitHub MCP to list recent pull requests in one of the target repositories.
```

If it fails, tell the user to install the GitHub MCP integration first.

### Step 2 — Determine trigger type

**Event-based (recommended if publicly reachable):**
Check `<RUNTIME_SERVICES>` for deployment reachability. If the deployment has a public URL, recommend an event trigger on `pull_request.opened` and `pull_request.synchronize`.

**Cron-based (local/private deployments):**
If the deployment is local, set up a cron schedule (e.g. every 5 minutes) that polls for recently updated PRs.

### Step 3 — Build the review prompt

Construct a prompt for the automation that includes:
- The user's chosen repositories
- Review focus areas (correctness, security, tests, maintainability)
- Review tone preference
- Whether to auto-post or draft

### Step 4 — Create the automation

Read the Automation backend URL and auth from `<RUNTIME_SERVICES>`:
- Use the **Automation backend** `url_from_agent` as `OPENHANDS_HOST`
- Auth: `X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY`

Use the **prompt preset** endpoint, but do it in a shell-neutral way:
1. Write the request body to a JSON file in the workspace (for example `.agent_tmp/github-pr-reviewer-request.json`).
2. POST that file with the HTTP client that fits the current environment (`curl`, `Invoke-RestMethod`, or a short Python script).

Request body:
```json
{
  "name": "GitHub PR Reviewer",
  "prompt": "<constructed review prompt>",
  "trigger": <trigger config from step 2>
}
```

The important part is the payload shape and endpoint; do not force bash-only quoting or heredoc patterns when creating the file or sending the request.

### Step 5 — Confirm

Tell the user:
> ✅ **GitHub PR Reviewer** is running!
>
> - Automation ID: `{id}`
> - Repositories: `{repo list}`
> - Trigger: `{trigger description}`
> - Review style: `{tone}`, `{auto-post or draft}`
