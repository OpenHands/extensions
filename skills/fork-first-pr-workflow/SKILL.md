---
name: fork-first-pr-workflow
description: This skill should be used when the user asks to "use my fork", "create a branch", "push my changes", "open a PR", "draft a PR to upstream", or when upstream repository permissions are missing or unclear. It guides a safe fork-first GitHub contribution workflow that prefers pushing to a personal fork and opening a pull request back to upstream.
triggers:
- use my fork
- draft a PR to upstream
- fork first
---

# Fork-First PR Workflow

## Objective
Contribute through a personal fork when upstream branch creation or pushes are unavailable, undesirable, or uncertain.

## When to Apply
Apply this workflow when any of the following is true:

- The user explicitly asks to work from a fork.
- The repository is hosted on GitHub and upstream write access is unknown.
- Direct branch creation on the upstream repository fails.
- The user wants a PR from a fork to upstream.
- The user prefers a predictable contributor workflow instead of relying on upstream push permissions.

## Core Workflow

1. Inspect the repository state before making GitHub changes.
2. Identify the upstream repository, default branch, current branch, and configured remotes.
3. Treat upstream write access as unknown until it is confirmed.
4. Prefer pushing to a fork remote when one exists and the user has not explicitly requested an upstream branch.
5. If no fork remote exists, look up the authenticated GitHub user and check whether a fork already exists.
6. If a fork exists, add it as a remote and push there.
7. If no fork exists and the user asked to push or open a PR, create the fork or ask for confirmation when the request is ambiguous.
8. Create a feature branch locally if the current branch is unsuitable.
9. Push the branch to the fork remote.
10. Open a pull request from the fork branch to the upstream base branch.
11. Reuse the same PR and branch for follow-up commits unless the user explicitly asks for a new branch.

## Remote Selection Rules

- Run `git remote -v` before choosing a push target.
- Distinguish the fork remote from the upstream remote explicitly.
- If `origin` points to upstream and a fork remote exists, push to the fork remote by name.
- If `origin` already points to the fork, keep `upstream` configured separately for fetches and PR targeting.
- Do not fail the workflow merely because upstream rejects branch creation or push access.
- Do not assume the remote named `origin` is always the correct push target.

## Branching Rules

- Never push directly to `main` or `master`.
- Create a descriptive feature branch before pushing.
- Check `git status --short` before switching branches or committing.
- Stop and ask the user if unrelated uncommitted changes are present.
- Keep later fixes on the same branch when updating an existing PR.

## Pull Request Rules

- Prefer the GitHub API or `gh` CLI over browser-based GitHub flows.
- Target the upstream repository's default branch unless the user requests another base branch.
- Use a draft PR when the user explicitly asks for a draft.
- After opening the PR, report the PR link and summarize the source branch, head repository, and base branch.
- When posting a PR title or description for humans, include a short AI disclosure note required by the environment policy.

## Approval and Merge Follow-up

- After approval, check mergeability and actor permissions before attempting to merge.
- If merge permissions are missing, leave a concise maintainer-facing follow-up comment instead of looping on auto-merge.
- Avoid repeated branch-update or auto-merge retries when the blocker is repository permissions.
- If the PR needs a base-branch update, confirm with the user before performing a rebase or merge that could affect review state.

## Useful Commands

### Inspect remotes and branch state

```bash
git remote -v
git branch --show-current
git status --short
```

### Identify the authenticated GitHub user

```bash
export GH_TOKEN="$GITHUB_TOKEN"
gh api user --jq .login
```

### Check whether a fork already exists

```bash
export GH_TOKEN="$GITHUB_TOKEN"
gh api repos/<login>/<repo> --jq '{full_name: .full_name, parent: .parent.full_name}'
```

### Add a fork remote

```bash
git remote add fork https://github.com/<login>/<repo>.git
```

### Push the current branch to the fork explicitly

```bash
git push -u fork HEAD
```

### Create a PR from fork to upstream

```bash
export GH_TOKEN="$GITHUB_TOKEN"
gh pr create \
  --repo <upstream-owner>/<repo> \
  --head <fork-owner>:<branch> \
  --base <base-branch> \
  --title "<title>" \
  --body-file <body-file>
```

## Output Expectations

Provide a short final update that includes:

- which remote was treated as upstream
- which remote was used for pushing
- the created or reused branch name
- whether the PR is draft or ready for review
- the PR link or the blocker that prevented opening it

## Failure Handling

- If GitHub authentication fails, refresh the token-backed remote or re-run the GitHub command with `GH_TOKEN` exported.
- If no fork is available and the user did not clearly authorize creating one, stop and ask.
- If upstream PR creation fails because the head branch is missing, verify the push target and branch name before retrying.
- If permissions block merging after approval, report the blocker and prepare a maintainer handoff message.
