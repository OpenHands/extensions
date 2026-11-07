# GitLab work item refiner

A scheduled automation that reads labelled GitLab issue-type work items and posts refinement feedback with open questions, recommendations, and requirements gaps. It posts once per label application; remove and reapply the label to request another pass. It does not modify issue fields, inspect repository code, or create merge requests.

## Setup

Use **GitLab work item refiner** in Automations > Templates, or run `/gitlab-prd-refiner:setup`. Select projects, a refinement label (default `openhands-refine`), the GitLab HTTPS API root (default `https://gitlab.com/api/v4`), and a polling schedule (default every 15 minutes).

Connect GitLab in Settings > Integrations or save `GITLAB_TOKEN` with `api` scope and permission to read issues and post notes. MCP-only access is not supported by this REST-backed template. Local deployments poll rather than receive webhooks. On Cloud the worker requires the automation KV store.

Issue content is untrusted. Give the delegated agent only the permissions it needs.
