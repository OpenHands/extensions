# GitHub Actions Skill

A comprehensive skill for creating, debugging, and testing GitHub Actions workflows and custom actions.

## Overview

This skill provides guidance for working with GitHub Actions, including:
- Creating and structuring workflows
- Building custom actions (composite and reusable)
- Testing actions locally and in CI
- Debugging failed workflows
- Avoiding common pitfalls
- Best practices and security considerations

## When to Use This Skill

Use this skill when:
- Creating new GitHub Actions workflows
- Building custom composite or reusable actions
- Debugging workflow failures
- Setting up CI/CD pipelines
- Troubleshooting permission or secret issues
- Testing actions before merging to main

## Key Concepts

### Action Testing Requirements

**Critical**: When creating a custom action from scratch:
1. The action **must** be merged to the main branch before it can be used
2. After the initial merge, you can test changes from feature branches
3. Always add debug steps for new or complex actions

### Types of Actions

1. **Workflows** (`.github/workflows/*.yml`) - Standard CI/CD pipelines
2. **Composite Actions** (`.github/actions/*/action.yml`) - Reusable actions within a repo
3. **Reusable Workflows** - Workflows that can be called from other workflows

## Common Scenarios

### Scenario 1: Creating a New Custom Action

```bash
# 1. Create the action locally
mkdir -p .github/actions/my-action
cat > .github/actions/my-action/action.yml << 'EOF'
name: My Action
description: Does something useful
inputs:
  param:
    description: A parameter
    required: true
runs:
  using: composite
  steps:
    - run: echo "Param: ${{ inputs.param }}"
      shell: bash
EOF

# 2. Create a workflow to test it
cat > .github/workflows/test-action.yml << 'EOF'
name: Test My Action
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/my-action
        with:
          param: test-value
EOF

# 3. Commit and merge to main FIRST
git add .github/actions/my-action .github/workflows/test-action.yml
git commit -m "Add custom action"
git push origin feature-branch
# Create and merge PR to main

# 4. Now you can test changes from other branches
```

### Scenario 2: Debugging a Failed Workflow

```yaml
name: Debug Workflow
on: [push]
jobs:
  debug:
    runs-on: ubuntu-latest
    steps:
      # Add debug step at the beginning
      - name: Debug - Print all contexts
        run: |
          echo "Event: ${{ github.event_name }}"
          echo "Ref: ${{ github.ref }}"
          echo "SHA: ${{ github.sha }}"
          echo "Actor: ${{ github.actor }}"
          echo "Working dir: $(pwd)"
          echo "Environment vars:"
          env | sort
      
      - uses: actions/checkout@v4
      
      - name: Debug - Check files
        run: ls -la
      
      # Your actual steps here
```

### Scenario 3: Testing Locally with act

```bash
# Install act
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Test the default push event
act

# Test a specific workflow
act -W .github/workflows/test.yml

# Test with secrets
act --secret GITHUB_TOKEN=$GITHUB_TOKEN

# List all jobs that would run
act -l

# Dry run (show what would execute)
act -n
```

### Scenario 4: Handling Permissions Issues

```yaml
name: PR Comment Workflow
on:
  pull_request:
    branches: [main]

jobs:
  comment:
    runs-on: ubuntu-latest
    # Explicitly grant permissions
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '✅ Validation passed!'
            })
```

## Common Pitfalls

### 1. Forgetting to Merge Action to Main First

**Problem**: Creating an action and trying to use it before merging to main.

**Solution**: Always merge the action to the default branch first, then test changes from feature branches.

### 2. Secrets Not Available in Fork PRs

**Problem**: Workflows triggered by PRs from forks can't access secrets.

**Solution**: Don't rely on secrets for fork PR validation, or use `pull_request_target` with caution (security risk).

### 3. Using Unstable Action References

**Problem**: Using `@main` or `@master` for action versions can break unexpectedly.

**Solution**: Pin to specific versions (`@v4`) or SHA hashes.

### 4. Missing Permissions

**Problem**: GITHUB_TOKEN doesn't have permissions for operations like commenting on PRs.

**Solution**: Explicitly declare required permissions in the workflow.

### 5. Not Printing Debug Information

**Problem**: Workflows fail without enough context to debug.

**Solution**: Add a debug step that prints non-secret parameters at the start of your action.

## Advanced Patterns

### Reusable Workflow with Matrix

```yaml
# .github/workflows/reusable-test.yml
name: Reusable Test
on:
  workflow_call:
    inputs:
      node-version:
        required: true
        type: string

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
      - run: npm test

# Caller workflow
# .github/workflows/ci.yml
name: CI
on: [push]
jobs:
  test:
    strategy:
      matrix:
        node-version: [16, 18, 20]
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: ${{ matrix.node-version }}
```

### Conditional Jobs Based on File Changes

```yaml
name: Smart CI
on: [push]

jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      backend: ${{ steps.filter.outputs.backend }}
      frontend: ${{ steps.filter.outputs.frontend }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v2
        id: filter
        with:
          filters: |
            backend:
              - 'backend/**'
            frontend:
              - 'frontend/**'
  
  test-backend:
    needs: changes
    if: needs.changes.outputs.backend == 'true'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Testing backend"
  
  test-frontend:
    needs: changes
    if: needs.changes.outputs.frontend == 'true'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Testing frontend"
```

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax Reference](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Security Hardening Guide](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [act - Local Testing](https://github.com/nektos/act)
- [Awesome Actions](https://github.com/sdras/awesome-actions)

## Related Skills

- **github** - General GitHub operations, PR management, and API usage
- **github-pr-review** - Posting structured PR reviews
- **docker** - Working with Docker in GitHub Actions workflows
