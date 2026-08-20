# Integration Validation

Add integrations only after core login, LLM, and conversation checks pass. Validate each integration independently. A working callback URL does not prove account linking, repository access, event routing, or provider-side permissions.

Never print provider tokens, app secrets, signing secrets, private keys, or complete webhook bodies containing customer data.

## GitHub

Use a GitHub App rather than a GitHub OAuth App. Validate separate paths:

1. user sign-in;
2. GitHub App installation on an approved test repository;
3. repository search for the signed-in user;
4. one bounded repository-backed conversation;
5. webhook or automation delivery when it is in scope.

Useful bounded checks:

```bash
curl -sS -H "Authorization: Bearer $OPENHANDS_API_KEY" \
  "$APP_URL/api/v1/users/me"

curl -sS -H "Authorization: Bearer $OPENHANDS_API_KEY" \
  "$APP_URL/api/v1/git/repositories/search?provider=github&query=<owner>/<repo>&limit=5"
```

Do not enable shell tracing while using API keys. If repository search reports an invalid GitHub token, refresh the user's GitHub authorization rather than extracting credentials from the cluster.

## GitLab, Bitbucket, and Azure DevOps

Follow the version-matched OpenHands Enterprise guide for the chosen provider. Validate login or account linking, repository discovery, one bounded repository operation, and any required callback or webhook. Use a disposable test repository when possible.

## Jira

The current VM documentation provides a supported Jira Data Center integration. Validate:

- Admin Console configuration exists for the supported Jira deployment type;
- account linking or service-account access works as configured;
- the Jira webhook reaches the documented OpenHands endpoint;
- one disposable test issue event produces the expected bounded result.

Treat custom Jira-to-Automations webhooks as a separate automation design, not a generic installation requirement. Do not copy customer-specific shim URLs, project keys, cloud IDs, tokens, or one-off routing patches into this skill.

## Slack

Validate both setup layers:

1. Admin Console credentials and Slack request URL verification;
2. OpenHands-side `Install Slack` workspace and user linking.

Then invite the bot to a test channel and send one bounded mention. If Slack delivers the event but no conversation starts, verify workspace/user linking before changing webhook configuration.

## Analytics (Laminar)

For the bundled analytics option, validate:

- `https://analytics.<base-domain>` loads;
- Keycloak login works;
- a project exists;
- an ingest-only project API key is configured through the Admin Console;
- a fresh conversation creates a trace.

Use Laminar for trace-level observability. Use OpenHands application storage for durable conversation metadata and product state.

## Automations

When Automations is enabled, create or dispatch one bounded test using the supported UI or API. Verify the event, run, and conversation identifiers without logging secrets or full customer payloads. Delete disposable triggers and credentials after testing when required by policy.
