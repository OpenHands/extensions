---
name: learn-from-code-review
description: Distill code review feedback from GitHub PRs into reusable skills and guidelines. This skill should be used when users ask to "learn from code reviews", "distill PR feedback", "improve coding standards", "extract learnings from reviews", or want to generate skills/guidelines from historical review comments.
triggers:
- /learn-from-reviews
- learn from code review
- distill reviews
---

# Learn from Code Review

Analyze code review comments from GitHub pull requests and distill them into reusable skills or repository guidelines that improve future code quality.

## Overview

Code review feedback contains valuable institutional knowledge that often gets buried across hundreds of PRs. This skill extracts meaningful patterns from review comments and transforms them into:

1. **Repository-specific skills** - Placed in `.openhands/skills/` for domain-specific patterns
2. **AGENTS.md guidelines** - Overall repository conventions and best practices

## Prerequisites

- `GITHUB_TOKEN` environment variable must be set
- GitHub CLI (`gh`) should be available

## Workflow

### Step 1: Identify Target Repository

Determine the repository to analyze:

```bash
# Get current repo info
gh repo view --json nameWithOwner -q '.nameWithOwner'
```

If not in a repository, ask the user which repository to analyze.

### Step 2: Fetch Review Comments

Retrieve PR review comments from the repository:

```bash
# Fetch merged PRs from the last 30 days (adjustable)
gh pr list --repo {owner}/{repo} \
  --state merged \
  --limit 50 \
  --json number,title,mergedAt

# For each PR, fetch review comments
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments \
  --jq '.[] | {body: .body, path: .path, user: .user.login, created_at: .created_at}'

# Also fetch review-level comments (not tied to specific lines)
gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews \
  --jq '.[] | select(.body != "") | {body: .body, user: .user.login, state: .state}'
```

### Step 3: Filter and Categorize Comments

Apply noise filtering to keep only meaningful feedback:

**Exclude:**
- Bot comments (dependabot, copilot, github-actions, etc.)
- Low-signal responses ("LGTM", "+1", "looks good", "thanks", "nice")
- Comments shorter than 30 characters
- Auto-generated comments (CI status, coverage reports)

**Categorize remaining comments by:**
- Security concerns
- Performance patterns
- Code style/conventions
- Architecture/design patterns
- Error handling
- Testing requirements
- Documentation standards

### Step 4: Distill Patterns

For each category with sufficient examples (3+ similar comments), identify:

1. **The recurring issue** - What mistake or oversight keeps appearing
2. **The desired pattern** - What reviewers consistently ask for
3. **Example context** - Concrete before/after code snippets when available

### Step 5: Generate Output

If clear, actionable patterns emerge, generate focused skill files. If no clear patterns emerge, report this to the user—it's fine to produce no output when the codebase already has strong conventions or when review comments don't cluster into recurring themes.

When creating skills, place them in `.openhands/skills/{domain-name}/SKILL.md`:

```yaml
---
name: database-queries
description: Database query patterns and best practices for this repository.
---

# Database Query Guidelines

### Always Use Parameterized Queries
[Pattern description with examples]

### Connection Pool Management
[Pattern description with examples]
```

Prefer skills over AGENTS.md updates, since AGENTS.md typically already contains general coding guidelines.

### Step 6: Create Draft PR (if applicable)

Use the `create_pr` tool to open a draft PR with the proposed changes. The PR description should include:
- Number of PRs analyzed
- Number of comments processed
- Categories of patterns found
- List of proposed changes (new skills and/or AGENTS.md updates)

## Example Output

### Sample Skill: API Error Handling

```yaml
---
name: api-error-handling
description: API error handling patterns for this repository.
---

# API Error Handling

## Always Return Structured Errors

❌ Avoid:
```python
return {"error": str(e)}
```

✅ Prefer:
```python
return {
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input",
        "details": {"field": "email", "reason": "Invalid format"}
    }
}
```

## Log Before Returning Errors

```python
logger.error(f"API error in {endpoint}: {e}", exc_info=True)
return error_response(e)
```
```

## Defaults

This workflow analyzes PRs from the past 30 days by default.

## Best Practices

1. **Run periodically** - Schedule monthly or quarterly to capture evolving patterns
2. **Review before merging** - Generated content is a draft; human review is essential
3. **Iterate** - Refine patterns based on team feedback
4. **Avoid duplication** - Check existing AGENTS.md and skills before adding
5. **Cite sources** - Reference PR numbers when documenting patterns

## Error Handling

Handle these common edge cases gracefully:

- **Repository has few PRs**: If fewer than 10 merged PRs exist in the timeframe, inform the user that there may not be enough data to identify patterns. Proceed with analysis but note the limited sample size.
- **No patterns emerge**: When comments don't cluster into recurring themes (common for well-established codebases), report this to the user and suggest either expanding the time range or that the codebase may already have strong conventions.
- **Token lacks repository access**: If the GitHub API returns 403/404, explain that the token may not have access to the repository and suggest checking token permissions.
- **`gh` CLI unavailable**: Fall back to direct GitHub API calls using `curl` with `$GITHUB_TOKEN`, or inform the user that `gh` needs to be installed.

## Limitations

- Only analyzes accessible repositories (requires appropriate permissions)
- Cannot capture verbal feedback from pair programming or meetings
- Patterns may reflect individual reviewer preferences vs. team consensus
- Historical comments may reference outdated code patterns

## Additional Resources

For posting structured code reviews, see the `github-pr-review` skill.
For creating new skills, see the `skill-creator` skill.
