# Git Provider Authentication

Select one provider for the first installation pass. Configure additional providers only after core login, LLM, and conversation checks pass.

## Approval and Secret Handling

Treat provider application creation and callback changes as external mutations. Before running a helper or creating an application:

1. identify the provider organization and approved test repository;
2. review requested scopes, callback URLs, webhook URLs, and events;
3. identify the provider administrator who approves the change;
4. explain created resources and cleanup steps;
5. obtain explicit approval;
6. transfer generated secrets through an approved secret channel.

Do not print client secrets, webhook secrets, user tokens, or private keys. Use least privilege and a disposable test repository where possible.

## GitHub

The current OpenHands Enterprise quick start links to the official `scripts/create_github_app` helper in the OpenHands Cloud repository.

Review the current helper before execution. Confirm the base URL and requested permissions match the target release, then obtain approval to run it. Configure the Admin Console with the generated:

- Client ID
- Client Secret
- App ID
- App Slug
- Webhook Secret
- Private Key

Use a GitHub App, not a GitHub OAuth App. Install the app only on approved repositories for the initial test.

Validate sign-in, repository discovery, one bounded repository-backed conversation, and one webhook event when Automations is in scope.

Official quick start: https://docs.openhands.dev/enterprise/quick-start

## GitLab

Configure the GitLab host and OAuth client values supported by the target OHE release. Keep `gitlab.com` for GitLab SaaS or use the customer-managed hostname.

Follow the current Admin Console and provider documentation rather than adapting the GitHub helper. Validate callback TLS, sign-in, repository discovery, and one bounded repository-backed conversation.

## Bitbucket Data Center

Use the current OpenHands Enterprise Bitbucket Data Center guide for application, bot identity, callback, and webhook requirements. Do not assume Bitbucket Cloud instructions apply.

Official guide: https://docs.openhands.dev/enterprise/integrations/bitbucket-data-center

## Azure DevOps

Use the current OpenHands Enterprise Azure DevOps guide for Microsoft Entra tenant, organization, client application, permissions, and callbacks. Validate the exact organization and a disposable repository before broadening access.

Official guide: https://docs.openhands.dev/enterprise/integrations/azure-devops

## Completion Record

Record only non-secret evidence:

```text
Provider:
Provider organization/host:
Application name and non-secret ID:
Approved repository scope:
Callback/webhook validation:
Sign-in result:
Repository discovery result:
Repository-backed conversation result:
Cleanup owner:
```
