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

If the user asks you to check pipeline status, view issues, or manage merge requests, use `glab` CLI commands:
Examples:
- `glab mr view <mr-number>` to view a merge request
- `glab mr view <mr-number> --comments` to view MR with comments
- `glab issue view <issue-number> --comments` to view an issue with comments
- `glab ci status` to check pipeline status
- `glab ci view` to view the current pipeline
- `glab pipeline list` to list recent pipelines
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

## Common GitLab CLI (glab) Commands

### Merge Requests
```bash
# List merge requests
glab mr list

# View a specific MR with comments
glab mr view <mr-number> --comments

# Create a merge request
glab mr create --source-branch <branch> --target-branch main --title "Title" --description "Description"

# Check out an MR locally
glab mr checkout <mr-number>

# Approve a merge request
glab mr approve <mr-number>

# Merge a merge request
glab mr merge <mr-number>
```

### Issues
```bash
# List issues
glab issue list

# View an issue with comments
glab issue view <issue-number> --comments

# Create an issue
glab issue create --title "Title" --description "Description"

# Close an issue
glab issue close <issue-number>

# Add a comment to an issue
glab issue note <issue-number> --message "Comment text"
```

### Pipelines and CI
```bash
# View current pipeline status
glab ci status

# View pipeline details
glab ci view

# List recent pipelines
glab pipeline list

# Retry a failed pipeline
glab ci retry

# View a specific job's log
glab ci trace <job-id>
```

### API Access
```bash
# Make direct API calls using glab
glab api projects/:id/merge_requests

# Get project details
glab api projects/:id

# List project variables
glab api projects/:id/variables
```

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

4. Retry a failed pipeline:
```bash
# List recent pipelines to find the ID
glab pipeline list

# Retry the failed pipeline
glab ci retry <pipeline-id>
```