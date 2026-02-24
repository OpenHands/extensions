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

## Quick Patterns

**Basic Workflow:**
```yaml
# .github/workflows/ci.yml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
```

**Composite Action:**
```yaml
# .github/actions/setup/action.yml
name: Setup
runs:
  using: composite
  steps:
    - run: npm install
      shell: bash
```

**Reusable Workflow:**
```yaml
# .github/workflows/deploy.yml
on:
  workflow_call:
    inputs:
      env:
        required: true
        type: string
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploy to ${{ inputs.env }}"
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
