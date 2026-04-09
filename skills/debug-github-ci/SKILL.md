---
name: debug-github-ci
description: Debug GitHub Actions CI failures by fetching logs, identifying root causes, and suggesting fixes.
triggers:
- /debug-github-ci
- github ci failed
- github actions failed
- workflow failed
- ci failure github
---

# Debug GitHub CI Failure

Diagnose and fix GitHub Actions workflow failures by fetching logs, analyzing errors, and providing actionable fixes.

## Quick Start

```bash
# Get recent failed workflow runs
gh run list --status failure --limit 5

# View logs for a specific run
gh run view <run_id> --log-failed

# Rerun failed jobs
gh run rerun <run_id> --failed
```

## Step-by-Step Debugging Workflow

### 1. Identify the Failed Run

```bash
# List recent workflow runs with status
gh run list --limit 10

# Filter by workflow name
gh run list --workflow "CI" --status failure --limit 5

# Get run ID from a PR's checks
gh pr checks <pr_number>
```

### 2. Fetch Failure Details

```bash
# View run summary (shows failed jobs)
gh run view <run_id>

# Download full logs
gh run view <run_id> --log-failed

# For verbose logs (all jobs, not just failed)
gh run view <run_id> --log
```

### 3. Analyze the Error

Common failure patterns to look for:

| Pattern | Likely Cause |
|---------|--------------|
| `exit code 1` in test step | Test failure - check test output |
| `ENOENT` / `file not found` | Missing dependency or build artifact |
| `permission denied` | Incorrect file permissions or missing secrets |
| `rate limit exceeded` | API throttling - add retry logic or caching |
| `out of memory` | Increase runner memory or optimize build |
| `timeout` | Increase timeout or optimize slow steps |
| `secret not found` | Missing or misspelled secret name |

### 4. Common Fixes

#### Test Failures
```bash
# Run tests locally first
npm test  # or pytest, cargo test, etc.

# Check if tests pass with verbose output
npm test -- --verbose
```

#### Dependency Issues
```bash
# Clear caches and reinstall
rm -rf node_modules package-lock.json
npm install

# For Python
pip install --upgrade -r requirements.txt
```

#### Environment Differences
```yaml
# Pin versions in workflow
- uses: actions/setup-node@v4
  with:
    node-version: '20.x'  # Be specific
```

### 5. Rerun and Verify

```bash
# Rerun only failed jobs (faster)
gh run rerun <run_id> --failed

# Rerun entire workflow
gh run rerun <run_id>

# Watch the run in real-time
gh run watch <run_id>
```

## API Fallback (curl)

If `gh` CLI is unavailable:

```bash
# List workflow runs
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/{owner}/{repo}/actions/runs?status=failure"

# Get run details
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}"

# Download logs (returns redirect URL)
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/logs"
```

## Workflow File Debugging

```bash
# Validate workflow syntax
gh workflow view <workflow_name>

# Check workflow file location
ls -la .github/workflows/

# Common workflow issues:
# - Incorrect indentation (YAML is whitespace-sensitive)
# - Missing 'on:' trigger
# - Invalid action version (use @v4 not @latest)
```

## Advanced: Matrix Build Failures

```bash
# View specific matrix combination
gh run view <run_id> --job <job_id>

# List all jobs in a run
gh api repos/{owner}/{repo}/actions/runs/{run_id}/jobs
```

## Debugging Checklist

1. ✅ **Fetch logs**: `gh run view <run_id> --log-failed`
2. ✅ **Identify failing step**: Look for the first red ❌ in output
3. ✅ **Check error message**: Read the actual error, not just "failed"
4. ✅ **Reproduce locally**: Try to replicate the failure on your machine
5. ✅ **Check recent changes**: Did a recent commit introduce the failure?
6. ✅ **Verify secrets**: Ensure all required secrets are configured
7. ✅ **Check dependencies**: Are versions pinned and compatible?
8. ✅ **Review workflow file**: Is the YAML valid and logic correct?

## Summary

1. Use `gh run list --status failure` to find failed runs
2. Use `gh run view <run_id> --log-failed` to fetch logs
3. Identify the root cause from error messages
4. Fix the issue locally and verify
5. Push changes and use `gh run rerun <run_id> --failed` to verify the fix
