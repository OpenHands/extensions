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
3. Add debug steps for new actions or when troubleshooting tricky issues

### Types of Actions

#### 1. Workflow Files (`.github/workflows/*.yml`)

Standard CI/CD workflows that run on repository events:

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
```

#### 2. Composite Actions (`.github/actions/*/action.yml`)

Reusable actions within the same repository:

```yaml
# .github/actions/setup-env/action.yml
name: Setup Environment
description: Setup project dependencies
inputs:
  node-version:
    description: Node.js version
    required: false
    default: '18'
runs:
  using: composite
  steps:
    - uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
    - run: npm install
      shell: bash
```

#### 3. Reusable Workflows (`.github/workflows/*.yml` with `workflow_call`)

Workflows that can be called from other workflows:

```yaml
# .github/workflows/reusable-deploy.yml
name: Reusable Deploy
on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying to ${{ inputs.environment }}"
```

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

**Problem**: Workflows triggered by PRs from forks can't access secrets (security feature).

**Solution**: Don't rely on secrets for fork PR validation, or use `pull_request_target` with extreme caution:

```yaml
# CAREFUL: pull_request_target runs in context of base repo
on:
  pull_request_target:
    # Only use for safe operations, never run untrusted code
```

### 3. Using Unstable Action References

**Problem**: Using `@main` or `@master` for action versions can break unexpectedly.

**Solution**: Pin to specific versions (`@v4`) or SHA hashes for stability:

```yaml
# Recommended: Pin to version
- uses: actions/checkout@v4

# Or pin to specific SHA for immutability
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

# Avoid: Using @main in production
- uses: actions/checkout@main  # Can break without warning
```

### 4. Missing GITHUB_TOKEN Permissions

**Problem**: Default `GITHUB_TOKEN` may lack permissions for certain operations like commenting on PRs.

**Solution**: Explicitly declare required permissions in workflow:

```yaml
permissions:
  contents: write      # Push to repository
  pull-requests: write # Comment on PRs
  issues: write        # Update issues
  packages: write      # Publish packages
```

### 5. Not Printing Debug Information

**Problem**: Complex or new workflows fail without enough context to debug.

**Solution**: When creating new actions or troubleshooting tricky issues, add a debug step that prints non-secret parameters:

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      # Debug step - prints all non-secret inputs/variables
      - name: Debug - Print context
        run: |
          echo "Event name: ${{ github.event_name }}"
          echo "Ref: ${{ github.ref }}"
          echo "SHA: ${{ github.sha }}"
          echo "Actor: ${{ github.actor }}"
          echo "Runner OS: ${{ runner.os }}"
          echo "Working directory: $(pwd)"
          # Add any custom inputs or variables (DO NOT print secrets)
          echo "Input param: ${{ inputs.my-param }}"
      
      - name: Actual workflow steps
        run: echo "Now running actual logic"
```

### 6. Workflow File Changes Don't Trigger Themselves

**Problem**: Pushing workflow file changes doesn't trigger the workflow on that push.

**Solution**: The workflow runs on the next trigger event after the workflow file is merged, not when the workflow file itself is added/modified.

### 7. Path Filters Are OR'd, Not AND'd

**Problem**: Multiple paths in path filters match ANY, not ALL.

```yaml
# This triggers if EITHER path matches (OR logic)
on:
  push:
    paths:
      - 'src/**'
      - 'tests/**'
```

### 8. Matrix Build Context Access

**Problem**: Matrix variables aren't accessible in job-level `if` conditions.

**Solution**: Use `strategy` context properly:

```yaml
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - name: Linux-specific step
        if: ${{ matrix.os == 'ubuntu-latest' }}
        run: echo "Linux only"
```

### 9. Environment Variables vs Inputs

**Problem**: Confusion between workflow-level env vars and action inputs.

**Solution**: Understand the scopes:

```yaml
env:
  # Available to all jobs in workflow
  GLOBAL_VAR: value

jobs:
  build:
    env:
      # Available to all steps in job
      JOB_VAR: value
    steps:
      - name: Step with env
        env:
          # Only available to this step
          STEP_VAR: value
        run: echo "$STEP_VAR"
```

### 10. Artifacts Don't Persist Between Jobs

**Problem**: Files don't persist between jobs without explicit artifact handling.

**Solution**: Use artifacts to share data:

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "data" > output.txt
      - uses: actions/upload-artifact@v4
        with:
          name: my-artifact
          path: output.txt
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: my-artifact
      - run: cat output.txt
```

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

## Local Testing with act

Test workflows locally before pushing:

```bash
# Install act
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run workflows locally
act                          # Run default event (push)
act pull_request             # Simulate pull_request event
act -l                       # List available workflows
act -j test                  # Run specific job

# Use with secrets
act --secret GITHUB_TOKEN=xxx

# Use specific event payload
act -e event.json
```

**Note**: `act` doesn't perfectly replicate GitHub Actions environment but catches most issues.

## Debugging Failed Workflows

### Enable Debug Logging

Add repository secrets for verbose logging:
- `ACTIONS_STEP_DEBUG`: true (step-level debug)
- `ACTIONS_RUNNER_DEBUG`: true (runner-level debug)

Or add to workflow:

```yaml
jobs:
  debug:
    runs-on: ubuntu-latest
    steps:
      - name: Enable debug
        run: |
          echo "ACTIONS_STEP_DEBUG=true" >> $GITHUB_ENV
          echo "ACTIONS_RUNNER_DEBUG=true" >> $GITHUB_ENV
      
      - name: Debug step
        run: echo "::debug::This is a debug message"
```

### Common Debug Commands

```yaml
- name: Debug - Show all environment
  run: env | sort

- name: Debug - Show GitHub context
  run: echo '${{ toJSON(github) }}'

- name: Debug - Show runner context  
  run: echo '${{ toJSON(runner) }}'

- name: Debug - Check file structure
  run: ls -laR

- name: Debug - Print secrets (masked)
  run: |
    # Secrets are automatically masked in output
    echo "Token length: ${#GITHUB_TOKEN}"
    echo "Token (masked): $GITHUB_TOKEN"
```

### Using gh CLI for Workflow Management

Monitor and interact with workflows using GitHub CLI:

```bash
# Check workflow runs
gh run list --workflow=ci.yml

# Watch a specific run
gh run watch <run-id>

# Re-run failed jobs
gh run rerun <run-id> --failed

# View logs
gh run view <run-id> --log

# Check workflow status from PR
gh pr checks <pr-number> --watch

# List recent workflow runs
gh run list --limit 10

# Download logs
gh run view <run-id> --log > workflow.log
```

## Best Practices

1. **Pin action versions**: Use specific versions (`@v4`) or SHA hashes, not `@main`
2. **Minimal permissions**: Explicitly set `permissions` to minimum required
3. **Debug steps**: Add debug output when creating new actions or troubleshooting tricky issues (not required for every workflow)
4. **Fail fast**: Use `fail-fast: false` in matrix builds only when needed
5. **Secrets handling**: Never print secrets; they're masked but can be exposed via encoding
6. **Caching**: Use `actions/cache` for dependencies to speed up workflows
7. **Concurrency control**: Use `concurrency` to cancel redundant workflow runs
8. **Timeout limits**: Set `timeout-minutes` to prevent hung jobs

### Example Best Practice Implementation

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10  # Prevent jobs from hanging
    concurrency:
      group: ${{ github.workflow }}-${{ github.ref }}
      cancel-in-progress: true  # Cancel old runs when new ones start
    permissions:
      contents: read  # Minimal permissions
    steps:
      - uses: actions/checkout@v4  # Pinned version
      
      - name: Cache dependencies
        uses: actions/cache@v4
        with:
          path: ~/.npm
          key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
      
      - run: npm ci
      - run: npm test
```

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax Reference](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Security Hardening Guide](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [act - Local Testing](https://github.com/nektos/act)
- [Awesome Actions](https://github.com/sdras/awesome-actions)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)

## Related Skills

- **github** - General GitHub operations, PR management, and API usage
- **github-pr-review** - Posting structured PR reviews
- **docker** - Working with Docker in GitHub Actions workflows
