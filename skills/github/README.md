# Github

Interact with GitHub repositories, pull requests, issues, and workflows using the GITHUB_TOKEN environment variable and GitHub CLI. Use when working with code hosted on GitHub or managing GitHub resources.

## Triggers

This skill is activated by the following keywords:

- `github`
- `git`

## Details

You can interact with GitHub using one of the following methods, in order of preference:

1. **OAuth MCP Server** (preferred): If authenticated GitHub MCP tools are available in the
   environment, use them for GitHub operations. MCP tools handle authentication via the
   configured OAuth integration, so no token is needed.
2. **Secret Token**: If a `GITHUB_TOKEN` environment variable is set, use it with the GitHub
   API and GitHub CLI (`gh`), as described below.
3. **No authentication**: If neither is available, ask the user to either:
   - Connect a GitHub OAuth MCP server in Canvas, OR
   - Provide a `GITHUB_TOKEN` as a Secret

Detection is based on the availability of authenticated GitHub MCP tools - no specific
MCP server name or tool name is required. When MCP tools are available, prefer them;
the token/REST and `gh` flows below remain the correct path when MCP is unavailable or
when you explicitly need raw API/curl or CLI access.

If `GITHUB_TOKEN` may be set but you are unsure, check it before relying on the token path:

```bash
[ -n "$GITHUB_TOKEN" ] && echo "GITHUB_TOKEN is set" || echo "GITHUB_TOKEN is NOT set"
```

<IMPORTANT>
You can use `curl` with the `GITHUB_TOKEN` to interact with GitHub's API.
ALWAYS use the GitHub API for operations instead of a web browser.
ALWAYS use the `create_pr` tool to open a pull request
If the user asks you to check GitHub Actions status, first try to use `gh` to work with workflows, and only fallback to basic API calls if that fails.
Examples:
- `gh run watch` (https://cli.github.com/manual/gh_run_watch) to monitor workflow runs
- `gh pr checks 200 --watch --interval 10` to check until completed.
</IMPORTANT>

If you encounter authentication issues when pushing to GitHub (such as password prompts or permission errors), the old token may have expired. In such case, update the remote URL to include the current token: `git remote set-url origin https://${GITHUB_TOKEN}@github.com/username/repo.git`

Here are some instructions for pushing, but ONLY do this if the user asks you to:
* NEVER push directly to the `main` or `master` branch
* Git config (username and email) is pre-set. Do not modify.
* You may already be on a branch starting with `openhands-workspace`. Create a new branch with a better name before pushing.
* Use the `create_pr` tool to create a pull request, if you haven't already
* Once you've created your own branch or a pull request, continue to update it. Do NOT create a new one unless you are explicitly asked to. Update the PR title and description as necessary, but don't change the branch name.
* Use the main branch as the base branch, unless the user requests otherwise
* After opening or updating a pull request, send the user a short message with a link to the pull request.
* Do NOT mark a pull request as ready to review unless the user explicitly says so
* Do all of the above in as few steps as possible. E.g. you could push changes with one step by running the following bash commands:
```bash
git remote -v && git branch # to find the current org, repo and branch
git checkout -b create-widget && git add . && git commit -m "Create widget" && git push -u origin create-widget
```