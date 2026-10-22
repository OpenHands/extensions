# Azure Devops

Interact with Azure DevOps repositories, pull requests, and APIs using the AZURE_DEVOPS_TOKEN environment variable. Use when working with code hosted on Azure DevOps or managing Azure DevOps resources.

## Triggers

This skill is activated by the following keywords:

- `azure_devops`
- `azure`

## Details

Use authenticated Azure DevOps MCP tools first when they are available in the agent's environment. Detect the connection through tool availability rather than a particular server name. Fall back to the documented `AZURE_DEVOPS_TOKEN` and direct API flow when those tools are unavailable or raw API or `curl` access is explicitly needed.

You have access to an environment variable, `AZURE_DEVOPS_TOKEN`, which allows you to interact with
the Azure DevOps API.

<IMPORTANT>
You can use `curl` with the `AZURE_DEVOPS_TOKEN` to interact with Azure DevOps's API.
ALWAYS use the Azure DevOps API for operations instead of a web browser.
</IMPORTANT>

### Git

Use plain `git clone`, `git fetch`, `git pull` and `git push`. OpenHands sets up git credentials for each Azure DevOps organization the user belongs to, so these commands work for any repository in those organizations, not only the one that was opened. Run them with `GIT_TERMINAL_PROMPT=0` so git fails at once instead of waiting at a username or password prompt.

A repository written as `ORG/PROJECT/REPO` is cloned from `https://dev.azure.com/ORG/PROJECT/_git/REPO`:

```bash
GIT_TERMINAL_PROMPT=0 git clone https://dev.azure.com/ORG/PROJECT/_git/REPO
```

Do not put `AZURE_DEVOPS_TOKEN` in a remote URL or pass it to git as an option: a token saved in `.git/config` stays on disk and stops working when it expires. If git fails because it needs a username or password, credentials are not set up for that organization; tell the user instead of embedding the token.

Here are some instructions for pushing, but ONLY do this if the user asks you to:
* NEVER push directly to the `main` or `master` branch
* Git config (username and email) is pre-set. Do not modify.
* You may already be on a branch starting with `openhands-workspace`. Create a new branch with a better name before pushing.
* Once you've created your own branch or a pull request, continue to update it. Do NOT create a new one unless you are explicitly asked to. Update the PR title and description as necessary, but don't change the branch name.
* Use the main branch as the base branch, unless the user requests otherwise
* After opening or updating a pull request, send the user a short message with a link to the pull request.
* Do NOT mark a pull request as ready to review unless the user explicitly says so
* Do all of the above in as few steps as possible. E.g. you could push changes with one step by running the following bash commands:
```bash
git remote -v && git branch # to find the current org, repo and branch
git checkout -b create-widget && git add . && git commit -m "Create widget" && GIT_TERMINAL_PROMPT=0 git push -u origin create-widget
```

## Azure DevOps API Usage

`AZURE_DEVOPS_TOKEN` is either a Personal Access Token (PAT) or, for users who sign in with Microsoft Entra ID, an Entra access token. Basic authentication works with both: leave the username empty and use the token as the password. An Entra access token can also be sent as `Authorization: Bearer $AZURE_DEVOPS_TOKEN`.

Here's how to authenticate with curl:
```bash
# Base64-encode ":<token>" on one line (Entra tokens are long enough to wrap)
AUTH=$(echo -n ":$AZURE_DEVOPS_TOKEN" | base64 | tr -d '\n')

# Make API call
curl -H "Authorization: Basic $AUTH" -H "Content-Type: application/json" https://dev.azure.com/{organization}/{project}/_apis/git/repositories?api-version=7.1
```

Common API endpoints:
- List repositories: `https://dev.azure.com/{organization}/{project}/_apis/git/repositories?api-version=7.1`
- Get repository details: `https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repositoryId}?api-version=7.1`
- List pull requests: `https://dev.azure.com/{organization}/{project}/_apis/git/pullrequests?api-version=7.1`
- Create pull request: `https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repositoryId}/pullrequests?api-version=7.1` (POST)
