"""
PR Review Prompt Template

This module contains the prompt template used by the OpenHands agent
for conducting pull request reviews. The template uses skill triggers:
- {skill_trigger} will be replaced with '/codereview'
- /github-pr-review provides instructions for posting review comments via GitHub API

The template includes:
- {diff} - The complete git diff for the PR (may be truncated for large files)
- {pr_number} - The PR number
- {commit_id} - The HEAD commit SHA
- {review_context} - Previous review comments and thread resolution status

When sub-agent delegation is enabled (``use_sub_agents=True``), the agent
gets the TaskToolSet and decides at runtime whether to delegate based on
diff size and complexity.
"""

# Template for when there is review context available
_REVIEW_CONTEXT_SECTION = """
## Previous Review History

The following shows previous reviews and review threads on this PR.
Pay attention to:
- **Unresolved threads**: These issues may still need to be addressed
- **Resolved threads**: These provide context on what was already discussed
- **Previous review decisions**: See what other reviewers have said

{review_context}

When reviewing, consider:
1. Don't repeat comments that have already been made and are still relevant
2. If an issue is still unresolved in the code, you may reference it
3. If resolved, don't bring it up unless the fix introduced new problems
4. Focus on NEW issues in the current diff that haven't been discussed yet
"""

_EVIDENCE_REQUIREMENT_SECTION = """
## PR Description Evidence Requirement

Require the PR description to include an `Evidence` section (or similarly labeled section) showing that the code actually works.

When checking the PR description:
- For frontend or UI changes, require a screenshot or video that demonstrates the implemented behavior in the actual product.
- For backend, API, CLI, or script changes, require the command(s) used to run or exercise the real code path end-to-end and the resulting output.
- Unit tests alone do **not** count as evidence. Do not accept `pytest`, unit test output, or similar test runs as the only proof that the change works.
- If the change appears to come from an agent conversation or AI-assisted workflow, prefer a conversation link such as `https://app.all-hands.dev/conversations/{conversation_id}` so reviewers can trace the work.
- Do not accept vague claims like "tested locally" without concrete runtime artifacts, commands, or output.

If the change is substantive and this evidence is missing or weak, call it out as a must-fix issue in your review. Do not invent evidence that is not present in the PR description.
"""

PROMPT = """{skill_trigger}
/github-pr-review

When posting a review, keep the review body brief unless your active review instructions require a longer structured format.

Review the PR changes below and identify issues that need to be addressed.

## Pull Request Information

- **Title**: {title}
- **Description**: {body}
- **Repository**: {repo_name}
- **Base Branch**: {base_branch}
- **Head Branch**: {head_branch}
- **PR Number**: {pr_number}
- **Commit ID**: {commit_id}

{review_context_section}{evidence_requirements_section}

## Git Diff

```diff
{diff}
```

Analyze the changes and post your review using the GitHub API.
"""

# Prompt used when sub-agent delegation is enabled (use_sub_agents=True).
# The agent gets the TaskToolSet and decides at runtime whether to delegate
# based on diff size and complexity.
DELEGATION_PROMPT = """{skill_trigger}
/github-pr-review

When posting a review, keep the review body brief unless your active review instructions require a longer structured format.

Review the PR changes below and identify issues that need to be addressed.

## Pull Request Information

- **Title**: {title}
- **Description**: {body}
- **Repository**: {repo_name}
- **Base Branch**: {base_branch}
- **Head Branch**: {head_branch}
- **PR Number**: {pr_number}
- **Commit ID**: {commit_id}

{review_context_section}{evidence_requirements_section}

## Delegation Strategy

You have access to the **task** tool (TaskToolSet) for delegating file-level
reviews to `file_reviewer` sub-agents. **Decide whether to delegate based on
the diff below:**

- **Delegate** when the diff spans many files (roughly 4+) or is large
  (roughly 500+ changed lines). Split by file or small groups of related files
  and use `subagent_type: "file_reviewer"` for each chunk.
- **Review directly** when the diff is small or touches only a few files —
  delegation overhead is not worth it.

If you delegate:
1. Send each file/group to a sub-agent with the diff chunk and PR context.
2. Collect and merge findings, de-duplicate, drop noise.
3. Post a single consolidated review via the GitHub API.

If you review directly:
- Analyze the diff yourself and post the review as usual.

## Git Diff

```diff
{diff}
```

Analyze the changes and post your review using the GitHub API.
"""

# System-level instruction injected into each file_reviewer sub-agent so it
# knows its role, the review style, and the expected output format.
FILE_REVIEWER_SKILL = """\
You are a **file-level code reviewer**. You will receive a diff for one or more
files from a pull request together with PR metadata.

You have access to `terminal` and `file_editor` (read-only) so you can inspect
the full source files for surrounding context — use `cat`, `grep`, or the
file_editor `view` command when the diff alone is not enough to judge an issue.

Review style: {review_style_description}

For each issue you find, return a JSON object with these exact fields:
- `path` (string): the file path exactly as shown in the diff header
- `line` (integer): the NEW file line number where the issue occurs
- `severity` (string): one of `"critical"`, `"major"`, `"minor"`, `"nit"`
- `body` (string): a concise description of the issue with a suggested fix

Example output:
```json
[
  {{"path": "src/utils.py", "line": 42, "severity": "major", "body": "Unchecked `None` return — add a guard before accessing `.value`."}},
  {{"path": "src/utils.py", "line": 78, "severity": "nit", "body": "Unused import `os`."}}
]
```

Return your findings as a JSON array. If you find no issues, return `[]`.
Do NOT post anything to the GitHub API — the coordinator agent will handle that.
"""


def format_prompt(
    skill_trigger: str,
    title: str,
    body: str,
    repo_name: str,
    base_branch: str,
    head_branch: str,
    pr_number: str,
    commit_id: str,
    diff: str,
    review_context: str = "",
    require_evidence: bool = False,
    use_sub_agents: bool = False,
) -> str:
    """Format the PR review prompt with all parameters.

    Args:
        skill_trigger: The skill trigger (e.g., '/codereview')
        title: PR title
        body: PR description
        repo_name: Repository name (owner/repo)
        base_branch: Base branch name
        head_branch: Head branch name
        pr_number: PR number
        commit_id: HEAD commit SHA
        diff: Git diff content
        review_context: Formatted previous review context. If empty or whitespace-only,
                        the review context section is omitted from the prompt.
        require_evidence: Whether to instruct the reviewer to enforce PR description
                          evidence showing the code works.
        use_sub_agents: When True, the agent gets the TaskToolSet and decides
                        at runtime whether to delegate file-level reviews to
                        sub-agents based on diff size and complexity.

    Returns:
        Formatted prompt string
    """
    # Only include the review context section if there is actual context
    if review_context and review_context.strip():
        review_context_section = _REVIEW_CONTEXT_SECTION.format(
            review_context=review_context
        )
    else:
        review_context_section = ""

    evidence_requirements_section = (
        _EVIDENCE_REQUIREMENT_SECTION if require_evidence else ""
    )

    template = DELEGATION_PROMPT if use_sub_agents else PROMPT

    return template.format(
        skill_trigger=skill_trigger,
        title=title,
        body=body,
        repo_name=repo_name,
        base_branch=base_branch,
        head_branch=head_branch,
        pr_number=pr_number,
        commit_id=commit_id,
        review_context_section=review_context_section,
        evidence_requirements_section=evidence_requirements_section,
        diff=diff,
    )


def get_file_reviewer_skill_content(review_style: str = "standard") -> str:
    """Return the file_reviewer sub-agent skill content.

    Args:
        review_style: 'standard' or 'roasted'

    Returns:
        Formatted skill content string for the file_reviewer agent type
    """
    style_descriptions = {
        "standard": (
            "Balanced review covering correctness, style, readability, "
            "and security. Be constructive."
        ),
        "roasted": (
            "Linus Torvalds-style brutally honest review. Focus on data "
            "structures, simplicity, and pragmatism. No hand-holding."
        ),
    }
    description = style_descriptions.get(review_style, style_descriptions["standard"])
    return FILE_REVIEWER_SKILL.format(review_style_description=description)
