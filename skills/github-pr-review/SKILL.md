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

**Important**: Always use `--input` with a JSON file instead of inline `-F` flags. This avoids shell quoting issues with special characters in comment bodies (quotes, backticks, newlines, etc.) and eliminates the need for bash-only heredoc scripts.

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

**`start_line`/`line` define the range that will be REPLACED.** The suggestion block may have any number of lines — it does **not** have to match the range size. See the next section for the exact semantics; getting this wrong is how suggestions silently delete or duplicate code.

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

### How Suggestions Actually Work (READ THIS BEFORE WRITING ONE)

A suggestion block **replaces** the targeted range with its contents. The replaced range is:

- `line` only → the single line `line` (replaces 1 line)
- `start_line` + `line` → the inclusive range `start_line..line` (replaces `line - start_line + 1` lines)

The suggestion content can be **any number of lines** — 0 (deletion), 1, or many. It does not have to match the range size. Whatever is between the ` ```suggestion ` and closing ` ``` ` fences becomes the new content of those lines.

Writing the wrong combination of `start_line`/`line` and suggestion body is what causes accepted suggestions to **duplicate** or **delete** code. Use the table below as your contract:

| Intent | `start_line` | `line` | Suggestion body must contain |
|--------|--------------|--------|-------------------------------|
| Change line N | omit | N | the new content for line N |
| Change lines N..M | N | M | the new content for the whole block |
| **Add** a line **after** line N (keep line N) | omit | N | line N's exact current text, then the new line(s) |
| **Add** a line **before** line N (keep line N) | omit | N | the new line(s), then line N's exact current text |
| **Insert** lines inside range N..M (keep N..M) | N | M | every original line in N..M plus the new lines, in the final desired order |
| **Delete** line N | omit | N | empty body (just an empty ` ```suggestion ``` ` block) |
| **Delete** lines N..M | N | M | empty body |

### Common Mistakes That Break Code

1. **Duplicated lines.** You copy a neighboring line (N-1 or N+1) into the suggestion body as context — that line is still present in the file outside the replaced range, so accepting the suggestion inserts a second copy of it. Fix: only include lines that fall within the targeted range, plus any genuinely new content.
2. **Disappearing lines.** You target `start_line=10, line=12` to comment on a 3-line block, but your suggestion body only contains 1 line because you "only want to change line 11". Accepting that suggestion deletes lines 10 and 12. Fix: either narrow the range to just line 11, or include lines 10 and 12 verbatim in the body.
3. **Description does not match the suggestion.** The prose says "rename this variable" but the suggestion replaces an entire function. Or the prose says "add a None check" but the suggestion only contains the check (deleting the original code). Fix: after writing the suggestion, re-read the prose and confirm the resulting file would match it line-for-line.

### Mandatory Verification Before Posting

For every comment that contains a ` ```suggestion ``` ` block, do this check before adding it to the review JSON:

1. Read the actual file lines that will be replaced using the file editor, your code editor, or another shell-appropriate file-view command.
2. Mentally apply the suggestion: drop those lines, splice in the suggestion body, and look at the result in context.
3. Confirm the resulting code matches **exactly** what your prose description promises — no extra duplicated line above/below, no original line accidentally dropped, no off-by-one.
4. If the change cannot be expressed cleanly as a contiguous replacement (e.g., it touches non-adjacent lines, or it depends on edits elsewhere in the file), do **not** use a suggestion block — describe the change in prose instead.

If you are not 100% sure the suggestion will produce the exact code you described, drop the ` ```suggestion ``` ` block and leave a regular inline comment. A correct prose comment is always better than a one-click suggestion that silently corrupts the file.

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
6. Use suggestion syntax for concrete code changes, but only after verifying the resulting code matches your description (see "How Suggestions Actually Work")
7. Keep the review body brief (details go in inline comments)
8. If no issues: post a short approval message with no inline comments
