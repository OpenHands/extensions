# GitLab work item refiner

A scheduled or event-triggered automation that reads labelled GitLab issue-type work items and posts refinement feedback with open questions, recommendations, and requirements gaps. It posts once per label application; remove and reapply the label to request another pass. Failed refinements retry once, then post a failure note on the issue. It does not modify issue fields, inspect repository code, or create merge requests.

## Setup

Use **GitLab work item refiner** in Automations > Templates, or run `/gitlab-prd-refiner:setup`. Select projects, a refinement label (default `openhands-refine`), the GitLab HTTPS API root (default `https://gitlab.com/api/v4`), and a schedule (default every 15 minutes) or **Event**. An event run handles just the issue sent by GitLab, after rechecking its project, open state, label and latest label application through the API. It waits for the note to be posted before completing. An unfinished conversation after 1600 seconds fails the run; use a schedule for backlog scans or to finish work that outlasts an event run.

**Before selecting Event**, register a signed custom webhook source (for example `gitlab`) and configure GitLab **Issue events** on the project or parent group with its webhook URL and signing token. Follow the [signed webhook registration instructions](../gitlab-mr-reviewer/README.md#event-trigger-prerequisite-gitlab-190), selecting **Issue events** rather than **Merge request events** in GitLab (keep `event_key_expr: object_kind`). Both templates can use one source if the same GitLab webhook sends **Issue events** and **Merge request events**; otherwise use separate sources and signing tokens. Select the source listed in `eventSources`. GitLab 19.0+ and a publicly reachable webhook endpoint are required; older GitLab or private local deployments should use the scheduled trigger. Never substitute the plain-text `X-Gitlab-Token` secret for a signing token.

Connect GitLab in Settings > Integrations or save `GITLAB_TOKEN` with `api` scope and permission to read issues and post notes. MCP-only access is not supported by this REST-backed template. On Cloud the worker requires the automation KV store.

Issue content is untrusted. Give the delegated agent only the permissions it needs.
