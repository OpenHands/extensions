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

Use the GitHub CLI (`gh`) with a JSON input file. The `GITHUB_TOKEN` is automatically available.

**Important**: Always use `--input` with a JSON file instead of inline `-F` flags. This avoids shell quoting issues with special characters in comment bodies and works cleanly across Windows, macOS, and Linux.

### Step 1: Create a JSON file

Write the review payload to a JSON file under the system temporary directory (for example `<system-temp>/review.json`). Use the file editor or any shell-appropriate file-writing command. Replace `<system-temp>` with an absolute path for the current OS temp directory.

```json
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
```

### Step 2: Post the review

```text
gh api -X POST repos/{owner}/{repo}/pulls/{pr_number}/reviews --input <system-temp>/review.json
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

```json
{
  "path": "path/to/file.py",
  "start_line": 10,
  "line": 12,
  "side": "RIGHT",
  "body": "🟡 Suggestion: Refactor this block:\n\n```suggestion\nline_one = \"new\"\nline_two = \"code\"\nline_three = \"here\"\n```"
}
```

**`start_line`/`line` define the range that will be REPLACED.** The suggestion block may have any number of lines — it does **not** have to match the range size.

## Priority Labels

Start each comment with a priority label. **Minimize nits** — leave minor style issues to linters.

| Label | When to Use |
|-------|-------------|
| 🔴 **Critical** | Must fix: security vulnerabilities, bugs, data loss risks |
| 🟠 **Important** | Should fix: logic errors, performance issues, missing error handling |
| 🟡 **Suggestion** | Worth considering: significant improvements to clarity or maintainability |

**Do NOT post 🟢 Nit or 🟢 Acceptable comments.** If code is fine, simply don't comment on it.

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

Use the file editor, your code editor's line numbers, or another shell-appropriate search command. Verify the exact lines to be replaced before posting a suggestion; do not rely on POSIX-only `grep`, `sed`, or `head | tail` snippets.

## Fallback: curl

If `gh` is unavailable, use any HTTP client that can POST the saved JSON file. Example:

```text
curl -X POST -H "Authorization: token $GITHUB_TOKEN" -H "Accept: application/vnd.github+json" -H "Content-Type: application/json" https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews --data-binary @<system-temp>/review.json
```

## Summary

1. Analyze the code and identify important issues (minimize nits)
2. Write review data to a JSON file under the system temporary directory (for example `<system-temp>/review.json`)
3. Post **ONE** review using `gh api --input <system-temp>/review.json`
4. Use priority labels (🔴🟠🟡) on every comment
5. Do NOT post comments for code that is acceptable — only comment when action is needed
6. Use suggestion syntax for concrete code changes, but verify the resulting code first
7. Keep the review body brief (details go in inline comments)
8. If no issues: post a short approval message with no inline comments