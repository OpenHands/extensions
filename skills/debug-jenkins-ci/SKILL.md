---
name: debug-jenkins-ci
description: Debug Jenkins CI/CD pipeline failures by fetching logs, identifying root causes, and suggesting fixes.
triggers:
- /debug-jenkins-ci
- jenkins ci failed
- jenkins build failed
- jenkins pipeline failed
- ci failure jenkins
---

# Debug Jenkins CI Failure

Diagnose and fix Jenkins pipeline failures by fetching logs, analyzing errors, and providing actionable fixes.

## Prerequisites

Set the following environment variables:

```bash
export JENKINS_URL="https://jenkins.example.com"
export JENKINS_USER="your-username"
export JENKINS_API_TOKEN="your-api-token"
```

## Quick Start

```bash
# Get recent builds for a job
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/job/{job_name}/api/json?tree=builds[number,result,timestamp]"

# Get console output for a failed build
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/job/{job_name}/{build_number}/consoleText"
```

## Step-by-Step Debugging Workflow

### 1. Identify the Failed Build

```bash
# List recent builds with status
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/job/{job_name}/api/json?tree=builds[number,result,timestamp,duration]" | jq '.builds[:5]'

# Get last failed build number
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/job/{job_name}/lastFailedBuild/api/json" | jq '.number'

# For multibranch pipelines
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/job/{pipeline_name}/job/{branch_name}/api/json?tree=builds[number,result]"
```

### 2. Fetch Failure Details

```bash
# Get full console output
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/job/{job_name}/{build_number}/consoleText"

# Get console output with timestamps
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/job/{job_name}/{build_number}/timestamps/?elapsed=HH:mm:ss&appendLog"

# For Pipeline jobs - get stage logs
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/job/{job_name}/{build_number}/wfapi/describe" | jq '.stages'
```

### 3. Analyze the Error

Common Jenkins failure patterns:

| Pattern | Likely Cause |
|---------|--------------|
| `ERROR: script returned exit code 1` | Script/command failure |
| `java.io.IOException` | Agent connectivity or disk issues |
| `No such DSL method` | Missing Jenkins plugin or typo in Jenkinsfile |
| `Timeout exceeded` | Build took too long - optimize or increase timeout |
| `CredentialsNotFoundException` | Missing or misconfigured credentials |
| `WorkspaceNotAllocated` | Agent workspace issues |
| `UNSTABLE` | Tests passed but with warnings/flaky tests |
| `RejectedAccessException` | Script security sandbox violation |

### 4. Pipeline-Specific Debugging

#### Get Failed Stage Information
```bash
# List all stages with status
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/job/{job_name}/{build_number}/wfapi/describe" | \
  jq '.stages[] | {name: .name, status: .status, durationMillis: .durationMillis}'

# Get logs for a specific stage
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/job/{job_name}/{build_number}/execution/node/{node_id}/wfapi/log"
```

#### Common Pipeline Fixes
```groovy
// Add timeout to prevent hung builds
timeout(time: 30, unit: 'MINUTES') {
    sh 'npm test'
}

// Retry flaky steps
retry(3) {
    sh 'npm install'
}

// Handle credentials properly
withCredentials([string(credentialsId: 'my-secret', variable: 'SECRET')]) {
    sh 'echo "Using secret"'
}
```

### 5. Rerun and Verify

```bash
# Trigger a new build
curl -X POST -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/job/{job_name}/build"

# Trigger with parameters
curl -X POST -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/job/{job_name}/buildWithParameters?PARAM1=value1"

# Replay a Pipeline build (with modified script)
# Use the UI: $JENKINS_URL/job/{job_name}/{build_number}/replay
```

## Jenkinsfile Debugging

```groovy
// Add debug output
pipeline {
    agent any
    options {
        timestamps()  // Add timestamps to console
    }
    stages {
        stage('Debug') {
            steps {
                sh 'env | sort'  // Print all environment variables
                sh 'pwd && ls -la'  // Show workspace contents
            }
        }
    }
}
```

### Validate Jenkinsfile Syntax
```bash
# Using Jenkins CLI
java -jar jenkins-cli.jar -s $JENKINS_URL declarative-linter < Jenkinsfile

# Or via API
curl -X POST -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  -F "jenkinsfile=<Jenkinsfile" \
  "$JENKINS_URL/pipeline-model-converter/validate"
```

## Advanced: Blue Ocean API

For Pipeline visualization data:

```bash
# Get pipeline runs
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/blue/rest/organizations/jenkins/pipelines/{job_name}/runs/"

# Get specific run details
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/blue/rest/organizations/jenkins/pipelines/{job_name}/runs/{run_number}/"

# Get nodes (stages) in a run
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/blue/rest/organizations/jenkins/pipelines/{job_name}/runs/{run_number}/nodes/"
```

## Agent/Node Issues

```bash
# List all nodes
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/computer/api/json" | jq '.computer[] | {name: .displayName, offline: .offline}'

# Check specific node status
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/computer/{node_name}/api/json"

# Get node's executors
curl -s -u "$JENKINS_USER:$JENKINS_API_TOKEN" \
  "$JENKINS_URL/computer/{node_name}/api/json?tree=executors[currentExecutable[url]]"
```

## Debugging Checklist

1. ✅ **Fetch console output**: Get the full build log
2. ✅ **Identify failing stage**: For pipelines, find which stage failed first
3. ✅ **Check error message**: Read the actual error, not just "FAILURE"
4. ✅ **Verify agent status**: Is the build agent online and healthy?
5. ✅ **Check credentials**: Are all required credentials configured?
6. ✅ **Review Jenkinsfile**: Is the syntax valid? Any recent changes?
7. ✅ **Check plugins**: Are required plugins installed and up-to-date?
8. ✅ **Reproduce locally**: Can you run the same commands locally?

## Summary

1. Use the Jenkins API to fetch build status: `/job/{name}/lastFailedBuild/api/json`
2. Get console output: `/job/{name}/{build}/consoleText`
3. For pipelines, get stage details: `/job/{name}/{build}/wfapi/describe`
4. Identify the root cause from error messages
5. Fix the issue (Jenkinsfile, credentials, or code)
6. Trigger a new build: `POST /job/{name}/build`
