# Learn from Code Review

Distill code review feedback from GitHub pull requests into reusable skills and repository guidelines.

## What It Does

This skill analyzes PR review comments from a repository and extracts recurring patterns of feedback. These patterns are then transformed into:

- **Repository-specific skills** (`.openhands/skills/`) for domain-specific patterns
- **AGENTS.md updates** for general coding conventions and best practices

## When to Use

- "Learn from our code reviews"
- "Distill PR feedback into guidelines"
- "What patterns do reviewers keep pointing out?"
- "Generate coding standards from review history"
- Running `/learn-from-reviews`

## Requirements

- `GITHUB_TOKEN` environment variable
- GitHub CLI (`gh`) available

## Example

```
User: Learn from our code reviews over the past month

Agent: I'll analyze recent PR review comments and distill them into actionable guidelines.

[Analyzes 25 merged PRs with 150 review comments]
[Filters out bot comments and low-signal responses]
[Identifies 4 recurring patterns]

Found the following patterns from code review feedback:

1. Error Handling (12 comments)
   - Always include context when logging errors
   - Use structured error responses in APIs

2. Testing (8 comments)
   - Add edge case tests for validation logic
   - Mock external services consistently

3. Database Queries (6 comments)
   - Use parameterized queries exclusively
   - Add appropriate indexes for new queries

I'll create a draft PR with:
- New skill: `.openhands/skills/error-handling/SKILL.md`
- Updates to `AGENTS.md` with testing and database guidelines
```

## Output

The skill generates a draft PR containing proposed changes based on the analysis. Human review is expected before merging.

## Related Skills

- `github-pr-review` - Post structured code reviews
- `code-review` - Perform code reviews
- `skill-creator` - Create new skills manually
- `agent-memory` - Persist repository knowledge
