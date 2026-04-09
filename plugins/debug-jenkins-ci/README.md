# Debug Jenkins CI Plugin

Automated debugging of Jenkins CI/CD pipeline failures using OpenHands agents. This plugin provides scripts and configuration that can diagnose and suggest fixes when Jenkins builds fail.

## Quick Start

Set up your Jenkins environment:

```bash
export JENKINS_URL="https://jenkins.example.com"
export JENKINS_USER="your-username"
export JENKINS_API_TOKEN="your-api-token"
```

Then run the debug script when a build fails.

## Features

- **Automatic Build Failure Analysis**: Triggered when Jenkins builds fail
- **Console Log Analysis**: Fetches and analyzes build console output
- **Pipeline Stage Debugging**: For Pipeline jobs, identifies which stage failed
- **Actionable Suggestions**: Provides specific fixes and Jenkinsfile changes
- **Error Pattern Recognition**: Identifies common Jenkins failure patterns

## Plugin Contents

```
plugins/debug-jenkins-ci/
├── README.md              # This file
├── skills/                # Symbolic links to debug skills
│   └── debug-jenkins-ci -> ../../../skills/debug-jenkins-ci
└── scripts/               # Python scripts for debug execution
    ├── agent_script.py    # Main Jenkins debug agent script
    └── prompt.py          # Prompt template for debugging
```

Notes:
- The marketplace manifest uses the repo-wide `pluginRoot: "./skills"`, so `source: "./debug-jenkins-ci"` resolves to `skills/debug-jenkins-ci`.
- The `plugins/debug-jenkins-ci/skills/debug-jenkins-ci` symlink mirrors the `pr-review` plugin pattern so the plugin bundle can reference the matching skill content without duplicating `SKILL.md`.

## Installation

### 1. Configure Jenkins Credentials

You'll need a Jenkins API token:

1. Log in to Jenkins
2. Click your username → Configure
3. Add new API Token
4. Save the token securely

### 2. Set Environment Variables

```bash
export JENKINS_URL="https://jenkins.example.com"
export JENKINS_USER="your-username"
export JENKINS_API_TOKEN="your-api-token"
export LLM_API_KEY="your-llm-api-key"
```

### 3. Run the Debug Script

```bash
# Debug a specific build
python scripts/agent_script.py --job "my-job" --build 123

# Debug the last failed build
python scripts/agent_script.py --job "my-job" --last-failed
```

## Integration Options

### Option 1: Post-Build Action

Add to your Jenkinsfile:

```groovy
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'make build'
            }
        }
    }
    post {
        failure {
            script {
                // Trigger OpenHands debug analysis
                sh '''
                    curl -X POST "$OPENHANDS_WEBHOOK_URL" \
                        -H "Content-Type: application/json" \
                        -d "{
                            \"job\": \"${JOB_NAME}\",
                            \"build\": \"${BUILD_NUMBER}\",
                            \"url\": \"${BUILD_URL}\"
                        }"
                '''
            }
        }
    }
}
```

### Option 2: Jenkins Shared Library

Create a shared library function:

```groovy
// vars/debugBuildFailure.groovy
def call(Map config = [:]) {
    def job = config.job ?: env.JOB_NAME
    def build = config.build ?: env.BUILD_NUMBER
    
    withCredentials([string(credentialsId: 'llm-api-key', variable: 'LLM_API_KEY')]) {
        sh """
            python /path/to/debug-jenkins-ci/scripts/agent_script.py \
                --job "${job}" \
                --build "${build}"
        """
    }
}
```

Use in your pipeline:

```groovy
post {
    failure {
        debugBuildFailure()
    }
}
```

### Option 3: Standalone Script

Run manually or via cron:

```bash
# Check for recent failures and debug them
python scripts/agent_script.py --job "my-pipeline" --last-failed
```

## Script Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--job` | Yes | Jenkins job name |
| `--build` | No | Specific build number to debug |
| `--last-failed` | No | Debug the last failed build |
| `--llm-model` | No | LLM model (default: claude-sonnet) |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JENKINS_URL` | Yes | Jenkins server URL |
| `JENKINS_USER` | Yes | Jenkins username |
| `JENKINS_API_TOKEN` | Yes | Jenkins API token |
| `LLM_API_KEY` | Yes | LLM API key |
| `LLM_MODEL` | No | LLM model to use |
| `LLM_BASE_URL` | No | Custom LLM endpoint |

## What Gets Analyzed

The agent analyzes:

1. **Console output**: Full build log
2. **Pipeline stages**: For Pipeline jobs, which stage failed
3. **Error messages**: Specific error patterns and stack traces
4. **Jenkinsfile**: Issues in the pipeline configuration
5. **Node status**: Agent/executor availability

## Output

The agent provides:

- **Root Cause Analysis**: What caused the failure
- **Suggested Fixes**: Specific Jenkinsfile changes or commands
- **Prevention Tips**: How to avoid similar failures
- **Related Documentation**: Links to relevant Jenkins docs

## Common Failure Patterns

The agent recognizes these patterns:

| Pattern | Example | Typical Fix |
|---------|---------|-------------|
| Script error | `ERROR: script returned exit code 1` | Check the failing command |
| Timeout | `Timeout exceeded` | Increase timeout or optimize |
| Credentials | `CredentialsNotFoundException` | Configure missing credentials |
| Agent offline | `java.io.IOException` | Check agent connectivity |
| Sandbox violation | `RejectedAccessException` | Approve script or use @NonCPS |

## Troubleshooting

### Authentication Failed

1. Verify `JENKINS_API_TOKEN` is valid (tokens expire)
2. Check `JENKINS_USER` has read access to the job
3. Ensure `JENKINS_URL` doesn't have trailing slash

### No Logs Found

1. Build may have been deleted (check retention policy)
2. User may not have permission to view console
3. Build may still be running

### Pipeline Stages Not Detected

1. Ensure it's a Pipeline job (not Freestyle)
2. Check if Blue Ocean plugin is installed
3. Verify the build completed (not aborted)

## Security

- Uses Jenkins API tokens (not passwords)
- Only reads build logs (no write operations)
- Does not execute any code from the failed build
- API tokens should be stored securely (use credentials binding)

## Contributing

See the main [extensions repository](https://github.com/OpenHands/extensions) for contribution guidelines.

## License

This plugin is part of the OpenHands extensions repository. See [LICENSE](../../LICENSE) for details.
