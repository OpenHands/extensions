# Debug Jenkins CI

Debug Jenkins CI/CD pipeline failures by fetching logs, identifying root causes, and suggesting fixes.

## Triggers

This skill is activated by the following keywords:

- `/debug-jenkins-ci`
- `jenkins ci failed`
- `jenkins build failed`
- `jenkins pipeline failed`
- `ci failure jenkins`

## Overview

This skill provides a systematic approach to debugging Jenkins pipeline failures:

1. **Identify** the failed build using Jenkins API
2. **Fetch** console output and stage logs
3. **Analyze** error patterns to find root causes
4. **Fix** the underlying issue (Jenkinsfile, credentials, code)
5. **Verify** by triggering a new build

## Prerequisites

Set the following environment variables:

```bash
export JENKINS_URL="https://jenkins.example.com"
export JENKINS_USER="your-username"
export JENKINS_API_TOKEN="your-api-token"
```

To get an API token:
1. Log in to Jenkins
2. Click your username → Configure
3. Add new API Token

## Quick Example

```bash
# Get last failed build console output
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/job/{job_name}/lastFailedBuild/consoleText"
```

## Common Use Cases

- Pipeline script errors in Jenkinsfile
- Build failures due to dependency issues
- Agent/node connectivity problems
- Credential and permission issues
- Timeout failures in long-running jobs
- Flaky test failures with retry logic
