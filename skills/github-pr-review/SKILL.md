---
name: github-pr-review
description: Post focused PR review comments using the GitHub API. Prioritizes important issues over nits.
triggers:
- /github-pr-review
---

# GitHub PR Review

Post focused code review feedback using the GitHub API. **Prioritize quality over quantity** - only comment on issues that matter.

## Core Principle

**Less is more.** A review with 2 important comments is better than one with 10 nits. Don't add noise.

## When to APPROVE vs COMMENT

**APPROVE** when:
- Code is correct and follows good practices
- Only minor style preferences differ (leave to linters)
- Changes are low-risk (config, docs, simple additions)

**COMMENT** when:
- There are real issues worth discussing
- Security, correctness, or maintainability concerns exist

**Don't comment just to comment.** If code is good, approve it.

---

## Priority Labels

Only use these three levels. **Skip nits entirely.**

| Label | When to Use |
|-------|-------------|
| 🔴 **Critical** | Must fix: security vulnerabilities, bugs, data loss risks |
| 🟠 **Important** | Should fix: logic errors, missing error handling, breaking changes |
| 🟡 **Suggestion** | Worth considering: significant simplifications, better approaches |

**What NOT to comment on:**
- Style/formatting (leave to linters)
- Minor naming preferences
- "Nice to have" improvements
- Praise for good code (just approve)

---

## Key Rule: One API Call

Bundle ALL comments into a **single review API call**. Do not post comments individually.

## Posting a Review

Use the GitHub CLI (`gh`). The `GITHUB_TOKEN` is automatically available.

```bash
gh api \
  -X POST \
  repos/{owner}/{repo}/pulls/{pr_number}/reviews \
  -f commit_id='{commit_sha}' \
  -f event='COMMENT' \
  -f body='Brief 1-2 sentence summary.' \
  -f comments[][path]='path/to/file.py' \
  -F comments[][line]=42 \
  -f comments[][side]='RIGHT' \
  -f comments[][body]='🔴 Critical: SQL injection risk - use parameterized queries.' \
  -f comments[][path]='another/file.js' \
  -F comments[][line]=15 \
  -f comments[][side]='RIGHT' \
  -f comments[][body]='🟠 Important: Missing error handling for network failures.'
```

### Parameters

| Parameter | Description |
|-----------|-------------|
| `commit_id` | Commit SHA to comment on (use `git rev-parse HEAD`) |
| `event` | `COMMENT`, `APPROVE`, or `REQUEST_CHANGES` |
| `path` | File path as shown in the diff |
| `line` | Line number in the NEW version (right side of diff) |
| `side` | `RIGHT` for new/added lines, `LEFT` for deleted lines |
| `body` | Comment text with priority label |

### Multi-Line Comments

For comments spanning multiple lines, add `start_line` to specify the range:

```bash
  -f comments[][path]='path/to/file.py' \
  -F comments[][start_line]=10 \
  -F comments[][line]=12 \
  -f comments[][side]='RIGHT' \
  -f comments[][body]='🟠 Important: Missing null check:

```suggestion
if user is None:
    raise ValueError("User required")
return process(user)
```'
```

**Important**: The suggestion must have the same number of lines as the range (e.g., lines 10-12 = 3 lines).

## GitHub Suggestions

For concrete code fixes, use the suggestion syntax for one-click apply:

~~~
```suggestion
improved_code_here()
```
~~~

Use suggestions for: bug fixes, missing error handling, small refactors.

**Don't use suggestions for:** style preferences, optional improvements, large refactors.

## Finding Line Numbers

```bash
# From diff header: @@ -old_start,old_count +new_start,new_count @@
# Count from new_start for added/modified lines

grep -n "pattern" filename     # Find line number
head -n 42 filename | tail -1  # Verify line content
```

## Fallback: curl

If `gh` is unavailable:

```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews" \
  -d '{
    "commit_id": "{commit_sha}",
    "event": "COMMENT",
    "body": "Review summary.",
    "comments": [
      {"path": "file.py", "line": 42, "side": "RIGHT", "body": "🔴 Critical: Issue"},
      {"path": "file.py", "start_line": 10, "line": 12, "side": "RIGHT", "body": "🟠 Important: Issue"}
    ]
  }'
```

---

## Summary

1. **Filter first**: Only comment on 🔴 Critical and 🟠 Important issues. Skip nits.
2. **One API call**: Bundle all comments into a single review
3. **Use labels**: 🔴🟠🟡 on every comment (no 🟢 nits)
4. **Approve readily**: If no real issues, just approve
5. **Keep it brief**: Details in inline comments, summary stays short
