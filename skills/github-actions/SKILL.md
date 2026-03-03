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
- After the initial merge, changes can be tested from feature branches

**Debug Steps:**
Add debug steps that print non-secret parameters when:
- Creating a new action, OR
- Troubleshooting a particularly tricky issue

(Not required for every workflow - use when needed)

## Testing & Monitoring Strategy

**Actions have costs** - Each workflow run consumes CI minutes. Plan efficiently:

1. **Test locally first** with `act` when possible
2. **Use debug steps early** - don't guess, read actual values
3. **Monitor actively** - use `gh run watch <run-id>` or `gh pr checks <pr-number> --watch`
4. **Read logs immediately** - `gh run view <run-id> --log` or view in GitHub UI
5. **Understand before changing** - examine what actually ran, not what you think ran

**Effective debugging workflow:**
```bash
# Watch workflow run in real-time
gh run watch

# Or monitor PR checks with auto-refresh
gh pr checks <pr-number> --watch --interval 10

# When failed, read full logs immediately
gh run view <run-id> --log

# Examine specific job logs
gh run view <run-id> --log --job=<job-id>
```

**Add visibility to your actions:**
```yaml
steps:
  # Print all non-secret inputs/context at start
  - name: Debug - Action inputs
    run: |
      echo "Event: ${{ github.event_name }}"
      echo "Ref: ${{ github.ref }}"
      echo "Actor: ${{ github.actor }}"
      echo "Working dir: $(pwd)"
      echo "Custom input: ${{ inputs.my-param }}"
  
  # Your action logic here
  
  # Verify outcome before finishing
  - name: Debug - Verify results
    run: |
      echo "Files created:"
      ls -la
      echo "Exit code: $?"
```

## Key Gotchas

1. **Secrets unavailable in fork PRs** - Use `pull_request_target` with caution or don't rely on secrets
2. **Pin action versions** - Use `@v4` or SHA, not `@main` (prevents breaking changes)
3. **Explicit permissions** - Set `permissions:` block for GITHUB_TOKEN operations
4. **Artifacts for job-to-job data** - Files don't persist between jobs without `upload-artifact`/`download-artifact`

## Detailed Information

See [README.md](README.md) for:
- Step-by-step examples and scenarios
- Complete list of common pitfalls
- Local testing with `act`
- Debugging techniques and `gh` CLI usage
- Advanced patterns and best practices
