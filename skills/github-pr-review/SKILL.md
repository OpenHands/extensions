---
name: github-pr-review
description: Post PR review comments using the GitHub API with inline comments, suggestions, and priority labels.
triggers:
- /github-pr-review
---

# GitHub PR Review

Post structured code review feedback using the GitHub API with inline comments on specific lines.

## Key Rule: One API Call

Bundle ALL comments into a **single review API call**. Do not post comments individually.

## Posting a Review

Use the GitHub CLI (`gh`) with a JSON input file. The `GITHUB_TOKEN` is automatically available.

**Important**: Always use `--input` with a JSON file instead of `-F` flags. This avoids shell quoting issues with special characters in comment bodies (quotes, backticks, newlines, etc.) and eliminates the need for complex heredoc scripts.

### Step 1: Create a JSON file

```bash
cat > /tmp/review.json << 'EOF'
{
  "commit_id": "{commit_sha}",
  "event": "COMMENT",
  "body": "Brief 1-3 sentence summary.",
  "comments": [
    {
      "path": "path/to/file.py",
      "line": 42,
      "side": "RIGHT",
      "body": "🟠 Important: Your comment here."
    },
    {
      "path": "another/file.js",
      "line": 15,
      "side": "RIGHT",
      "body": "🟡 Suggestion: Another comment."
    }
  ]
}
EOF
```

### Step 2: Post the review

```bash
gh api -X POST repos/{owner}/{repo}/pulls/{pr_number}/reviews --input /tmp/review.json
```

### Step 3: Confirm completion with a PR issue comment

After the review API call succeeds, post a short issue comment on the PR conversation confirming that the review finished. This gives the PR timeline a durable marker that the review was actually submitted on a specific commit, which is useful when an agent analyzed the PR but might otherwise fail before leaving visible proof that the review API call succeeded.

```bash
gh api -X POST repos/{owner}/{repo}/issues/{pr_number}/comments \
  -f body='Completed OpenHands review: submitted a COMMENT review on commit {commit_sha}.'
```

Replace `COMMENT` with the same value you sent in the review payload's `event` field (`COMMENT`, `APPROVE`, or `REQUEST_CHANGES`). Replace `{commit_sha}` with the same SHA you used in `commit_id`.

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

```json
{
  "path": "path/to/file.py",
  "start_line": 10,
  "line": 12,
  "side": "RIGHT",
  "body": "🟡 Suggestion: Refactor this block:\n\n```suggestion\nline_one = \"new\"\nline_two = \"code\"\nline_three = \"here\"\n```"
}
```

**Important**: The suggestion must have the same number of lines as the range (e.g., lines 10-12 = 3 lines).

## Priority Labels

Start each comment with a priority label. **Minimize nits** - leave minor style issues to linters.

| Label | When to Use |
|-------|-------------|
| 🔴 **Critical** | Must fix: security vulnerabilities, bugs, data loss risks |
| 🟠 **Important** | Should fix: logic errors, performance issues, missing error handling |
| 🟡 **Suggestion** | Worth considering: significant improvements to clarity or maintainability |

**Do NOT post 🟢 Nit or 🟢 Acceptable comments.** If code is fine, simply don't comment on it. Inline comments that say "this looks good" or "acceptable trade-off" are noise — they create review threads that must be resolved without providing actionable value.

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

If `gh` is unavailable, use curl with the JSON file:

```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews" \
  -d @/tmp/review.json
```

## Summary

1. Analyze the code and identify important issues (minimize nits)
2. Write review data to a JSON file (e.g., `/tmp/review.json`)
3. Post **ONE** review using `gh api --input /tmp/review.json`
4. Post a short PR issue comment confirming the review was submitted on the same event and commit SHA
5. Use priority labels (🔴🟠🟡) on every comment
6. Do NOT post comments for code that is acceptable - only comment when action is needed
7. Use suggestion syntax for concrete code changes
8. Keep the review body brief (details go in inline comments)
9. If no issues: post a short approval message with no inline comments, then post the matching completion comment
10. Do not finish unless both the review object and completion comment were created successfully
