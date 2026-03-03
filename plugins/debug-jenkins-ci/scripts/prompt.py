"""
Jenkins CI Debug Prompt Template

This module contains the prompt template used by the OpenHands agent
for debugging Jenkins CI/CD pipeline failures.

The template includes:
- {job_name} - The Jenkins job name
- {build_number} - The build number
- {jenkins_url} - The Jenkins server URL
- {build_result} - The build result (FAILURE, UNSTABLE, etc.)
- {stages} - Pipeline stages information (if applicable)
- {logs} - The console output from the build
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

PROMPT = """/debug-jenkins-ci

Debug the Jenkins build failure below and identify the root cause.

## Build Information

- **Jenkins URL**: {jenkins_url}
- **Job**: {job_name}
- **Build Number**: {build_number}
- **Result**: {build_result}
- **Duration**: {duration}
- **Timestamp**: {timestamp}

## Pipeline Stages

{stages}

## Console Output

The following is the console output from the failed build. Analyze it to identify the root cause.

```
{logs}
```

## Your Task

1. **Analyze the console output** to identify the specific error(s) that caused the failure
2. **Determine the root cause** - is it a code issue, Jenkinsfile problem, dependency issue, or infrastructure problem?
3. **Provide actionable fixes** with specific Jenkinsfile changes or commands
4. **Consider common Jenkins issues**:
   - Script sandbox violations (RejectedAccessException)
   - Credential issues (CredentialsNotFoundException)
   - Agent/node problems
   - Timeout issues
   - Flaky tests

Provide clear, actionable guidance that helps developers fix the issue quickly.

If you need more context, you can use curl to query the Jenkins API:

```bash
# Get build details
curl -u "$JENKINS_USER:$JENKINS_API_TOKEN" "{jenkins_url}/job/{job_name}/{build_number}/api/json"

# Get pipeline stages (Blue Ocean API)
curl -u "$JENKINS_USER:$JENKINS_API_TOKEN" "{jenkins_url}/blue/rest/organizations/jenkins/pipelines/{job_name}/runs/{build_number}/nodes/"
```
"""

# Validation patterns for inputs used in API calls
BUILD_NUMBER_PATTERN = re.compile(r"^[0-9]+$")
JOB_NAME_PATTERN = re.compile(r"^[\w./-]+$")


class PromptValidationError(ValueError):
    """Raised when prompt inputs fail validation."""

    pass


def _validate_jenkins_url(jenkins_url: str) -> None:
    """Validate jenkins_url is a valid URL."""
    try:
        result = urlparse(jenkins_url)
        if not all([result.scheme, result.netloc]):
            raise PromptValidationError(
                f"Invalid jenkins_url: '{jenkins_url}'. Expected valid URL."
            )
    except Exception:
        raise PromptValidationError(
            f"Invalid jenkins_url: '{jenkins_url}'. Expected valid URL."
        )


def _validate_job_name(job_name: str) -> None:
    """Validate job_name contains only safe characters."""
    if not JOB_NAME_PATTERN.match(job_name):
        raise PromptValidationError(
            f"Invalid job_name: '{job_name}'. "
            "Expected alphanumeric characters, dots, hyphens, underscores, or slashes."
        )


def _validate_build_number(build_number: str) -> None:
    """Validate build_number is numeric."""
    if not BUILD_NUMBER_PATTERN.match(build_number):
        raise PromptValidationError(
            f"Invalid build_number: '{build_number}'. Expected numeric value."
        )


def format_prompt(
    jenkins_url: str,
    job_name: str,
    build_number: str,
    build_result: str,
    duration: str,
    timestamp: str,
    stages: str,
    logs: str,
) -> str:
    """Format the Jenkins debug prompt with all parameters.

    Args:
        jenkins_url: Jenkins server URL
        job_name: Name of the Jenkins job
        build_number: Build number (must be numeric)
        build_result: Build result (FAILURE, UNSTABLE, etc.)
        duration: Build duration
        timestamp: Build timestamp
        stages: Formatted pipeline stages info
        logs: Console output from the build

    Returns:
        Formatted prompt string

    Raises:
        PromptValidationError: If inputs fail validation.
    """
    # Validate inputs used in API calls
    _validate_jenkins_url(jenkins_url)
    _validate_job_name(job_name)
    _validate_build_number(build_number)

    return PROMPT.format(
        jenkins_url=jenkins_url,
        job_name=job_name,
        build_number=build_number,
        build_result=build_result,
        duration=duration,
        timestamp=timestamp,
        stages=stages,
        logs=logs,
    )
