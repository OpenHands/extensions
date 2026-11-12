---
name: gitlab-mr-reviewer
description: This skill should be used when the user asks to "review GitLab merge requests automatically" or "set up GitLab MR code review".
triggers:
  - /gitlab-mr-reviewer:setup
---

# GitLab merge request review

Choose **GitLab merge request review** in Automations > Templates. Select GitLab projects, a review label, the GitLab API root, and a schedule or event trigger. Connect a GitLab account under Settings > Integrations or add `GITLAB_TOKEN` with `api` scope and permission to read merge requests and post notes. MCP-only access is not supported by this REST-backed template.

Before selecting Event, ask the user to set up a GitLab **signing token** (GitLab 19.0+) and register a custom webhook source (for example `gitlab`) with `event_key_expr: object_kind`, `signature_header: webhook-signature`, `signature_scheme: standard_webhooks`, and `event_id_header: webhook-id`. Provide the request in [README.md](README.md); **do not register it or ask the user to share its token in chat**. They must configure Merge request events with the returned webhook URL and the same token on a project or parent group; separately generated project tokens require separate sources and automations. Verify the chosen source is in `eventSources` before offering the event trigger. A local deployment needs a publicly reachable ingress for webhooks; otherwise choose the schedule. Older GitLab instances without signing tokens should use polling rather than unsigned webhook delivery.

Scheduled runs scan open, non-draft labelled merge requests; event runs verify the webhook's project and MR against GitLab and wait until the targeted review has been posted. For local runs, the worker downloads the exact head's full repository tree (from the source project for fork MRs) into an isolated, credential-free workspace and starts the conversation there. Cloud conversations have separate sandboxes, so the agent must fetch the MR ref, verify its SHA, and work in that checkout; allow `GITLAB_TOKEN` in the chosen agent profile for private projects. The agent reads surrounding code and runs focused tests, using the bounded diff to identify changes. A failed checkout is not published as a review. When the conversation stops, the local workspace is removed. The worker publishes one note per head SHA; a new head can receive a new review. It never approves or merges. Limit the delegated agent's permissions because merge request text is untrusted.

The worker source is `scripts/main.py`; the shared implementation is `scripts/common.py`. The Cloud runtime requires the automation KV store.
