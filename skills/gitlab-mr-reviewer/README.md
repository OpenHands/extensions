# GitLab MR reviewer

A scheduled automation that reviews labelled, open, non-draft GitLab merge requests and posts one actionable summary note per head commit. It never approves or merges requests. A new head can receive a new review. Failed or timed-out reviews retry once, then post a failure note on the merge request; push a new head to request another review.

## Setup

Use **GitLab merge request review** in Automations > Templates, or run `/gitlab-mr-reviewer:setup`. Select projects, a review label (default `openhands-review`), the GitLab HTTPS API root (default `https://gitlab.com/api/v4`), and a polling schedule (default every 15 minutes).

Connect GitLab in Settings > Integrations or save `GITLAB_TOKEN` with `api` scope and permission to read merge requests and post notes. MCP-only access is not supported by this REST-backed template. Local deployments poll rather than receive webhooks. On Cloud the worker requires the automation KV store.

Merge request content is untrusted. Give the delegated agent only the permissions it needs.
