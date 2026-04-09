# Debug GitHub CI

Debug GitHub Actions CI failures by fetching logs, identifying root causes, and suggesting fixes.

## Triggers

This skill is activated by the following keywords:

- `/debug-github-ci`
- `github ci failed`
- `github actions failed`
- `workflow failed`
- `ci failure github`

## Overview

This skill provides a systematic approach to debugging GitHub Actions workflow failures:

1. **Identify** the failed workflow run using `gh run list`
2. **Fetch** detailed logs with `gh run view --log-failed`
3. **Analyze** error patterns to find root causes
4. **Fix** the underlying issue
5. **Verify** with `gh run rerun --failed`

## Prerequisites

- `GITHUB_TOKEN` environment variable (automatically available)
- GitHub CLI (`gh`) installed (preferred) or `curl` as fallback

## Quick Example

```bash
# Find and debug the most recent CI failure
gh run list --status failure --limit 1
gh run view <run_id> --log-failed
```

## Common Use Cases

- Test failures in pull request checks
- Build failures due to dependency issues
- Deployment failures from missing secrets
- Timeout issues in long-running jobs
- Matrix build failures across different environments
