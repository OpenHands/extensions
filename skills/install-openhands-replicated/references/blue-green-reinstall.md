# Blue/Green Reinstall

Use this reference only after the operator explicitly approves a rebuild and cutover. Rebuilding, restoring, switching DNS, or changing provider callbacks can cause downtime, duplicate events, or data loss.

Prefer a version-matched OpenHands Support procedure when preserving application state across OHE versions. Use this reference when rebuilding an OpenHands Enterprise Replicated instance with minimal downtime or when stale state makes an in-place reinstall risky.

## Default Recommendation

Prefer blue/green over in-place wipe:

1. Keep the current instance running.
2. Provision a new VM or cluster with temporary hostnames.
3. Recreate configuration and app state intentionally.
4. Validate the new instance.
5. Cut DNS and provider webhooks over during a quiet window.
6. Keep the old instance as rollback until the new instance survives real use.

Use in-place reinstall only when downtime and rollback loss are acceptable.

## What To Preserve

Preserve as source material:

- redacted KOTS `ConfigValues`;
- Terraform inputs and outputs;
- DNS record inventory;
- TLS certificate coverage;
- org secret names, not values;
- LLM profile definitions;
- automation definitions;
- GitHub/Jira/Slack/Laminar integration settings;
- current backup status and restore expectations.

Preserve backups and snapshots, but do not restore old Postgres by default when
the goal is to remove stale state.

## Temporary Hostnames

Temporary hostnames let the new instance be validated without disrupting the old one. For a Simple-mode base domain like `openhands-next.example.com`, expect:

```text
admin.openhands-next.example.com
app.openhands-next.example.com
auth.openhands-next.example.com
analytics.openhands-next.example.com
llm-proxy.openhands-next.example.com
runtime-api.openhands-next.example.com
<id>-runtime.openhands-next.example.com
```

Keep a Legacy-mode source installation on its existing hostname layout unless hostname migration is part of the approved change.

Before final cutover, update the new instance's Replicated/KOTS hostname config
to the original domains, upload/provision certs for those domains, redeploy, and
then switch DNS.

## External Provider Constraints

Do not assume GitHub, Jira, or Slack can point to both old and new instances at
the same time.

Recommended approach:

- Use temporary provider apps/webhooks for pre-cutover testing when available.
- Otherwise keep production provider URLs on the old instance until cutover.
- Validate production provider routing immediately after DNS/webhook cutover.

GitHub has separate concerns:

- sign-in/OAuth callback;
- user provider token for repo search and repo-backed conversations;
- GitHub App webhook delivery into automations.

Jira and Slack also have separate delivery and user/workspace-linking states.

## Clean-State Rehydrate Order

1. Configure domain, TLS, LLM, sandbox lifecycle, and required app features.
2. Validate `/ready`, pods, statefulsets, and storage guard.
3. Sign in and create/claim the org.
4. Create a fresh org API key.
5. Import canonical org secrets.
6. Recreate LLM profiles with fresh LiteLLM proxy tokens.
7. Recreate automations.
8. Validate one manual conversation.
9. Validate integrations one at a time.
10. Configure and test backups.

## Cutover Checklist

Before cutover:

- final old-instance backup exists;
- old instance remains untouched for rollback;
- new instance passes core smoke tests;
- provider URL changes are known;
- DNS TTL is understood;
- original-domain TLS certs are ready.

During cutover:

1. Disable old automations if duplicate events are risky.
2. Set original hostnames in the new Replicated/KOTS config.
3. Deploy and verify new app readiness.
4. Switch DNS records.
5. Update GitHub/Jira/Slack callbacks/webhooks if needed.
6. Re-enable automations on the new instance.
7. Run login, API key, LLM, conversation, and integration smoke tests.

Rollback:

1. Switch DNS/webhooks back to the old instance.
2. Re-enable old automations.
3. Keep the failed new instance for analysis.

## Completion Criteria

A blue/green reinstall is complete only when:

- original app URL works on the new instance;
- protected API endpoint works with a new org key;
- at least one LLM-backed conversation completes;
- GitHub/Jira/Slack paths needed for demos are validated;
- Laminar traces are visible if analytics is enabled;
- backups are scheduled and at least one backup job succeeds;
- old instance rollback is no longer needed.
