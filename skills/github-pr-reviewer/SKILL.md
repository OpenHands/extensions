---
name: github-pr-reviewer
description: >
  Create an automation that reviews GitHub pull requests when they are opened
  or updated. Polls configured repositories on a fixed 5-minute cron schedule,
  detects new or updated PRs, and starts an OpenHands conversation for each
  one that performs a code review and posts it directly back to GitHub.
  Only reviews each unique HEAD commit once — no duplicate reviews on the same
  code. Draft PRs are skipped by default.
triggers:
  - /pr-reviewer-setup
---

# GitHub Code Review Agent  —  Setup

Create a cron automation that polls a set of GitHub repositories every
5 minutes. For each open PR that has not been reviewed at its current HEAD
commit it:

1. Creates an OpenHands conversation that fetches the diff, reviews the
   changes, and posts the review back to GitHub via the `/github-pr-review`
   skill.
2. Posts a "review in progress" comment on the PR with a link to the
   conversation.
3. Records the reviewed HEAD SHA so the same commit is never reviewed twice.
   A new review is triggered automatically when the PR author pushes a new
   commit.

> **Schedule is fixed at `*/5 * * * *`.** Do NOT ask the user for a cron
> schedule and do NOT deviate from this interval.

---

## Prerequisites

### Required secret

The following secret **must** exist in **OpenHands Settings → Secrets**:

| Secret name | Token type | Minimum permissions |
|---|---|---|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Classic PAT | `repo` (private repos) or `public_repo` (public repos) |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Fine-grained PAT | Pull requests: Read and Write |

Verify with:
```bash
curl -s https://api.github.com/user \
  -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('login') or d.get('message'))"
```

If the token is missing, inform the user and stop — the automation cannot
function without GitHub credentials.

### Optional secret

| Secret name | Default | Purpose |
|---|---|---|
| `OPENHANDS_URL` | `http://localhost:8000` | Base URL used to build conversation links in GitHub comments |

---

## Setup Workflow

Follow these steps in order.

### Step 1  —  Verify GITHUB_PERSONAL_ACCESS_TOKEN

Fetch the secret and run the `curl` check above.

- If the secret is absent: tell the user to add it in Settings → Secrets
  (classic PAT with `repo` / `public_repo` scope or a fine-grained PAT with
  "Pull requests: Read and Write"), then stop.
- If the API returns `{"message": "Bad credentials"}`: tell the user the
  token is invalid and ask them to update it, then stop.

### Step 2  —  Collect repositories

Ask the user:
*"Which GitHub repositories should be monitored for code review?
(Format: `owner/repo`, comma-separated for multiple repos.
Example: `myorg/backend, myorg/frontend`)"*

- Validate each repo with a quick `GET /repos/{owner}/{repo}` check using
  the token. Abort with a clear error if any repo is not accessible.
- Record the result as `REPOS` — a list of `"owner/repo"` strings.

### Step 3  —  Collect label filter (optional)

Ask the user:
*"Should the bot only review PRs that carry a specific label?
(Press Enter to review all open PRs, or type a label name, e.g. `needs-review`)"*

- Empty / Enter → `LABEL_FILTER = ""`  (review all open non-draft PRs)
- A label name → `LABEL_FILTER = "<label>"`

### Step 4  —  Collect review tone

Ask the user:
*"What review tone should the bot use?
1. Balanced (default) — constructive and respectful
2. Roasted — frank and unsparing
(Press Enter for balanced)"*

Map the answer:

| Answer | `REVIEW_TONE` |
|---|---|
| 1 / Enter | `"balanced"` |
| 2 | `"roasted"` |

### Step 5  —  Generate the automation script

Read `scripts/main.py` from this skill's directory. Apply exactly four
constant substitutions near the top of the file:

| Placeholder | Replace with |
|---|---|
| `REPOS = ["owner/repo"]` | `REPOS = {repos_python_list}` |
| `LABEL_FILTER = ""` | `LABEL_FILTER = "{label_filter}"` |
| `REVIEW_TONE = "balanced"` | `REVIEW_TONE = "{review_tone}"` |
| `DEFAULT_OPENHANDS_URL = "http://localhost:8000"` | keep default unless the user has overridden `OPENHANDS_URL` |

Write the customised script to a temporary build directory:
```bash
mkdir -p /tmp/pr-reviewer-build
# write the customised main.py to /tmp/pr-reviewer-build/main.py
```

Validate syntax before packaging:
```bash
python3 -m py_compile /tmp/pr-reviewer-build/main.py && echo "Syntax OK"
```

Fix any syntax errors before proceeding.

### Step 6  —  Package and upload

Read the Automation backend URL and auth from `<RUNTIME_SERVICES>`:
- Use the **Automation backend** `url_from_agent` as `OPENHANDS_HOST`
- Auth header: `X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY`

If no Automation backend is listed in `<RUNTIME_SERVICES>`, stop and tell
the user to start the full automation stack.

```bash
tar -czf /tmp/pr-reviewer.tar.gz -C /tmp/pr-reviewer-build .

TARBALL_PATH=$(curl -s -X POST \
  "${OPENHANDS_HOST}/api/automation/v1/uploads?name=github-pr-reviewer" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/gzip" \
  --data-binary @/tmp/pr-reviewer.tar.gz \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['tarball_path'])")

echo "Uploaded: $TARBALL_PATH"
```

### Step 7  —  Create the automation

```bash
REPOS_DISPLAY="{comma-separated repo list}"

curl -s -X POST "${OPENHANDS_HOST}/api/automation/v1" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"GitHub Code Review: ${REPOS_DISPLAY}\",
    \"trigger\": {\"type\": \"cron\", \"schedule\": \"*/5 * * * *\"},
    \"tarball_path\": \"$TARBALL_PATH\",
    \"entrypoint\": \"python3 main.py\",
    \"timeout\": 55
  }" | python3 -m json.tool
```

Record the returned `id`.

### Step 8  —  Confirm

Tell the user:

> ✅ **GitHub Code Review Agent** is running!
>
> - Automation ID: `{id}`
> - Repositories: `{repo list}`
> - Label filter: `{label_filter or "none (reviews all open PRs)"}`
> - Review tone: `{review_tone}`
> - Schedule: every 5 minutes
> - State file: `~/.openhands/workspaces/automation-state/pr_reviewer_{id}.json`
>
> The bot will review each open PR once per HEAD commit. When the PR author
> pushes new commits the bot will review again automatically.
> Draft PRs are skipped.

---

## Runtime Behaviour (per poll)

Each cron run executes `main.py`, which:

1. **Loads state** from the JSON file (see `references/state-schema.md`).
2. **Resolves and validates `GITHUB_PERSONAL_ACCESS_TOKEN`** — aborts
   immediately if absent or invalid.
3. **Polls open PRs** for each configured repo (`GET /repos/{owner}/{repo}/pulls?state=open`).
4. **Filters PRs**:
   - Skips drafts (when `SKIP_DRAFTS = True`).
   - Skips PRs that don't carry `LABEL_FILTER` (when configured).
   - Skips PRs whose HEAD SHA matches the last recorded review.
5. **For each eligible PR**, creates an OpenHands conversation that:
   - Fetches the PR diff via the GitHub API.
   - Reviews the changes for correctness, security, tests, and
     maintainability.
   - Posts the review to GitHub as a single API call using the
     `/github-pr-review` skill.
6. **Posts a GitHub comment** on the PR with a link to the conversation.
7. **Saves state** (reviewed HEAD SHA per PR) and fires the completion
   callback.

---

## Additional Resources

- **`references/state-schema.md`** — State JSON schema and field definitions.
- **`references/github-api.md`** — GitHub API endpoints, token scopes,
  rate limits, and error codes.
- **`scripts/main.py`** — The full automation script.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| No reviews posted | `GITHUB_PERSONAL_ACCESS_TOKEN` missing or wrong scopes | Verify token; check that it has PR read/write permission |
| "Bad credentials" in run logs | Token expired | Rotate token and update the secret in Settings |
| PR skipped with "already reviewed" | Same commit pushed twice | Expected behaviour — push a new commit to re-trigger |
| Draft PR not reviewed | `SKIP_DRAFTS = True` | Mark the PR as "Ready for review" to include it |
| Review conversation created but no GitHub review posted | Agent error inside conversation | Open the conversation in the OpenHands UI for details |
| Same PR reviewed multiple times per run | State file deleted or corrupted | State resets on deletion; harmless but creates duplicate conversations |
