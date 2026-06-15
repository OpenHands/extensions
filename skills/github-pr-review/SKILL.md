---
name: github-pr-review
description: Post PR review comments using the GitHub API with inline comments, suggestions, and priority labels.
triggers:
- /github-pr-review
---

# GitHub PR Review

Post a single **Pull Request Review** with one **inline comment per finding** — never a single blob comment. The body of each inline comment follows the `github-code-quality[bot]` format so reviewers can scan, discuss, and one-click-apply suggestions directly on the diff line.

Reference example of the target format: https://github.com/m0nklabs/cryptotrader/pull/379 (16 inline review threads, each on its own file/line, each with a `## <Category>` heading, one-line statement, `---` separator, and prose fix guidance).

## Pre-Review Checks (run before drafting the review)

1. **PR is still open:**
   ```bash
   gh pr view {pr_number} --json state,mergedAt,merged
   ```
   - `state: OPEN` → proceed.
   - `state: MERGED` → stop, nothing to review.
   - `state: CLOSED` and `merged: false` → stop, do not review. The PR was abandoned; route back to planning.

2. **Scope guardrail:** review only within the issue/PR scope and regressions introduced by that scope. Do not flag unrelated cleanup, refactors, or wishlist improvements. If a finding is out of scope, skip it.

3. **Severity filter:** only report findings that are medium severity or higher, have a concrete failure mechanism, and tie to user-visible impact, correctness risk, or metric distortion. Style nits belong to linters, not reviews.

4. **Cap the number of findings.** A focused review with 5 strong findings beats a noisy review with 20 weak ones. If you have more than ~10, keep the top-severity ones and silently drop the rest.

5. **Order by severity:** 🔴 Critical → 🟠 Important → 🟡 Suggestion. Within the same priority, the most user-visible issue goes first.

## Key Rule: One PR Review, One API Call, Many Inline Comments

Post exactly **one** Pull Request Review (`POST /repos/{owner}/{repo}/pulls/{pr_number}/reviews`) whose `comments[]` array contains **one entry per finding**. Each entry becomes a separate inline thread anchored to a `path` + `line` + `side`.

**Do NOT:**
- Post a single big issue/PR comment that contains all findings as numbered sections. That bypasses the inline diff anchoring, breaks the suggestion-block UX, and is not what `github-code-quality[bot]` does.
- Post each finding as a separate API call. That fragments the review into N pending reviews and pollutes the timeline.

## Inline Comment Body Format

Each `comments[i].body` string follows this exact template (this is the `github-code-quality[bot]` shape, with the priority label folded into the heading and an optional one-click suggestion block appended):

```markdown
## <Priority> <Category>

<One-line statement of the issue>

---

<General fix philosophy: how to address this class of issue without changing behavior.>

Best fix in this file (`<path/to/file.py`): <concrete, line-specific guidance.>

<Scope confirmation: "No logic changes, new methods, or dependency changes are needed." or equivalent.>

```suggestion
<optional replacement code, only when the fix is small and contiguous>
```
```

Rules:
- **Heading** is `## <Priority> <Category>`. The priority prefix is one of:
  - `🔴 Critical:` — must fix: security, data loss, broken invariants.
  - `🟠 Important:` — should fix: logic errors, performance, missing error handling.
  - `🟡 Suggestion:` — worth considering: clarity, maintainability.
  - **Never** `🟢 Nit` or `🟢 Acceptable`. If the code is fine, do not comment.
- **One-line statement** names the specific defect at that file/line. No "consider", no "could be better" — state what is wrong.
- **`---`** is a literal Markdown horizontal rule. It separates the diagnosis from the fix guidance and is what makes the format scannable in the GitHub UI.
- **General fix** is one or two sentences explaining the approach (e.g., "remove only the unused symbol from the import list while keeping used imports intact").
- **Best fix here** is anchored to the actual file path and line number in backticks. It is the *one* edit the reviewer should make.
- **Scope confirmation** explicitly says no other code changes / no new imports / no new methods are needed. This is what differentiates a focused review from a sprawl.
- **` ```suggestion ``` ` block** is appended at the end when, and only when, the change can be expressed as a contiguous replacement of ≤ 5 lines on the new (right) side. For multi-region, architectural, or ambiguous changes, omit the block — describe the fix in prose instead.

### Worked example (matches the format on PR #379)

```
🟠 Important: Unused import

Import of 'generate_macd_signal' is not used.

---

To fix an unused import without changing behavior, remove only the unused symbol from the import statement and keep the rest intact.

Best fix in this file (`core/analysis/indicator_correlation.py`): update line 23 so it imports only `compute_macd`, and remove `generate_macd_signal` from that line. No other code changes are needed, assuming the symbol is indeed unused throughout the file.

```suggestion
from core.indicators.macd import compute_macd
```
```

## Posting the Review

Use the GitHub CLI (`gh`) with a JSON input file. The `GITHUB_TOKEN` is automatically available.

**Important**: Always use `--input` with a JSON file instead of `-F` flags. This avoids shell-quoting issues with backticks, quotes, and newlines inside suggestion blocks.

### Step 1: Create the JSON file

```bash
cat > /tmp/review.json << 'EOF'
{
  "commit_id": "{commit_sha}",
  "event": "COMMENT",
  "body": "Review summary: 2 important findings + 1 suggestion. Inline comments below.",
  "comments": [
    {
      "path": "core/analysis/indicator_correlation.py",
      "line": 23,
      "side": "RIGHT",
      "body": "🟠 Important: Unused import\n\nImport of 'generate_macd_signal' is not used.\n\n---\n\nTo fix an unused import without changing behavior, remove only the unused symbol from the import statement and keep the rest intact.\n\nBest fix in this file (`core/analysis/indicator_correlation.py`): update line 23 so it imports only `compute_macd`, and remove `generate_macd_signal` from that line. No other code changes are needed, assuming the symbol is indeed unused throughout the file.\n\n```suggestion\nfrom core.indicators.macd import compute_macd\n```"
    },
    {
      "path": "api/routes/health.py",
      "line": 42,
      "side": "RIGHT",
      "body": "🟠 Important: Division by None\n\n`uptime_seconds` divides by `(now - start_time)` without checking whether `start_time` is set, raising `TypeError` on first startup.\n\n---\n\nGuard the division with a `None` check and return `0` until the service is fully initialized.\n\nBest fix in this file (`api/routes/health.py`): add the guard at line 42 so the function returns `uptime_seconds=0` cleanly when `start_time` is None.\n\nNo new imports, methods, or external dependencies are needed.\n\n```suggestion\nif start_time is None:\n    uptime_seconds = 0\nelse:\n    uptime_seconds = int((now - start_time).total_seconds())\n```"
    }
  ]
}
EOF
```

### Step 2: Post the review

```bash
gh api -X POST repos/{owner}/{repo}/pulls/{pr_number}/reviews --input /tmp/review.json
```

### Parameters

| Parameter | Description |
|-----------|-------------|
| `commit_id` | Commit SHA to comment on (use `git rev-parse HEAD`). |
| `event` | `COMMENT` (leave as comments), `APPROVE`, or `REQUEST_CHANGES`. |
| `body` | Brief 1–3 sentence summary. Keep it short — every detail belongs in an inline comment. |
| `comments[].path` | File path exactly as shown in the diff. |
| `comments[].line` | 1-based line number in the NEW version (right side of diff). |
| `comments[].side` | `RIGHT` for new/added lines, `LEFT` for deleted lines. |
| `comments[].body` | The formatted Markdown described in "Inline Comment Body Format" above. |
| `comments[].start_line` | (Optional) For multi-line suggestion ranges, see below. |

## Multi-Line Suggestion Blocks

For a fix that spans multiple lines, set `start_line` to the first line of the range. **`start_line`/`line` together define the range that will be REPLACED** when the reviewer clicks "Commit suggestion".

```json
{
  "path": "api/routes/health.py",
  "start_line": 41,
  "line": 43,
  "side": "RIGHT",
  "body": "🟠 Important: ...\n\n---\n\n...\n\n```suggestion\nif start_time is None:\n    uptime_seconds = 0\nelse:\n    uptime_seconds = int((now - start_time).total_seconds())\n```"
}
```

## How Suggestions Actually Work (Mandatory Verification)

A ` ```suggestion ``` ` block **replaces** the targeted range with its contents. The replaced range is:

- `line` only → the single line `line` (replaces 1 line).
- `start_line` + `line` → the inclusive range `start_line..line` (replaces `line − start_line + 1` lines).

The suggestion body can be any number of lines — 0 (deletion), 1, or many. It does **not** have to match the range size.

| Intent | `start_line` | `line` | Suggestion body must contain |
|--------|--------------|--------|-------------------------------|
| Change line N | omit | N | the new content for line N |
| Change lines N..M | N | M | the new content for the whole block |
| **Add** a line **after** line N (keep line N) | omit | N | line N's exact current text, then the new line(s) |
| **Add** a line **before** line N (keep line N) | omit | N | the new line(s), then line N's exact current text |
| **Insert** lines inside range N..M (keep N..M) | N | M | every original line in N..M plus the new lines, in the final desired order |
| **Delete** line N | omit | N | empty body (just an empty ` ```suggestion ``` ` block) |
| **Delete** lines N..M | N | M | empty body |

### Common mistakes that silently corrupt code

1. **Duplicated lines.** You copy a neighboring line into the suggestion body as "context" — but that line is still present in the file outside the replaced range, so accepting the suggestion inserts a second copy. Fix: only include lines that fall within the targeted range, plus any genuinely new content.
2. **Disappearing lines.** You target `start_line=10, line=12` to comment on a 3-line block, but your suggestion body only contains 1 line because you "only want to change line 11". Accepting that suggestion deletes lines 10 and 12. Fix: narrow the range to just line 11, or include lines 10 and 12 verbatim in the body.
3. **Description does not match the suggestion.** The prose says "rename this variable" but the suggestion replaces an entire function. Fix: re-read the prose after writing the suggestion and confirm the resulting file matches it line-for-line.

### Mandatory verification before posting

For every inline comment that contains a ` ```suggestion ``` ` block, do this check before adding it to the review JSON:

1. Read the actual file lines that will be replaced: `sed -n '<start_line>,<line>p' <path>` (or `sed -n '<line>p' <path>` for a single-line target).
2. Mentally apply the suggestion: drop those lines, splice in the suggestion body, and look at the result in context.
3. Confirm the resulting code matches **exactly** what your prose description promises — no extra duplicated line above/below, no original line accidentally dropped, no off-by-one.
4. If the change cannot be expressed cleanly as a contiguous replacement (non-adjacent lines, depends on edits elsewhere), do **not** use a suggestion block — describe the change in prose instead.

If you are not 100% sure the suggestion will produce the exact code you described, drop the ` ```suggestion ``` ` block and leave a regular inline comment. A correct prose comment is always better than a one-click suggestion that silently corrupts the file.

## When to Use a Suggestion Block (and When Not To)

Use ` ```suggestion ``` ` for: small concrete changes — renames, typos, type hints, docstrings, 1–5 line refactors, removing a single unused import, adding one guard clause.

Skip ` ```suggestion ``` ` for: large refactors, architectural changes, multi-region fixes, ambiguous improvements, anything that requires context from other parts of the file. Describe the fix in prose and let the human implement it.

## Finding Line Numbers

```bash
# From a diff header: @@ -old_start,old_count +new_start,new_count @@
# Count from new_start for added/modified lines.

grep -n "pattern" filename     # Find the line number
sed -n '40,50p' filename       # Verify the surrounding context
```

## Good vs Bad Inline Comments

### ✅ Good (specific failure mode, file/line anchored, actionable)

```
🟠 Important: JWT signature not verified

The token is decoded without verifying the signature, allowing any forged token to pass authentication.

---

`jwt.decode()` must be called with both the secret key and the allowed `algorithms` list, otherwise signature verification is skipped entirely.

Best fix in this file (`api/auth.py`): pass the secret and the algorithm whitelist to `jwt.decode()` at line 87.

No additional methods, definitions, or external imports are required.

```suggestion
token_data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
```
```

### ❌ Bad (vague, no failure mode, no anchor)

```
This could be improved. Consider refactoring.
```

### ❌ Bad (style nit — belongs to a linter, not a review)

```
Variable should be named `user_id` instead of `uid`.
```

### ❌ Bad (out of scope — skip it)

```
Unrelated to this PR, but the README has a typo on line 12.
```

### ❌ Bad (no suggestion block where one is needed, or one where it isn't)

For a 30-line architectural refactor: do not paste a 30-line ` ```suggestion ``` ` block. Describe the change in prose and let the human do the refactor in a follow-up.

For a one-line unused-import removal: do not skip the suggestion block. The reviewer should be able to apply the fix with one click.

## Edge Cases

### Dependency-only PRs

For PRs that only update `package-lock.json`, `requirements.txt`, or similar:
- Do not flag normal metadata churn (dev/devOptional flags, version bumps).
- Only flag issues that break install, build, or runtime loading.
- Only flag known security vulnerabilities in dependencies.

### Documentation-only PRs

For PRs that only modify `.md` files:
- Check for broken links and incorrect code examples.
- Do not flag typos or grammar unless they change meaning.

### Test-only PRs

For PRs that only add/modify tests:
- Verify the tests actually test what they claim.
- Check for test interdependencies.
- Do not flag test refactoring without functional impact.

## Fallback: curl

If `gh` is unavailable, use curl with the same JSON file:

```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews" \
  -d @/tmp/review.json
```

## Summary Checklist

1. Pre-review checks passed (PR open, scope ok, severity filtered, ≤ 10 findings, severity-ordered).
2. Review data written to `/tmp/review.json` with one entry per finding in `comments[]`.
3. Each `comments[i].body` follows the `## <Priority> <Category>` template.
4. Each suggestion block has been verified by mentally applying it to the file.
5. Post **ONE** review with `gh api --input /tmp/review.json`.
6. If no actionable findings: post a short approval with `"event": "APPROVE"` and **no** `comments[]` entries.
