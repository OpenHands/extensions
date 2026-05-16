# Bitbucket

Interact with Bitbucket repositories and pull requests using the BITBUCKET_TOKEN environment variable. Use when working with code hosted on Bitbucket or managing Bitbucket resources via API.

## Triggers

This skill is activated by the following keywords:

- `bitbucket`
- `git`

## Details

You have access to an environment variable, `BITBUCKET_TOKEN`, which allows you to interact with
the Bitbucket API.

<IMPORTANT>
You can use `curl` with the `BITBUCKET_TOKEN` to interact with Bitbucket's API.
ALWAYS use the Bitbucket API for operations instead of a web browser.
ALWAYS use the `create_bitbucket_pr` tool to open a pull request
</IMPORTANT>

Only rewrite the Bitbucket remote if a push actually fails with authentication errors and the user has asked you to push. Do not proactively rewrite `origin`. OpenHands commonly stores `BITBUCKET_TOKEN` in the same unencoded `user:token` form used by commands such as `curl --user "$BITBUCKET_TOKEN" ...`, so keep it in that form unless you truly need to embed it in a Git remote URL.

If you need a non-interactive HTTPS remote URL, split `BITBUCKET_TOKEN` on the first `:` and URL-encode each part before calling `git remote set-url`. This avoids breaking usernames or emails that contain reserved URL characters such as `@`:

```bash
BB_USER="${BITBUCKET_TOKEN%%:*}" && \
BB_PASS="${BITBUCKET_TOKEN#*:}" && \
ENCODED_USER=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$BB_USER") && \
ENCODED_PASS=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$BB_PASS") && \
git remote set-url origin "https://${ENCODED_USER}:${ENCODED_PASS}@bitbucket.org/username/repo.git"
```

Atlassian's Bitbucket Cloud docs recommend avoiding long-lived credentials in the remote URL when possible. Their API token examples use either `https://{bitbucket_username}:{api_token}@...` or `https://x-bitbucket-api-token-auth:{api_token}@...`; OpenHands users should only construct those URLs on demand, with proper URL encoding.

Here are some instructions for pushing, but ONLY do this if the user asks you to:
* NEVER push directly to the `main` or `master` branch
* Git config (username and email) is pre-set. Do not modify.
* You may already be on a branch starting with `openhands-workspace`. Create a new branch with a better name before pushing.
* Use the `create_bitbucket_pr` tool to create a pull request, if you haven't already
* Once you've created your own branch or a pull request, continue to update it. Do NOT create a new one unless you are explicitly asked to. Update the PR title and description as necessary, but don't change the branch name.
* Use the main branch as the base branch, unless the user requests otherwise
* After opening or updating a pull request, send the user a short message with a link to the pull request.
* Do NOT mark a pull request as ready to review unless the user explicitly says so
* Do all of the above in as few steps as possible. E.g. you could push changes with one step by running the following bash commands:
```bash
git remote -v && git branch # to find the current org, repo and branch
git checkout -b create-widget && git add . && git commit -m "Create widget" && git push -u origin create-widget
```