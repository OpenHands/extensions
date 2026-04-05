# fork-first-pr-workflow

Guide OpenHands through a safe GitHub contribution workflow that prefers a personal fork over direct upstream branch creation.

## Triggers

This skill is activated by requests such as:

- "use my fork"
- "create a branch"
- "push my changes"
- "open a PR"
- "draft a PR to upstream"
- direct-push failures caused by missing upstream permissions

## What it does

- inspects remotes before choosing a push target
- treats upstream write access as unknown until confirmed
- prefers pushing feature branches to a fork
- opens pull requests from fork to upstream
- avoids auto-merge or branch-update loops when the real blocker is permissions

## Notes

- Designed for reusable GitHub contribution workflows, not repository-specific rules.
- Works best alongside the existing `github` skill for GitHub CLI and API operations.
- Requires GitHub authentication for fork discovery, pushing, and pull request creation.
