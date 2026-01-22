---
name: github-pr-review
description: How to post PR review comments using GitHub API, including inline comments, line numbers, multi-line suggestions, and the gh CLI. Use when reviewing pull requests and need to post structured feedback.
triggers:
- /github-pr-review
---

# GitHub PR Review Mechanics

This skill teaches how to post PR review comments using the GitHub API, including inline comments on specific lines, multi-line suggestions, and proper use of the `gh` CLI.

## Posting PR Reviews with Inline Comments

Use the GitHub CLI (`gh`) to post reviews with inline comments. The `GITHUB_TOKEN` environment variable is automatically available.

### Single API Call with Multiple Comments (Recommended)

Always bundle all comments into ONE review API call to avoid notification spam:

```bash
gh api \
  -X POST \
  repos/{owner}/{repo}/pulls/{pr_number}/reviews \
  -f commit_id='{commit_sha}' \
  -f event='COMMENT' \
  -f body='Brief summary of the review.' \
  -f comments[][path]='path/to/file.py' \
  -F comments[][line]=42 \
  -f comments[][side]='RIGHT' \
  -f comments[][body]='Your comment about this line.' \
  -f comments[][path]='path/to/another_file.js' \
  -F comments[][line]=15 \
  -f comments[][side]='RIGHT' \
  -f comments[][body]='Another comment.'
```

### Parameters Explained

- **commit_id**: The SHA of the commit to comment on (use `git rev-parse HEAD`)
- **event**: Use `COMMENT` for neutral feedback, `APPROVE` to approve, `REQUEST_CHANGES` to request changes
- **path**: Exact file path as shown in the diff (e.g., `src/utils/helper.py`)
- **line**: Line number in the NEW version of the file (right side of diff)
- **side**: `RIGHT` for new/added lines (most common), `LEFT` for deleted lines
- **body**: The comment text (supports markdown and suggestion syntax)

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

For comments spanning multiple lines, you have two options:

### Option 1: Using `start_line` and `line` parameters

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

### Option 2: Using `--line` with a range (simpler)

You can also comment on a range of lines using `--line 10-20` syntax:

```bash
gh pr comment {pr_number} --body "Your comment here" --line 10-20 --path path/to/file.py
```

**IMPORTANT**: The number of lines in your suggestion block MUST match the line range. If you select lines 10-12 (3 lines), your suggestion must contain exactly 3 lines.

## GitHub Suggestion Syntax

For small code changes, use GitHub's suggestion feature (one-click apply):

~~~markdown
```suggestion
def improved_function():
    return "better code here"
```
~~~

### When to Use Suggestions

✅ Good for:
- Renaming variables or functions
- Fixing typos or formatting
- Small refactors (1-5 lines)
- Adding type hints or docstrings
- Fixing comments

❌ Avoid for:
- Large refactors (multiple files)
- Architectural changes needing discussion
- Changes with multiple valid approaches

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

## Best Practices

1. **One API call**: Bundle all comments into a single review to avoid notification spam
2. **Brief summary**: Keep the review body short (1-3 sentences) since details are in inline comments
3. **Specific line numbers**: Always verify line numbers before posting
4. **Match suggestion lines**: Ensure suggestion line count matches the selected range
5. **Use RIGHT side**: For commenting on new/modified code (most common case)
