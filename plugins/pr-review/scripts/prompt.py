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

When sub-agent delegation is enabled (``use_sub_agents=True``), a short
delegation suffix is appended to the base prompt giving the agent the
option to delegate file-level reviews via the TaskToolSet.
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

# Appended to PROMPT when use_sub_agents=True.  Gives the main agent the
# option to delegate via the TaskToolSet without duplicating the base prompt.
_DELEGATION_SUFFIX = """
## Sub-agent Delegation

You have access to the **task** tool for delegating file-level reviews to
`file_reviewer` sub-agents. Use it when the diff is large — roughly 4+ files
or 500+ changed lines. For smaller diffs, just review directly.

When delegating, split the diff by file (or small group of related files) and
call the task tool with `subagent_type: "file_reviewer"`. Each sub-agent will
return a JSON array of findings. Merge them, de-duplicate, drop noise, and
post a single consolidated review via the GitHub API.
"""

# Skill content injected into each file_reviewer sub-agent.
# Defines the review persona, available tools, and — most importantly — the
# exact JSON schema the sub-agent must return.
FILE_REVIEWER_SKILL = """\
You are a **file-level code reviewer** sub-agent.

## Your Task

You will receive a diff for one or more files from a pull request.
Review the changes and return structured findings.

## Tools

You have `terminal` and `file_editor` so you can inspect the full source
files for surrounding context — use `cat`, `grep`, or `file_editor view`
when the diff alone is not enough to judge an issue.

## Review Style

Be direct, pragmatic, and thorough. Focus on correctness, security,
simplicity, and maintainability. Call out real problems; skip trivial noise.

## Output Format

Return a JSON array wrapped in a ```json fenced code block.
Each element must have exactly these fields:

| Field      | Type   | Description |
|------------|--------|-------------|
| `path`     | string | File path exactly as shown in the diff header (e.g. `src/utils.py`) |
| `line`     | int    | Line number in the **new** file where the issue occurs |
| `severity` | string | One of: `"critical"`, `"major"`, `"minor"`, `"nit"` |
| `body`     | string | Concise description of the issue, including a suggested fix |

### Severity guide
- **critical** — bug, security vulnerability, or data loss
- **major** — incorrect logic, missing error handling, performance issue
- **minor** — style, readability, or minor correctness concern
- **nit** — cosmetic or trivial preference

### Example

```json
[
  {{"path": "src/utils.py", "line": 42, "severity": "major", "body": "Unchecked `None` return — add a guard before accessing `.value`."}},
  {{"path": "src/utils.py", "line": 78, "severity": "nit", "body": "Unused import `os`."}}
]
```

If you find no issues, return:
```json
[]
```

**Important**: Return ONLY the JSON array. Do NOT post anything to the GitHub
API — the coordinator agent handles that.
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

    prompt = PROMPT.format(
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

    if use_sub_agents:
        prompt += _DELEGATION_SUFFIX

    return prompt


def get_file_reviewer_skill_content() -> str:
    """Return the file_reviewer sub-agent skill content."""
    return FILE_REVIEWER_SKILL
