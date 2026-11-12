# GitLab MR reviewer

A cron- or event-triggered automation that reviews labelled, open, non-draft GitLab merge requests and posts one actionable summary note per head commit. It never approves or merges requests. A new head can receive a new review. Failed reviews retry once, then post a failure note on the merge request; push a new head to request another review.

## Setup

Use **GitLab merge request review** in Automations > Templates, or run `/gitlab-mr-reviewer:setup`. Select projects, a review label (default `openhands-review`), the GitLab HTTPS API root (default `https://gitlab.com/api/v4`), and **Schedule** (default every 15 minutes) or **Event**. Event runs review only the MR that sent the webhook, after rechecking its project, state, label and head against GitLab. The event worker waits for the review and note to finish before completing its run; an unfinished review after 1600 seconds fails the run, so a manual retry or new MR event is needed. Use a schedule instead when webhook delivery is unavailable, or to sweep backlog and retry reviews that outlast an event run.

Connect GitLab in Settings > Integrations or save `GITLAB_TOKEN` with `api` scope and permission to read merge requests and post notes. MCP-only access is not supported by this REST-backed template. On Cloud the worker requires the automation KV store; allow `GITLAB_TOKEN` (saved secret) or `gitlab_token` (connected integration) in the selected agent profile so its separate conversation sandbox can fetch private repositories.

### Event trigger prerequisite (GitLab 19.0+)

The automations backend does not yet include a built-in GitLab event source. **Before selecting Event**, register a signed custom webhook source in your OpenHands organization and set up GitLab's **merge request events** webhook on the project (or parent group). The automation service's webhook URL must be reachable from your GitLab instance; a private `localhost` service cannot receive external events. If your GitLab version does not offer a **signing token** (GitLab 19.0+, enabled by default; stable in 19.1), choose Schedule instead. GitLab's older **secret token** / `X-Gitlab-Token` is not an HMAC signature and must not be used as a substitute.

In GitLab's project **Settings → Webhooks**, generate a signing token and copy it securely. Register the source using the OpenHands automation API (use your own host and authentication header; do not paste the token into a chat):

```bash
read -rsp 'GitLab signing token: ' GITLAB_SIGNING_TOKEN; echo
export GITLAB_SIGNING_TOKEN
jq -n '{name:"GitLab MR events",source:"gitlab",event_key_expr:"object_kind",signature_header:"webhook-signature",signature_scheme:"standard_webhooks",event_id_header:"webhook-id",webhook_secret:env.GITLAB_SIGNING_TOKEN}' |
  curl -X POST "$OPENHANDS_HOST/api/automation/v1/webhooks" \
    -H "Authorization: Bearer $OPENHANDS_API_KEY" \
    -H 'Content-Type: application/json' --data-binary @-
unset GITLAB_SIGNING_TOKEN
```

For local Agent Canvas, use its **public ingress URL** as `OPENHANDS_HOST` and `-H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY"` instead of the bearer header. Copy the returned `webhook_url` into GitLab's webhook URL field, select **Merge request events**, and save it with the same signing token. To monitor multiple projects with one source, configure one signed **group webhook** on their parent group. Otherwise, create a separate source and reviewer automation per project, since separately generated project tokens cannot share a source's one verification key. Select Event and its registered source only after it appears in your organization's automation capabilities (`eventSources`). OpenHands validates the signature and deduplicates redeliveries by `webhook-id`; the reviewer also deduplicates by MR head SHA. Grant webhook and GitLab credentials only the permissions needed for reviews.

Each local review starts in an isolated snapshot of the MR's exact head (including fork source projects). On Cloud the agent fetches the MR ref and verifies the SHA itself. It can inspect surrounding code and run focused tests before reporting; if it cannot obtain the checkout, it retries rather than issuing a diff-only review. Local snapshots are removed once their conversations stop, not while they are still running.

Merge request content is untrusted. Give the delegated agent only the permissions it needs.
