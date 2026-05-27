---
name: github-actions
description: Create, debug, and test GitHub Actions workflows and custom actions. Use when building CI/CD pipelines, automating workflows, or troubleshooting GitHub Actions.
triggers:
- github actions
- workflow
- ci/cd
- github workflow
---

# GitHub Actions Guide

## Critical Rules

**Custom Action Deployment:**
- New custom actions MUST be merged to the main branch before they can be used
- After the initial merge, they should be tested from feature branches

**Debug Steps:**
Add debug steps that print non-secret parameters when:
- Creating a new action, OR
- Troubleshooting a particularly tricky issue

(Not required for every workflow - use when needed)

## Effectiveness Principles

Actions cost CI minutes. Be deliberate, not iterative:

1. **Monitor, don't poll** - use `gh run watch` / `gh pr checks --watch` to follow runs live
2. **Read logs, don't guess** - fetch the failed job's log before changing code
3. **Print actual values** - debug steps reveal the real `inputs`/`github` context, not your assumptions
4. **Test locally first** - `act` runs workflows on your machine and avoids burning CI minutes
5. **Plan the smallest reproduction** - one job, minimal matrix, narrow trigger before scaling up

See [README.md](README.md) for the full debugging workflow, `gh` commands, and YAML debug-step examples.

## Key Gotchas

1. **Secrets unavailable in fork PRs** - Use `pull_request_target` with caution or don't rely on secrets
2. **Pin action versions** - Use `@v4` or SHA, not `@main` (prevents breaking changes)
3. **Explicit permissions** - Set `permissions:` block for GITHUB_TOKEN operations
4. **Artifacts for job-to-job data** - Files don't persist between jobs without `upload-artifact`/`download-artifact`
