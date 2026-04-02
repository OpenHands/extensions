"""
QA Changes Prompt Template

This module contains the prompt template used by the OpenHands agent
for conducting pull request QA validation. The template uses the
/qa-changes skill trigger.

The template includes:
- {diff} - The complete git diff for the PR (may be truncated)
- {pr_number} - The PR number
- {commit_id} - The HEAD commit SHA
- {repo_name} - Repository name (owner/repo)
"""

PROMPT = """/qa-changes

QA the PR changes below. Set up the environment, run the test suite, exercise
the changed behavior, and post a structured QA report as a PR comment.

## Pull Request Information

- **Title**: {title}
- **Description**: {body}
- **Repository**: {repo_name}
- **Base Branch**: {base_branch}
- **Head Branch**: {head_branch}
- **PR Number**: {pr_number}
- **Commit ID**: {commit_id}

## Git Diff

```diff
{diff}
```

Follow the /qa-changes methodology: understand the change, set up the
environment, run tests, exercise changed behavior, and report results.

Post your QA report as a PR comment using the GitHub API
(`gh pr comment {pr_number} --body "..."`).

Important:
- Run the ACTUAL code. Do not just read the diff and speculate.
- Include exact commands and their output as evidence.
- If setup fails, report the failure and stop.
- End with a clear verdict: PASS, PASS WITH ISSUES, or FAIL.
"""


def format_prompt(
    title: str,
    body: str,
    repo_name: str,
    base_branch: str,
    head_branch: str,
    pr_number: str,
    commit_id: str,
    diff: str,
) -> str:
    """Format the QA prompt with all parameters.

    Args:
        title: PR title
        body: PR description
        repo_name: Repository name (owner/repo)
        base_branch: Base branch name
        head_branch: Head branch name
        pr_number: PR number
        commit_id: HEAD commit SHA
        diff: Git diff content

    Returns:
        Formatted prompt string
    """
    return PROMPT.format(
        title=title,
        body=body,
        repo_name=repo_name,
        base_branch=base_branch,
        head_branch=head_branch,
        pr_number=pr_number,
        commit_id=commit_id,
        diff=diff,
    )
