# GitHub API Reference

Quick reference for the GitHub REST API endpoints used by the PR reviewer
automation.

---

## Authentication

All requests use a `Bearer` token header:

```
Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28
```

---

## Token Scopes

### Classic Personal Access Token (PAT)

| Scope | Required for |
|---|---|
| `repo` | Read PRs and post comments on **private** repos |
| `public_repo` | Read PRs and post comments on **public** repos |

### Fine-grained PAT

| Permission | Access level | Required for |
|---|---|---|
| Pull requests | Read and Write | Fetch PR data, post review comments |
| Contents | Read | Fetch file diffs (if the diff API is not sufficient) |

---

## Endpoints Used

### List open pull requests

```
GET /repos/{owner}/{repo}/pulls
```

Parameters:

| Parameter | Value | Description |
|---|---|---|
| `state` | `open` | Only return open PRs |
| `sort` | `updated` | Sort by last-updated |
| `direction` | `desc` | Most recently updated first |
| `per_page` | `100` | Maximum per page |
| `page` | `1, 2, …` | Page number for pagination |

Response: array of pull request objects.

Key fields:

| Field | Description |
|---|---|
| `number` | PR number |
| `title` | PR title |
| `body` | PR description (may be `null`) |
| `html_url` | Web URL of the PR |
| `draft` | `true` if the PR is a draft |
| `head.sha` | HEAD commit SHA |
| `head.ref` | Head branch name |
| `base.ref` | Base branch name |
| `labels[].name` | Label names |
| `user.login` | PR author's GitHub login |

---

### Get pull request files (diff)

```
GET /repos/{owner}/{repo}/pulls/{pull_number}/files
```

Response: array of file objects.

Key fields per file:

| Field | Description |
|---|---|
| `filename` | Path of the changed file |
| `status` | `added`, `removed`, `modified`, `renamed`, `copied`, `changed`, `unchanged` |
| `additions` | Number of added lines |
| `deletions` | Number of deleted lines |
| `patch` | Unified diff text (may be absent for large files) |

---

### Get pull request commits

```
GET /repos/{owner}/{repo}/pulls/{pull_number}/commits
```

Response: array of commit objects with `sha`, `commit.message`, `author`.

---

### Post a review comment (via `/github-pr-review` skill)

The review skill uses the Reviews API to post all inline comments in one call:

```
POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews
```

Body:

```json
{
  "commit_id": "{head_sha}",
  "event": "COMMENT",
  "body": "Overall summary.",
  "comments": [
    {
      "path": "src/foo.py",
      "line": 42,
      "side": "RIGHT",
      "body": "Comment text."
    }
  ]
}
```

Use `event: "APPROVE"` or `"REQUEST_CHANGES"` instead of `"COMMENT"` if the
review warrants it.

---

### Post a regular PR comment

```
POST /repos/{owner}/{repo}/issues/{issue_number}/comments
```

(PRs are issues in the GitHub API; use the PR number as `issue_number`.)

Body:

```json
{"body": "Comment text."}
```

---

## Rate Limits

| Token type | Authenticated rate limit |
|---|---|
| Classic / fine-grained PAT | 5 000 requests per hour |

At the default 5-minute poll interval with a moderate number of open PRs,
rate limits are not a practical concern. Each poll run makes roughly
`2 + N` API calls per repo (list PRs + 1 call per new PR to create a
conversation + 1 comment post per new PR).

Check the current rate limit:

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

| HTTP status | Meaning | Fix |
|---|---|---|
| 401 | Invalid or expired token | Rotate the `GITHUB_PERSONAL_ACCESS_TOKEN` secret |
| 403 | Insufficient scopes or rate limit exceeded | Check token scopes; wait for rate limit reset |
| 404 | Repo not found or no access | Verify `owner/repo` spelling; check token has read access |
| 422 | Validation failed (e.g. bad `commit_id`) | Ensure `commit_id` matches the PR's current HEAD SHA |
