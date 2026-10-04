---
name: github
description: Interact with GitHub repositories, pull requests, issues, and workflows using the GITHUB_TOKEN environment variable and GitHub CLI. Use when working with code hosted on GitHub or managing GitHub resources.
triggers:
- github
---

## Connection selection

Use authenticated GitHub MCP tools first when they are available in the agent's environment. Detect this by tool availability, without depending on a particular MCP server name. Use the token and direct API instructions below only when GitHub MCP tools are unavailable or when raw API or `curl` access is explicitly needed.

You have access to an environment variable, `GITHUB_TOKEN`, which allows you to interact with
the GitHub API.

<IMPORTANT>
You can use `curl` with the `GITHUB_TOKEN` to interact with GitHub's API.
ALWAYS use the GitHub API for operations instead of a web browser.
ALWAYS use the `create_pr` tool to open a pull request
If the user asks you to check GitHub Actions status, first try to use `gh` to work with workflows, and only fallback to basic API calls if that fails.
Examples:
- `gh run watch` (https://cli.github.com/manual/gh_run_watch) to monitor workflow runs
- `gh pr checks 200 --watch --interval 10` to check until completed.
</IMPORTANT>

Windows PowerShell equivalents for the multi-line shell snippets below are in `references/windows.md`.

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

## Merging Pull Requests (async merge API)

IMPORTANT:
Only merge if the user asks you to, without ambiguity.

GitHub released an async merge API in October 2026; it is now the
recommended way to merge PRs programmatically, and the only merge API that supports stacked PRs. It can also add a PR to a merge queue.
Prefer it over `PUT .../pulls/{n}/merge` and the GraphQL `mergePullRequest` mutation.
A GitHub MCP merge tool may still use the older synchronous endpoint; for stacked PRs or merge queues, use the calls below.
Docs: https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request-asynchronously

1. Request the merge (`merge_action`: `default` uses the merge queue if the branch has one, else merges directly; or `direct_merge` / `merge_queue`). `merge_method`, `commit_title` and `commit_message` apply only to direct merges:
```bash
gh api -X PUT repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/merge-async -f merge_method=squash -f sha=<HEAD_SHA>
```
2. A `202` returns `details.uuid`; poll it every few seconds until `status` is no longer `pending`:
```bash
gh api repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/merge-async/<UUID>
```

Final `status` is `merged`, `enqueued` (added to the merge queue, NOT merged yet), or `failed` (see `details.message`).
A `200` on the PUT means the PR is already merged or queued; a `409` means a merge request is already pending (its UUID is returned).

## Handling Review Comments

- Critically evaluate each review comment before acting on it. Not all feedback is worth implementing:
  - Does it fix a real bug or improve clarity significantly?
  - Does it align with the project's engineering principles (simplicity, maintainability)?
  - Is the suggested change proportional to the benefit, or does it add unnecessary complexity?
- It's acceptable to respectfully decline suggestions that add verbosity without clear benefit, over-engineer for hypothetical edge cases, or contradict the project's pragmatic approach.
- After addressing (or deciding not to address) inline review comments, mark the corresponding review threads as resolved.
- Before resolving a thread, leave a reply comment that either explains the reason for dismissing the feedback or references the specific commit (e.g., commit SHA) that addressed the issue.
- Prefer resolving threads only once fixes are pushed or a clear decision is documented.
- Use the GitHub GraphQL API to reply to and resolve review threads (see below).
- After making changes to a PR, verify the title and description still match the content. Update them if the scope, features, or intent changed.

## Resolving Review Threads via GraphQL

To resolve existing review threads programmatically:

1. Get the thread IDs (replace `<OWNER>`, `<REPO>`, `<PR_NUMBER>`):
```bash
gh api graphql -f query='
{
  repository(owner: "<OWNER>", name: "<REPO>") {
    pullRequest(number: <PR_NUMBER>) {
      reviewThreads(first: 20) {
        nodes {
          id
          isResolved
          comments(first: 1) {
            nodes { body }
          }
        }
      }
    }
  }
}'
```

2. Reply to the thread explaining how the feedback was addressed:
```bash
gh api graphql -f query='
mutation {
  addPullRequestReviewThreadReply(input: {
    pullRequestReviewThreadId: "<THREAD_ID>"
    body: "Fixed in <COMMIT_SHA>"
  }) {
    comment { id }
  }
}'
```

3. Resolve the thread:
```bash
gh api graphql -f query='
mutation {
  resolveReviewThread(input: {threadId: "<THREAD_ID>"}) {
    thread { isResolved }
  }
}'
```

4. Get the failed workflow run ID and rerun it:
```bash
# Find the run ID from the failed check URL, or use:
gh run list --repo <OWNER>/<REPO> --branch <BRANCH> --limit 5

# Rerun failed jobs
gh run rerun <RUN_ID> --repo <OWNER>/<REPO> --failed
```
