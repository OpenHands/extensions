---
name: github-pr-review
description: How to post PR review comments using GitHub API, including inline comments, line numbers, multi-line suggestions, and the gh CLI. Use when reviewing pull requests and need to post structured feedback.
triggers:
- /github-pr-review
---

# GitHub PR Review Mechanics

This skill teaches how to post PR review comments using the GitHub API, including inline comments on specific lines, multi-line suggestions, and proper use of the `gh` CLI.

## CRITICAL: Post ONE Single Review with All Comments

After completing your analysis, you MUST post your review as a **single API call** that includes both the summary AND all inline comments together.

**IMPORTANT - Avoid Duplication:**
- Do NOT post individual inline comments separately and then a summary review
- Do NOT make multiple API calls - use ONE call with all comments bundled
- The summary in the review body should be brief (1-3 sentences) since details are in inline comments

## Posting PR Reviews with Inline Comments

Use the GitHub CLI (`gh`) to post reviews with inline comments. The `GITHUB_TOKEN` environment variable is automatically available.

### Post a Review with Multiple Inline Comments (Required Approach)

```bash
gh api \
  -X POST \
  repos/{owner}/{repo}/pulls/{pr_number}/reviews \
  -f commit_id='{commit_sha}' \
  -f event='COMMENT' \
  -f body='Brief 1-3 sentence summary. Details are in inline comments below.' \
  -f comments[][path]='path/to/file.py' \
  -F comments[][line]=42 \
  -f comments[][side]='RIGHT' \
  -f comments[][body]='Your specific comment about this line.' \
  -f comments[][path]='path/to/another_file.js' \
  -F comments[][line]=15 \
  -f comments[][side]='RIGHT' \
  -f comments[][body]='Another specific comment.'
```

### Only If You Have a Single Comment to Make

```bash
gh api \
  -X POST \
  repos/{owner}/{repo}/pulls/{pr_number}/reviews \
  -f commit_id='{commit_sha}' \
  -f event='COMMENT' \
  -f body='Brief summary.' \
  -f comments[][path]='path/to/file.py' \
  -F comments[][line]=42 \
  -f comments[][side]='RIGHT' \
  -f comments[][body]='Your specific comment about this line.'
```

### Parameters Explained

- **commit_id**: The SHA of the commit to comment on (use `git rev-parse HEAD`)
- **event**: Use `COMMENT` for neutral feedback, `APPROVE` to approve, `REQUEST_CHANGES` to request changes
- **path**: Exact file path as shown in the diff (e.g., `src/utils/helper.py`)
- **line**: Line number in the NEW version of the file (the right side of the diff). For added lines (starting with +), use the line number shown in the diff.
- **side**: `RIGHT` for new/added lines (most common), `LEFT` for deleted lines
- **body**: The comment text. Provide a clear, actionable comment. Be specific about what should be changed.

## Priority Labels for Review Comments

**IMPORTANT**: Each inline comment MUST start with a priority label to help the PR author understand the importance of each suggestion. Use one of these prefixes:

- **🔴 Critical**: Must be fixed before merging. Security vulnerabilities, bugs that will cause failures, data loss risks, or breaking changes.
- **🟠 Important**: Should be addressed. Logic errors, performance issues, missing error handling, or significant code quality concerns.
- **🟡 Suggestion**: Nice to have improvements. Better naming, code organization, or minor optimizations that would improve the code.
- **🟢 Nit**: Minor stylistic preferences. Formatting, comment wording, or trivial improvements that are optional.

**Example comment with priority:**
```
🟠 Important: This function doesn't handle the case when `user` is None, which could cause an AttributeError in production.

```suggestion
if user is None:
    raise ValueError("User cannot be None")
```
```

**Another example:**
```
🟢 Nit: Consider using a more descriptive variable name for clarity.

```suggestion
user_count = len(users)
```
```

## Finding Line Numbers

### From the Diff Header

The diff header shows line ranges: `@@ -old_start,old_count +new_start,new_count @@`

Count lines from `new_start` for added/modified lines in the new version.

### Using grep

```bash
grep -n "pattern" filename
```

### Verifying a Line

```bash
head -n 42 filename | tail -1
```

## Multi-Line Comments and Suggestions

When your comment or suggestion spans multiple lines, you MUST specify a line range using both `start_line` and `line` parameters. This is **critical** for multi-line suggestions - if you only specify `line`, the suggestion will be misaligned.

**Parameters for multi-line comments:**
- **start_line**: The first line of the range (required for multi-line)
- **line**: The last line of the range
- **start_side**: Side of the first line (optional, defaults to same as `side`)
- **side**: Side of the last line

```bash
gh api \
  -X POST \
  repos/{owner}/{repo}/pulls/{pr_number}/reviews \
  -f commit_id='{commit_sha}' \
  -f event='COMMENT' \
  -f body='Found an issue spanning multiple lines.' \
  -f comments[][path]='path/to/file.py' \
  -F comments[][start_line]=10 \
  -F comments[][line]=12 \
  -f comments[][side]='RIGHT' \
  -f comments[][body]='Consider this improvement:

```suggestion
first_line = "improved"
second_line = "code"
third_line = "here"
```'
```

**IMPORTANT**: The number of lines in your suggestion block MUST match the number of lines in the selected range (line - start_line + 1). If you select lines 10-12 (3 lines), your suggestion must also contain exactly 3 lines.

## GitHub Suggestion Syntax

For small, concrete code changes, use GitHub's suggestion feature. This allows the PR author to apply your suggested change with one click. Format suggestions in the comment body using the special markdown syntax:

~~~markdown
```suggestion
def improved_function():
    return "better code here"
```
~~~

### Example: Including a Suggestion in Your Review

Include the suggestion syntax in the `body` field of your inline comment within the review:

```bash
gh api \
  -X POST \
  repos/{owner}/{repo}/pulls/{pr_number}/reviews \
  -f commit_id='{commit_sha}' \
  -f event='COMMENT' \
  -f body='Found one issue with variable naming.' \
  -f comments[][path]='path/to/file.py' \
  -F comments[][line]=42 \
  -f comments[][side]='RIGHT' \
  -f comments[][body]='🟡 Suggestion: Consider using a more descriptive variable name:

```suggestion
user_count = len(users)
```'
```

### When to Use Suggestions

✅ Good for:
- Renaming variables or functions for clarity
- Fixing typos or formatting issues
- Small refactors (1-5 lines)
- Adding missing type hints or docstrings
- Fixing misleading or outdated comments
- Updating documentation or README content
- Correcting comments in configuration files (YAML, JSON, etc.)

❌ Avoid for:
- Large refactors requiring multiple file changes
- Architectural changes that need discussion
- Changes where multiple valid approaches exist

## Fallback: Using curl

If `gh` is unavailable:

```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews" \
  -d '{
    "commit_id": "{commit_sha}",
    "body": "Review summary.",
    "event": "COMMENT",
    "comments": [
      {
        "path": "path/to/file.py",
        "line": 42,
        "side": "RIGHT",
        "body": "Your comment here."
      },
      {
        "path": "path/to/file.py",
        "start_line": 10,
        "line": 12,
        "side": "RIGHT",
        "body": "Multi-line suggestion:\n\n```suggestion\nline1\nline2\nline3\n```"
      }
    ]
  }'
```

## What to Review

- Focus on bugs, security issues, performance problems, and code quality
- Only post comments for actual issues or important suggestions
- Use the suggestion syntax for small, concrete code changes
- Be constructive and specific about what should be changed
- **Always include a priority label** (🔴 Critical, 🟠 Important, 🟡 Suggestion, 🟢 Nit) at the start of each inline comment
- If there are no issues, post a single review with an approval message (no inline comments needed)

## Best Practices

1. **One API call**: Bundle all comments into a single review to avoid notification spam
2. **Brief summary**: Keep the review body short (1-3 sentences) since details are in inline comments
3. **Specific line numbers**: Always verify line numbers before posting
4. **Match suggestion lines**: Ensure suggestion line count matches the selected range
5. **Use RIGHT side**: For commenting on new/modified code (most common case)
6. **Priority labels**: Always start inline comments with a priority emoji (🔴🟠🟡🟢)

## Your Task

1. Analyze the diff and code carefully
2. Identify ALL specific issues on specific lines
3. Post ONE single review using the GitHub API that includes:
   - A brief summary in the review body (1-3 sentences)
   - ALL inline comments bundled in the same API call
4. Do NOT make multiple API calls or post comments separately

**CRITICAL**: Make exactly ONE API call to post your complete review. Do NOT post individual comments first and then a summary - this creates duplication.
