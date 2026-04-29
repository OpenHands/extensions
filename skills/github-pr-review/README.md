# Github Pr Review

Post PR review comments using the GitHub API with inline comments, suggestions, and priority labels.

## Triggers

This skill is activated by the following keywords:

- `/github-pr-review`

## Details

# GitHub PR Review

Post structured code review feedback using the GitHub API with inline comments on specific lines.

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
  -f body='Brief 1-3 sentence summary.' \
  -f comments[][path]='path/to/file.py' \
  -F comments[][line]=42 \
  -f comments[][side]='RIGHT' \
  -f comments[][body]='🟠 Important: Your comment here.' \
  -f comments[][path]='another/file.js' \
  -F comments[][line]=15 \
  -f comments[][side]='RIGHT' \
  -f comments[][body]='🟡 Suggestion: Another comment.'
```

### Confirm completion with a PR issue comment

After the review API call succeeds, post a short issue comment on the PR conversation confirming that the review finished. This gives the PR timeline a durable marker that the review was actually submitted on a specific commit, which is useful when an agent analyzed the PR but might otherwise fail before leaving visible proof that the review API call succeeded.

```bash
gh api -X POST repos/{owner}/{repo}/issues/{pr_number}/comments \
  -f body='Completed OpenHands review: submitted a COMMENT review on commit {commit_sha}.'
```

Replace `COMMENT` with the same value you sent in the review request's `event` field (`COMMENT`, `APPROVE`, or `REQUEST_CHANGES`). Replace `{commit_sha}` with the same SHA you used for `commit_id`.

**Mandatory:** The review is only complete after both API calls succeed:
1. create the PR review object, and
2. post the completion comment on the PR issue.

If you found no actionable issues, post a short `APPROVE` review and a matching completion comment rather than ending silently without posting a review.

If the review API call fails, do not post the completion comment. If the review succeeds but the completion comment fails, tell the user that the review was submitted but completion reporting failed, include the review event and commit SHA in that response, and keep trying or ask for help instead of claiming success.

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
  -f comments[][body]='🟡 Suggestion: Refactor this block:

```suggestion
line_one = "new"
line_two = "code"
line_three = "here"
```'
```

**Important**: The suggestion must have the same number of lines as the range (e.g., lines 10-12 = 3 lines).

## Priority Labels

Start each comment with a priority label:

| Label | When to Use |
|-------|-------------|
| 🔴 **Critical** | Must fix: security vulnerabilities, bugs, data loss risks |
| 🟠 **Important** | Should fix: logic errors, performance issues, missing error handling |
| 🟡 **Suggestion** | Nice to have: better naming, code organization |
| 🟢 **Nit** | Optional: formatting, minor style preferences |

**Example:**
```
🟠 Important: This function doesn't handle None, which could cause an AttributeError.

```suggestion
if user is None:
    raise ValueError("User cannot be None")
```
```

## GitHub Suggestions

For small code changes, use the suggestion syntax for one-click apply:

~~~
```suggestion
improved_code_here()
```
~~~

Use suggestions for: renaming, typos, small refactors (1-5 lines), type hints, docstrings.

Avoid for: large refactors, architectural changes, ambiguous improvements.

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
      {"path": "file.py", "line": 42, "side": "RIGHT", "body": "Comment"},
      {"path": "file.py", "start_line": 10, "line": 12, "side": "RIGHT", "body": "Multi-line"}
    ]
  }'
```

## Summary

1. Analyze the code and identify issues
2. Post **ONE** review with all inline comments bundled
3. Post a short PR issue comment confirming the review was submitted on the same event and commit SHA
4. Use priority labels (🔴🟠🟡) on every comment
5. Use suggestion syntax for concrete code changes
6. Keep the review body brief (details go in inline comments)
7. If no issues: post a short approval message, then post the matching completion comment
8. Do not finish unless both the review object and completion comment were created successfully