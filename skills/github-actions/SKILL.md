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

## Creating and Testing Actions

<IMPORTANT>
When creating a GitHub Action from scratch or working with complex workflows:
1. **Initial deployment**: At least one version MUST be merged into the main branch before the action can be used
2. **After first merge**: You can test changes from other branches before merging by referencing the branch name in the workflow
3. **Debug step**: Add a debug step that prints non-secret parameters at the beginning of your action to facilitate troubleshooting
</IMPORTANT>

## Workflow File Structure

GitHub Actions workflows are defined in `.github/workflows/*.yml` files:

```yaml
name: My Workflow
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run a script
        run: echo "Hello World"
```

## Testing Custom Actions

### Initial Setup (First Deployment)

For a new custom action, you MUST merge it to main first:

```bash
# 1. Create your action in .github/actions/my-action/action.yml
# 2. Commit and push to a branch
git add .github/actions/my-action/action.yml
git commit -m "Add custom action"
git push origin feature-branch

# 3. Create and merge PR to main
# 4. Now the action can be used in workflows
```

### Testing Changes Before Merging

Once your action exists in main, test changes from feature branches:

```yaml
# In .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      # Test local action from current branch
      - uses: actions/checkout@v4
      - uses: ./.github/actions/my-action
      
      # Or test from specific branch
      - uses: owner/repo/.github/actions/my-action@feature-branch
```

### Add Debug Step for Troubleshooting

Always add a debug step when creating new actions or debugging complex issues:

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
          echo "Environment: ${{ github.event.deployment.environment }}"
          # Add any custom inputs or variables (DO NOT print secrets)
          echo "Input param: ${{ inputs.my-param }}"
      
      - name: Actual workflow steps
        run: echo "Now running actual logic"
```

## Types of GitHub Actions

### 1. Workflow Files (`.github/workflows/*.yml`)

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

### 2. Composite Actions (`.github/actions/*/action.yml`)

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

### 3. Reusable Workflows (`.github/workflows/*.yml` with `workflow_call`)

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

## Common Pitfalls and Non-Obvious Gotchas

### 1. Action Must Exist in Default Branch First

**Problem**: Referencing an action that doesn't exist in the default branch fails.

**Solution**: Merge action to main before using it in workflows from other branches.

### 2. Workflow Triggers and Permissions

**Problem**: Workflows triggered by `pull_request` from forks have limited permissions.

**Solution**: Use `pull_request_target` carefully (security risk) or separate workflows for forks:

```yaml
# Safe pattern for fork PRs
on:
  pull_request:
    # Limited permissions, safe for forks
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read  # Explicitly set minimal permissions
    steps:
      - uses: actions/checkout@v4
```

### 3. GITHUB_TOKEN Permissions

**Problem**: Default `GITHUB_TOKEN` may lack permissions for certain operations.

**Solution**: Explicitly declare permissions in workflow:

```yaml
permissions:
  contents: write      # Push to repository
  pull-requests: write # Comment on PRs
  issues: write        # Update issues
  packages: write      # Publish packages
```

### 4. Matrix Build Context Access

**Problem**: Matrix variables aren't accessible in job-level `if` conditions.

**Solution**: Use `strategy` context:

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

### 5. Secrets in Pull Requests from Forks

**Problem**: Secrets aren't available in workflows triggered by fork PRs (security feature).

**Solution**: Don't rely on secrets for fork PR validation, or use `pull_request_target` with extreme caution:

```yaml
# CAREFUL: pull_request_target runs in context of base repo
on:
  pull_request_target:
    # Only use for safe operations, never run untrusted code
```

### 6. Workflow File Changes Don't Trigger Themselves

**Problem**: Pushing workflow file changes doesn't trigger the workflow on that push.

**Solution**: The workflow runs on the next trigger event, not when the workflow file is added/modified.

### 7. Path Filters Are OR'd, Not AND'd

**Problem**: Multiple paths in path filters match ANY, not ALL.

```yaml
# This triggers if EITHER path matches
on:
  push:
    paths:
      - 'src/**'
      - 'tests/**'
```

### 8. Action Versions and References

**Problem**: Using `@main` for action versions can break if the action changes.

**Solution**: Pin to specific versions or SHA for stability:

```yaml
# Recommended: Pin to version
- uses: actions/checkout@v4

# Or pin to specific SHA for immutability
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

# Avoid: Using @main in production
- uses: actions/checkout@main  # Can break without warning
```

### 9. Environment Variables vs Inputs

**Problem**: Confusion between workflow-level env vars and action inputs.

**Solution**: Know the scopes:

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

### 10. Artifact Upload/Download Between Jobs

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

### Using gh CLI in Workflows

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
```

## Viewing Workflow Runs

Use GitHub CLI or API to check workflow status:

```bash
# List recent workflow runs
gh run list --limit 10

# View specific run details
gh run view <run-id>

# Watch run in progress
gh run watch

# Download logs
gh run view <run-id> --log > workflow.log

# Check status of PR checks
gh pr checks <pr-number>
```

## Best Practices

1. **Pin action versions**: Use specific versions (`@v4`) or SHA hashes, not `@main`
2. **Minimal permissions**: Explicitly set `permissions` to minimum required
3. **Debug steps**: Add parameter printing for new/complex actions
4. **Fail fast**: Use `fail-fast: false` in matrix builds only when needed
5. **Secrets handling**: Never print secrets; they're masked but can be exposed via encoding
6. **Caching**: Use `actions/cache` for dependencies to speed up workflows
7. **Concurrency control**: Use `concurrency` to cancel redundant workflow runs
8. **Timeout limits**: Set `timeout-minutes` to prevent hung jobs

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10  # Prevent jobs from hanging
    concurrency:
      group: ${{ github.workflow }}-${{ github.ref }}
      cancel-in-progress: true  # Cancel old runs when new ones start
```

## Common Workflow Patterns

### PR Validation

```yaml
name: PR Validation
on:
  pull_request:
    branches: [ main ]

jobs:
  validate:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: npm test
      - name: Comment results
        uses: actions/github-script@v7
        if: failure()
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '❌ Tests failed!'
            })
```

### Conditional Steps

```yaml
steps:
  - name: Only on main branch
    if: github.ref == 'refs/heads/main'
    run: echo "Main branch"
  
  - name: Only on success
    if: success()
    run: echo "Previous steps succeeded"
  
  - name: Only on failure
    if: failure()
    run: echo "Something failed"
  
  - name: Always run (even on failure)
    if: always()
    run: echo "Cleanup"
```

### Environment Deployments

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - name: Deploy
        run: ./deploy.sh
```

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax Reference](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)
- [act - Local Testing Tool](https://github.com/nektos/act)
