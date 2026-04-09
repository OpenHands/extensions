"""
CI Debug Prompt Template

This module contains the prompt template used by the OpenHands agent
for debugging GitHub Actions CI failures.

The template includes:
- {run_id} - The workflow run ID
- {repo_name} - The repository name
- {workflow_name} - Name of the failed workflow
- {failed_jobs} - Summary of failed jobs
- {logs} - The relevant log output from failed jobs
"""

from __future__ import annotations

import re

PROMPT = """/debug-github-ci

Debug the CI failure below and identify the root cause.

## Workflow Run Information

- **Repository**: {repo_name}
- **Run ID**: {run_id}
- **Workflow**: {workflow_name}
- **Branch**: {branch}
- **Commit**: {commit_sha}
- **Triggered by**: {triggered_by}

## Failed Jobs

{failed_jobs}

## Error Logs

The following logs are from the failed jobs. Analyze them to identify the root cause.

```
{logs}
```

## Your Task

1. **Analyze the logs** to identify the specific error(s) that caused the failure
2. **Determine the root cause** - is it a code issue, dependency problem, configuration error, or flaky test?
3. **Provide actionable fixes** with specific commands or code changes
4. **Post a comment** on the associated PR (if any) or create an issue with your findings

Use the GitHub CLI (`gh`) to:
- Fetch additional context if needed: `gh run view {run_id} --log`
- Post comments: `gh pr comment` or `gh issue create`
- Check recent commits: `gh api repos/{repo_name}/commits`

Focus on providing clear, actionable guidance that helps developers fix the issue quickly.
"""

# Validation patterns for inputs that are used in shell commands or API URLs
RUN_ID_PATTERN = re.compile(r"^[0-9]+$")
REPO_NAME_PATTERN = re.compile(r"^[\w.-]+/[\w.-]+$")


class PromptValidationError(ValueError):
    """Raised when prompt inputs fail validation."""

    pass


def _validate_run_id(run_id: str) -> None:
    """Validate run_id is numeric (used in API calls)."""
    if not RUN_ID_PATTERN.match(run_id):
        raise PromptValidationError(
            f"Invalid run_id: '{run_id}'. Expected numeric workflow run ID."
        )


def _validate_repo_name(repo_name: str) -> None:
    """Validate repo_name matches owner/repo format (used in API calls)."""
    if not REPO_NAME_PATTERN.match(repo_name):
        raise PromptValidationError(
            f"Invalid repo_name: '{repo_name}'. Expected format: owner/repo"
        )


def format_prompt(
    run_id: str,
    repo_name: str,
    workflow_name: str,
    branch: str,
    commit_sha: str,
    triggered_by: str,
    failed_jobs: str,
    logs: str,
) -> str:
    """Format the CI debug prompt with all parameters.

    Args:
        run_id: The workflow run ID (must be numeric)
        repo_name: Repository name (owner/repo format)
        workflow_name: Name of the failed workflow
        branch: Branch the workflow ran on
        commit_sha: Commit SHA that triggered the workflow
        triggered_by: Event that triggered the workflow
        failed_jobs: Formatted summary of failed jobs
        logs: Log output from failed jobs

    Returns:
        Formatted prompt string

    Raises:
        PromptValidationError: If run_id or repo_name fail validation.
    """
    # Validate inputs used in API calls/shell commands
    _validate_run_id(run_id)
    _validate_repo_name(repo_name)

    return PROMPT.format(
        run_id=run_id,
        repo_name=repo_name,
        workflow_name=workflow_name,
        branch=branch,
        commit_sha=commit_sha,
        triggered_by=triggered_by,
        failed_jobs=failed_jobs,
        logs=logs,
    )
