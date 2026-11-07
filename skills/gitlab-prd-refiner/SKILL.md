---
name: gitlab-prd-refiner
description: This skill should be used when the user asks to "refine GitLab work items", "write PRD feedback on GitLab issues", or "set up GitLab requirements refinement".
triggers:
  - /gitlab-prd-refiner:setup
---

# GitLab work item refinement

Choose **GitLab work item refiner** in Automations > Templates. Select GitLab projects, a refinement label, the GitLab API root, and a polling schedule. Connect a GitLab account under Settings > Integrations or add `GITLAB_TOKEN` with `api` scope and permission to read issues and post notes. MCP-only access is not supported by this REST-backed template.

The bundled worker polls GitLab issue-type work items. It reads the issue description and human discussion once per label application, delegates refinement to a conversation, and publishes one note with open questions, recommendations, and gaps. Remove and reapply the label to ask for a new refinement. It does not inspect linked repositories, modify issue fields, or create merge requests. Limit the delegated agent's permissions because issue text is untrusted.

The worker source is `scripts/main.py`; its shared implementation is shipped from the GitLab MR reviewer skill. The Cloud runtime requires the automation KV store. Do not use a webhook on a local deployment; this template polls on a schedule.
