---
name: fix-ci-pipelines
description: Diagnose and fix CI/CD pipeline failures including GitHub Actions, GitLab CI, Jenkins, and other CI systems. Analyzes build logs, identifies root causes, and implements fixes to get pipelines green again.
triggers:
- /fix-ci
- /fix-pipeline
---

# Fix CI Pipelines

Diagnose and resolve CI/CD pipeline failures to restore healthy builds and deployments.

## Process

1. **Identify the failure**: Fetch CI logs and identify the failing job, step, and error message
2. **Analyze root cause**: Determine if it's a code issue, dependency problem, flaky test, configuration error, or infrastructure issue
3. **Implement fix**: Apply the appropriate fix based on the root cause
4. **Verify**: Ensure the fix resolves the issue without breaking other jobs

## Common CI Failure Patterns

### Dependency Issues
- Version conflicts or missing dependencies
- Lock file out of sync with manifest
- Private registry authentication failures

### Test Failures
- Flaky tests with race conditions
- Environment-specific failures
- Missing test fixtures or data

### Build Failures
- Compilation errors
- Type checking failures
- Asset bundling issues

### Configuration Issues
- Invalid YAML syntax
- Missing secrets or environment variables
- Incorrect job dependencies or ordering

### Infrastructure Issues
- Resource limits (memory, disk, time)
- Network connectivity problems
- Docker image availability

## Output

Provide:
1. Root cause analysis of the failure
2. Specific fix with code changes
3. Explanation of why the fix works
4. Recommendations to prevent similar failures
