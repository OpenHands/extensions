# GitHub API Reference

Quick reference for the endpoints, authentication, and rate limits used by
the GitHub Repository Monitor automation.

---

## Authentication

All requests use Bearer authentication:

```
Authorization: Bearer {GITHUB_PERSONAL_ACCESS_TOKEN}
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28
```

---

## Token Types and Required Scopes

### Classic Personal Access Token

| Scope | Grants |
|-------|--------|
| `repo` | Full access to private and public repos (read + write issues/PRs) |
| `public_repo` | Write access to public repos only (sufficient for public repos) |

### Fine-Grained Personal Access Token

| Permission | Level |
|------------|-------|
| Issues | Read and Write |
| Pull requests | Read (optional, for fetching PR metadata) |

### Checking Token Scopes

```bash
curl -I https://api.github.com/user \
  -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
  | grep -i x-oauth-scopes
# X-OAuth-Scopes: repo, public_repo
```

Fine-grained PATs do not return `X-OAuth-Scopes`; the script relies on the
`permissions` field in the repo response instead.

---

## Endpoints Used

### Verify token identity

```
GET /user
```

Returns the authenticated user. Use to verify the token is valid.

---

### Verify repo access and permissions

```
GET /repos/{owner}/{repo}
```

Key fields in the response:

| Field | Type | Description |
|-------|------|-------------|
| `private` | bool | Whether the repo is private |
| `permissions.push` | bool | Token has write access (required for private repos) |
| `permissions.pull` | bool | Token has read access |
| `full_name` | string | `owner/repo` |

Error codes:
- `404` — Repo not found or token has no read access.
- `403` — Token exists but is blocked from this resource.

---

### Poll issue and PR comments

```
GET /repos/{owner}/{repo}/issues/comments
  ?since={ISO 8601 UTC}
  &sort=created
  &direction=asc
  &per_page=100
  &page={n}
```

Returns all comments on issues **and** PRs (PRs are a superset of issues in
GitHub's API). The `since` parameter filters to comments created **at or
after** the given timestamp.

Key fields per comment:

| Field | Description |
|-------|-------------|
| `id` | Integer comment ID (used for deduplication) |
| `body` | Comment text |
| `user.login` | Author username |
| `user.type` | `"User"` or `"Bot"` |
| `created_at` | ISO 8601 UTC creation timestamp |
| `html_url` | Direct link to the comment |
| `issue_url` | API URL of the parent issue/PR (extract number from last path segment) |

---

### Poll PR inline review comments

```
GET /repos/{owner}/{repo}/pulls/comments
  ?since={ISO 8601 UTC}
  &sort=created
  &direction=asc
  &per_page=100
  &page={n}
```

Returns inline review comments on PR diffs.

Key fields per comment:

| Field | Description |
|-------|-------------|
| `id` | Integer comment ID |
| `body` | Comment text |
| `user.login` | Author username |
| `pull_request_url` | API URL of the parent PR (extract number from last path segment) |
| `path` | File path the comment was left on |
| `line` | Line number in the file (nullable) |
| `created_at` | ISO 8601 UTC creation timestamp |

---

### Fetch issue/PR metadata

```
GET /repos/{owner}/{repo}/issues/{issue_number}
```

Works for both issues and pull requests. To distinguish:
- Response contains `pull_request` key → it's a PR.
- No `pull_request` key → it's a regular issue.

Key fields:

| Field | Description |
|-------|-------------|
| `number` | Issue/PR number |
| `title` | Title string |
| `body` | Description text (can be null) |
| `state` | `"open"` or `"closed"` |
| `html_url` | Browser URL |
| `labels[].name` | Label names |
| `pull_request.url` | Present only if this is a PR |

---

### Fetch recent comments for context

```
GET /repos/{owner}/{repo}/issues/{issue_number}/comments
  ?per_page=100
```

Returns all issue/PR comments in chronological order. The script fetches
all pages and takes the last `CONTEXT_COMMENT_LIMIT` (default 10) entries.

---

### Post a comment

```
POST /repos/{owner}/{repo}/issues/{issue_number}/comments

Body: { "body": "comment text (Markdown supported)" }
```

Works for both issues and PRs. Returns the created comment object including
its `id` and `html_url`.

Error codes:
- `403` — Token lacks write permission.
- `404` — Repo or issue not found.
- `410` — Issue is locked; comments are disabled.

---

## Rate Limits

| Tier | Limit | Notes |
|------|-------|-------|
| Authenticated requests | 5,000 / hour | Per token |
| Search API | 30 / minute | Not used by this script |
| Secondary rate limit | Varies | Triggered by rapid POST bursts; unlikely at 1-min polling |

At one poll per minute on a moderately active repo:
- ~2 GET calls per run baseline (user + repo)
- ~1–3 additional GETs per trigger event (issue context + comment history)
- ~1–2 POSTs per trigger event (acknowledgement comment + optional summary)

Typical usage: **< 20 requests/hour** for a quiet repo,
**< 300 requests/hour** for a very active repo (still well within the 5,000 limit).

Check remaining quota with:
```bash
curl -s https://api.github.com/rate_limit \
  -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
core = d['resources']['core']
print(f\"Remaining: {core['remaining']}/{core['limit']}  Reset: {core['reset']}\")
"
```

---

## Common Error Codes

| Code | Meaning | Typical fix |
|------|---------|-------------|
| 401 | Bad credentials / token expired | Rotate token; update the secret |
| 403 | Forbidden (scope missing or repo blocked) | Add required scope; check org SSO |
| 404 | Resource not found or no read access | Check repo name; ensure token has access |
| 410 | Gone (issue locked or deleted) | Harmless — skip this issue |
| 422 | Unprocessable entity (e.g., body too long) | Truncate comment body |
| 429 | Rate limit hit (secondary) | Slow down; add sleep between requests |

---

## Bot Detection

GitHub sets `user.type = "Bot"` for GitHub Apps and some bots. Classic bot
accounts (created as regular users) may instead have logins ending in
`[bot]` (e.g. `dependabot[bot]`). The script skips both patterns to avoid
feedback loops with other automation.
