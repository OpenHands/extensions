---
name: gitlab-prd-refiner
description: This skill should be used when the user asks to "refine GitLab work items", "write PRD feedback on GitLab issues", or "set up GitLab requirements refinement".
triggers:
  - /gitlab-prd-refiner:setup
---

# GitLab work item refinement

Choose **GitLab work item refiner** in Automations > Templates. Select GitLab projects, a refinement label, the GitLab API root, and a schedule or event trigger. Connect a GitLab account under Settings > Integrations or add `GITLAB_TOKEN` with `api` scope and permission to read issues and post notes. MCP-only access is not supported by this REST-backed template.

Before selecting Event, ask the user to register a signed GitLab 19.0+ custom webhook source with `event_key_expr: object_kind`, `signature_header: webhook-signature`, `signature_scheme: standard_webhooks`, and `event_id_header: webhook-id`; provide the request in [the MR reviewer README](../gitlab-mr-reviewer/README.md#event-trigger-prerequisite-gitlab-190). Ask them to configure **Issue events** on a project or parent group using the returned URL and the same token. Do not register it or ask the user to share the signing token in chat. Check that its source appears in `eventSources`; if GitLab lacks signing tokens or the webhook endpoint is unreachable, offer the schedule instead.

Scheduled runs poll GitLab issue-type work items; event runs target the signed webhook's issue and wait until feedback is posted. The worker reads the issue description and human discussion once per label application, delegates refinement to a conversation, and publishes one note with open questions, recommendations, and gaps. Remove and reapply the label to ask for a new refinement. It does not inspect linked repositories, modify issue fields, or create merge requests. Limit the delegated agent's permissions because issue text is untrusted.

The worker source is `scripts/main.py`; its shared implementation is shipped from the GitLab MR reviewer skill. The Cloud runtime requires the automation KV store.
