---
name: bitbucket-data-center
description: Bitbucket Data Center (self-hosted Bitbucket Server) specifics — authenticate with BITBUCKET_DATA_CENTER_TOKEN, use the REST API 1.0, PROJECT/repo_slug repositories, scm/ git remotes, and the create_bitbucket_data_center_pr tool. Loaded on demand by the bitbucket skill once a Data Center environment is detected.
---

Use authenticated Bitbucket Data Center MCP tools first when they are available in the agent's environment. Detect this by tool availability, without depending on a particular MCP server name. Use the token and direct REST API instructions below only when those tools are unavailable or when raw API or `curl` access is explicitly needed.

You are working with **Bitbucket Data Center** (self-hosted Bitbucket Server). You have
access to an environment variable, `BITBUCKET_DATA_CENTER_TOKEN`, which holds your Bitbucket
Data Center credential in one of two forms:

- An access or OAuth token: the value has no colon, or starts with `x-token-auth:`.
- A `username:token` pair.

> Environment variable names are case-sensitive. If `BITBUCKET_DATA_CENTER_TOKEN` is not
> present, use whichever case variant actually exists (for example
> `bitbucket_data_center_token`). Run `env | grep -i 'bitbucket_data_center'` to find it.

- REST API base URL: `https://{domain}/rest/api/1.0`
- Repository identifier format: `PROJECT/repo_slug` (project key, slash, repo slug)

Use it with the Bitbucket Data Center REST API as follows:

- An access or OAuth token goes in a Bearer header, without any `x-token-auth:` prefix:
  ```bash
  curl -H "Authorization: Bearer ${BITBUCKET_DATA_CENTER_TOKEN#x-token-auth:}" https://{domain}/rest/api/1.0/...
  ```
- A `username:token` pair uses HTTP Basic auth:
  ```bash
  curl -u "${BITBUCKET_DATA_CENTER_TOKEN}" https://{domain}/rest/api/1.0/...
  ```

<IMPORTANT>
ALWAYS use the Bitbucket Data Center API for operations instead of a web browser.
ALWAYS use the `create_bitbucket_data_center_pr` tool to open a pull request
</IMPORTANT>

If you encounter authentication issues when pushing to Bitbucket Data Center (such as password prompts or permission errors), the token in the remote URL may have expired. Update the remote URL to include the current token:

- For a `username:token` pair: `git remote set-url origin https://${BITBUCKET_DATA_CENTER_TOKEN}@{domain}/scm/{project_lower}/{repo}.git`
- For an access or OAuth token, keep the username that is already in the remote URL and replace only the token. The git username these tokens need depends on the server, so don't choose one yourself. If the remote URL has no username, tell the user instead.
  ```bash
  GIT_USER=$(git remote get-url origin | sed -nE 's#^https://([^:@/]+):[^@]*@.*#\1#p') && \
  [ -n "$GIT_USER" ] && \
  NEW_TOKEN=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "${BITBUCKET_DATA_CENTER_TOKEN#x-token-auth:}") && \
  git remote set-url origin "https://${GIT_USER}:${NEW_TOKEN}@{domain}/scm/{project_lower}/{repo}.git"
  ```

If the username or token contains characters that are reserved in URLs (such as `@`), split the pair on the first `:` and URL-encode each part before embedding it in a remote:

```bash
BB_USER="${BITBUCKET_DATA_CENTER_TOKEN%%:*}" && \
BB_PASS="${BITBUCKET_DATA_CENTER_TOKEN#*:}" && \
ENCODED_USER=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$BB_USER") && \
ENCODED_PASS=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$BB_PASS") && \
git remote set-url origin "https://${ENCODED_USER}:${ENCODED_PASS}@{domain}/scm/{project_lower}/{repo}.git"
```

Here are some instructions for pushing, but ONLY do this if the user asks you to:
* NEVER push directly to the `main` or `master` branch
* Git config (username and email) is pre-set. Do not modify.
* You may already be on a branch starting with `openhands-workspace`. Create a new branch with a better name before pushing.
* Use the `create_bitbucket_data_center_pr` tool to create a pull request, if you haven't already
* Once you've created your own branch or a pull request, continue to update it. Do NOT create a new one unless you are explicitly asked to. Update the PR title and description as necessary, but don't change the branch name.
* Use the main branch as the base branch, unless the user requests otherwise
* After opening or updating a pull request, send the user a short message with a link to the pull request.
* Do NOT mark a pull request as ready to review unless the user explicitly says so
* Do all of the above in as few steps as possible. E.g. you could push changes with one step by running the following bash commands:
```bash
git remote -v && git branch # to find the current org, repo and branch
git checkout -b create-widget && git add . && git commit -m "Create widget" && git push -u origin create-widget
```
