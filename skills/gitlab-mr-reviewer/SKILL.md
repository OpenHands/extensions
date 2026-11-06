---
name: gitlab-mr-reviewer
description: This skill should be used when the user asks to "review GitLab merge requests automatically" or "set up GitLab MR code review".
triggers:
  - /gitlab-mr-reviewer:setup
---

# GitLab merge request review

Choose **GitLab merge request review** in Automations > Templates. Select GitLab projects, a review label, the GitLab API root, and a polling schedule. Connect a GitLab account under Settings > Integrations or add `GITLAB_TOKEN` with `api` scope and permission to read merge requests and post notes. MCP-only access is not supported by this REST-backed template.

The bundled worker polls open, non-draft labelled merge requests. It delegates a bounded diff to a conversation, then publishes one note per head SHA. A new head can receive a new review. The worker never approves or merges. Limit the delegated agent's permissions because merge request text is untrusted.

The worker source is `scripts/main.py`; the shared implementation is `scripts/common.py`. The Cloud runtime requires the automation KV store. Do not use a webhook on a local deployment; this template polls on a schedule.
