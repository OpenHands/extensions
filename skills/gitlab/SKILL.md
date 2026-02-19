---
name: gitlab
description: Interact with GitLab repositories, merge requests, issues, and pipelines using the GITLAB_TOKEN environment variable and GitLab CLI (glab). Use when working with code hosted on GitLab or managing GitLab resources. Any URL starting with https://gitlab.com is a GitLab artifact.
triggers:
- gitlab
- git
- https://gitlab.com
---

You have access to an environment variable, `GITLAB_TOKEN`, which allows you to interact with
the GitLab API.

<IMPORTANT>
Any URL starting with `https://gitlab.com` refers to a GitLab artifact (repository, merge request, issue, pipeline, etc.) and should be handled using the GitLab CLI (`glab`) or GitLab API.

You can use `curl` with the `GITLAB_TOKEN` to interact with GitLab's API.
ALWAYS use the GitLab API or `glab` CLI for operations instead of a web browser.
ALWAYS use the `create_mr` tool to open a merge request.

If the user asks you to check pipeline status, view issues, or manage merge requests, use `glab` CLI:
Examples:
- `glab mr view <mr-number> --comments` to view MR with comments
- `glab issue view <issue-number> --comments` to view an issue with comments
- `glab ci status` to check pipeline status
- `glab ci retry` to retry a failed pipeline
</IMPORTANT>

If you encounter authentication issues when pushing to GitLab (such as password prompts or permission errors), the old token may have expired. In such case, update the remote URL to include the current token: `git remote set-url origin https://oauth2:${GITLAB_TOKEN}@gitlab.com/username/repo.git`

Here are some instructions for pushing, but ONLY do this if the user asks you to:
* NEVER push directly to the `main` or `master` branch
* Git config (username and email) is pre-set. Do not modify.
* You may already be on a branch starting with `openhands-workspace`. Create a new branch with a better name before pushing.
* Use the `create_mr` tool to create a merge request, if you haven't already
* Once you've created your own branch or a merge request, continue to update it. Do NOT create a new one unless you are explicitly asked to. Update the MR title and description as necessary, but don't change the branch name.
* Use the main branch as the base branch, unless the user requests otherwise
* After opening or updating a merge request, send the user a short message with a link to the merge request.
* Do NOT mark a merge request as ready to merge unless the user explicitly says so
* Do all of the above in as few steps as possible. E.g. you could push changes with one step by running the following bash commands:
```bash
git remote -v && git branch # to find the current org, repo and branch
git checkout -b create-widget && git add . && git commit -m "Create widget" && git push -u origin create-widget
```

## Handling Review Comments

- Critically evaluate each review comment before acting on it. Not all feedback is worth implementing:
  - Does it fix a real bug or improve clarity significantly?
  - Does it align with the project's engineering principles (simplicity, maintainability)?
  - Is the suggested change proportional to the benefit, or does it add unnecessary complexity?
- It's acceptable to respectfully decline suggestions that add verbosity without clear benefit, over-engineer for hypothetical edge cases, or contradict the project's pragmatic approach.
- After addressing (or deciding not to address) inline review comments, mark the corresponding discussion threads as resolved.
- Before resolving a thread, leave a reply comment that either explains the reason for dismissing the feedback or references the specific commit (e.g., commit SHA) that addressed the issue.
- Prefer resolving threads only once fixes are pushed or a clear decision is documented.
- Use the GitLab API to reply to and resolve discussion threads (see below).

## Resolving Discussion Threads via API

To resolve discussion threads programmatically:

1. Get the discussion IDs for a merge request:
```bash
glab api projects/:id/merge_requests/:mr_iid/discussions
```

2. Reply to a discussion thread:
```bash
curl --request POST --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/:id/merge_requests/:mr_iid/discussions/:discussion_id/notes" \
  --data "body=Fixed in <COMMIT_SHA>"
```

3. Resolve a discussion thread:
```bash
curl --request PUT --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/:id/merge_requests/:mr_iid/discussions/:discussion_id" \
  --data "resolved=true"
```

4. Get failed pipeline and retry it:
```bash
# List recent pipelines to find the ID
glab pipeline list

# Retry the failed pipeline
glab ci retry <pipeline-id>
```