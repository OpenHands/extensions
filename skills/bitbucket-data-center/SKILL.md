---
name: bitbucket-data-center
description: Bitbucket Data Center (self-hosted Bitbucket Server) specifics — authenticate with BITBUCKET_DATA_CENTER_TOKEN, use the REST API 1.0, PROJECT/repo_slug repositories, scm/ git remotes, and the create_bitbucket_data_center_pr tool. Loaded on demand by the bitbucket skill once a Data Center environment is detected.
---

You are working with **Bitbucket Data Center** (self-hosted Bitbucket Server). You have
access to an environment variable, `BITBUCKET_DATA_CENTER_TOKEN`, which contains a basic
auth token in the format `username:your-token` that allows you to interact with the git
repository and the REST API.

> Environment variable names are case-sensitive. If `BITBUCKET_DATA_CENTER_TOKEN` is not
> present, use whichever case variant actually exists (for example
> `bitbucket_data_center_token`). Run `env | grep -i 'bitbucket_data_center'` to find it.

## Finding the host/domain

Because Bitbucket Data Center is self-hosted, there is no fixed domain like
`bitbucket.org`. The `{domain}` (host) used in REST API URLs and git remotes comes from the
**`BITBUCKET_DATA_CENTER_HOST`** environment variable. OpenHands' Bitbucket Data Center
integration reads this same variable to build its base URL (`https://{host}/rest/api/1.0`),
so use it as the source of truth. Resolve it before constructing any URL:

```bash
BITBUCKET_DATA_CENTER_HOST="$(env | grep -i '^bitbucket_data_center_host=' | head -n1 | cut -d= -f2-)"
echo "${BITBUCKET_DATA_CENTER_HOST:?BITBUCKET_DATA_CENTER_HOST is not set}"
```

In the examples below, substitute the value of `${BITBUCKET_DATA_CENTER_HOST}` wherever you
see `{domain}`. If `BITBUCKET_DATA_CENTER_HOST` is not set, ask the user for the host
before proceeding rather than guessing.

- REST API base URL: `https://${BITBUCKET_DATA_CENTER_HOST}/rest/api/1.0`
- Repository identifier format: `PROJECT/repo_slug` (project key, slash, repo slug)

You can use this token to interact with the Bitbucket Data Center REST API:
```bash
curl -u "${BITBUCKET_DATA_CENTER_TOKEN}" "https://${BITBUCKET_DATA_CENTER_HOST}/rest/api/1.0/..."
```

<IMPORTANT>
ALWAYS use the Bitbucket Data Center API for operations instead of a web browser.
ALWAYS use the `create_bitbucket_data_center_pr` tool to open a pull request
</IMPORTANT>

If you encounter authentication issues when pushing to Bitbucket Data Center (such as password prompts or permission errors), the old token may have expired. In such case, update the remote URL to include the current token: `git remote set-url origin https://${BITBUCKET_DATA_CENTER_TOKEN}@${BITBUCKET_DATA_CENTER_HOST}/scm/{project_lower}/{repo}.git`

The token is a `username:token` pair, so if the username or token contains characters that are reserved in URLs (such as `@`), split on the first `:` and URL-encode each part before embedding it in a remote:

```bash
BB_USER="${BITBUCKET_DATA_CENTER_TOKEN%%:*}" && \
BB_PASS="${BITBUCKET_DATA_CENTER_TOKEN#*:}" && \
ENCODED_USER=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$BB_USER") && \
ENCODED_PASS=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$BB_PASS") && \
git remote set-url origin "https://${ENCODED_USER}:${ENCODED_PASS}@${BITBUCKET_DATA_CENTER_HOST}/scm/{project_lower}/{repo}.git"
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
