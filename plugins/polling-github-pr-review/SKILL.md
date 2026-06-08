---
name: polling-github-pr-review
description: >
  Deploy a cron automation that polls a GitHub repository every 5 minutes for
  pull requests that have moved to an Open status (newly opened or reopened)
  and automatically starts an OpenHands code review conversation for each one.
  Label filtering is optional. Use when you want automated PR code review
  without needing a publicly reachable webhook endpoint.
triggers:
  - poll github pr review
  - automated pull request code review
  - github pr polling automation
---

# GitHub PR Review Polling Automation

Sets up a cron automation (every 5 minutes) that:

1. Fetches the current set of open pull requests in the configured repository (filtered by label if one is provided).
2. Diffs against the set of open PRs recorded in the previous run to find PRs that have moved to an Open status - this catches both newly created PRs and PRs that were closed and then reopened.
3. Starts a new OpenHands conversation for each such PR to perform a code review using the configured skill.
4. On the first run (detected by the absence of the state file on disk), snapshots the current set of open PRs as a baseline and exits cleanly (no reviews are triggered for pre-existing PRs).

> **Note:** This automation uses polling rather than webhooks, so it works in all deployment modes including local setups without a publicly reachable URL.

---

## Prerequisites

### Required secret

Before deploying, ensure the following secret is set in **OpenHands Settings -> Secrets**:

| Secret name | Token type | Required permissions |
|---|---|---|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Classic PAT | `repo` (private repos) or `public_repo` (public repos) |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Fine-grained PAT | Pull requests: Read and Write |

Verify access:

```bash
curl -s https://api.github.com/user \
  -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('login') or d.get('message'))"
```

If the token is absent or returns `Bad credentials`, inform the user and stop - the automation cannot run without valid GitHub credentials.

---

## Setup Workflow

Follow these steps in order when the user invokes this plugin.

### Step 1 - Ask the user the required questions

Ask all three questions before proceeding to script generation. Collect the answers and then continue.

**Question 1:** *"Which GitHub repository should be monitored for new pull requests? (Format: `owner/repo`, e.g. `myorg/myrepo`)"*

Validate that the repository exists and is accessible:

```bash
curl -s "https://api.github.com/repos/{owner}/{repo}" \
  -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
if 'message' in d:
    print('ERROR:', d['message'])
else:
    print(f\"OK. Private: {d.get('private')}. Permissions: {d.get('permissions', {})}\")
"
```

If `message: Not Found` or `message: Bad credentials`, inform the user and ask them to verify the repo name and token.

Record as `REPO`.

---

**Question 2 (optional):** *"Should the automation only review PRs with a specific label? Enter a label name (e.g. `needs-review`, `ai-review`) or press Enter to review all newly-opened PRs regardless of label."*

If the user provides a label, record it as `LABEL`. If they skip (press Enter or say "no"), set `LABEL` to an empty string `""`.

Record as `LABEL`. Default: `""` (empty - no label filter).

---

**Question 3:** *"What code review skill should be used? Press Enter to use the default: `https://github.com/OpenHands/extensions/tree/main/skills/code-review`"*

If the user provides a URL, use that. Otherwise use the default.

Record as `CODE_REVIEW_SKILL`. Default: `https://github.com/OpenHands/extensions/tree/main/skills/code-review`

---

### Step 2 - Customize the automation script

Read `scripts/main.py` from this plugin's directory. Apply exactly three constant substitutions near the top of the file:

| Placeholder | Replace with |
|---|---|
| `REPO = "owner/repo"` | `REPO = "{user_repo}"` |
| `LABEL = ""` | `LABEL = "{user_label}"` (use `""` if the user skipped the label question) |
| `CODE_REVIEW_SKILL = (...)` the full multi-line string | `CODE_REVIEW_SKILL = "{user_skill_url}"` |

Write the customized script to a temporary build directory:

```bash
mkdir -p /tmp/polling-github-pr-review-build
# (write the customized main.py to /tmp/polling-github-pr-review-build/main.py)
```

Validate Python syntax before packaging:

```bash
python3 -m py_compile /tmp/polling-github-pr-review-build/main.py && echo "Syntax OK"
```

Fix any syntax errors before proceeding.

---

### Step 3 - Show the automation to the user

Present the key automation details to the user and confirm they are ready to deploy:

> **Automation summary:**
>
> - Repository: `{owner}/{repo}`
> - Label filter: `{label}` (or "none - all newly-opened PRs" if LABEL is empty)
> - Detection: PRs that move to Open status (newly created or reopened) since the previous run
> - Code review skill: `{skill_url}`
> - Schedule: every 5 minutes (`*/5 * * * *`)
> - Required secret: `GITHUB_PERSONAL_ACCESS_TOKEN`
> - First run behavior: snapshots current open PRs as baseline, no reviews triggered
>
> Ready to deploy?

Wait for the user to confirm before proceeding.

---

### Step 4 - Package and upload the script

Determine the Automation API host from the system context (`<HOST>` value, or default `https://app.all-hands.dev`):

```bash
OPENHANDS_HOST="https://app.all-hands.dev"   # replace with <HOST> if provided
```

Package and upload:

```bash
tar -czf /tmp/polling-github-pr-review.tar.gz \
  -C /tmp/polling-github-pr-review-build .

TARBALL_PATH=$(curl -s -X POST \
  "${OPENHANDS_HOST}/api/automation/v1/uploads?name=polling-github-pr-review" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/gzip" \
  --data-binary @/tmp/polling-github-pr-review.tar.gz \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['tarball_path'])")

echo "Uploaded tarball: $TARBALL_PATH"
```

If the upload fails with a size error, the tarball must be under 1 MB. The `main.py` script is under 10 KB so this should not occur.

---

### Step 5 - Create the automation

```bash
curl -s -X POST "${OPENHANDS_HOST}/api/automation/v1" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"GitHub PR Review Poller: {owner}/{repo}\",
    \"trigger\": {\"type\": \"cron\", \"schedule\": \"*/5 * * * *\"},
    \"tarball_path\": \"$TARBALL_PATH\",
    \"entrypoint\": \"python3 main.py\",
    \"timeout\": 270
  }" | python3 -m json.tool
```

Record the returned `id`.

---

### Step 6 - Confirm deployment

Tell the user:

> ✅ **GitHub PR Review Poller** is running!
>
> - Automation ID: `{id}`
> - Repository: `{owner}/{repo}`
> - Label filter: `{label}` (or "none - all newly-opened PRs")
> - Detection: PRs that move to Open status since the previous run
> - Code review skill: `{skill_url}`
> - Schedule: every 5 minutes (`*/5 * * * *`)
> - Required secret: `GITHUB_PERSONAL_ACCESS_TOKEN`
> - State file: `{workspace}/automation-state/github_pr_poller_{id}.json`
>
> **First run:** The automation will snapshot the current set of open PRs as a baseline and exit without triggering any reviews. Reviews will begin on the second run (approximately 5 minutes later).
>
> To test, open a new pull request in `{owner}/{repo}` (with the `{label}` label if configured). The automation will pick it up within 5 minutes.

---

## Runtime Behaviour (per poll)

Each cron run executes `main.py`, which:

1. **Reads state** from `automation-state/github_pr_poller_{id}.json`.
2. **Fetches the `GITHUB_PERSONAL_ACCESS_TOKEN` secret** from the agent server. Exits with `FAILED` status if absent or invalid.
3. **Fetches currently open PRs** from the GitHub API. If `LABEL` is set, filters by that label using `/issues?state=open&labels={LABEL}`; otherwise fetches all open PRs via `/pulls?state=open`. Both paths paginate to collect all results.
4. **First run guard:** if the state file does not exist on disk, saves the current open PR numbers as the baseline and exits with code 0 (no reviews triggered). The state file's existence — not its contents — is the source of truth for whether this is a first run.
5. **Set diff:** compares the current open PR numbers against the stored `open_pr_numbers`. PRs present in the current set but not in the stored set have "moved to Open" (newly opened or reopened).
6. **For each PR that moved to Open**, calls `POST /api/conversations` on the agent server to create a new OpenHands conversation. The conversation prompt includes:
   - PR number, title, URL, labels, and description
   - An instruction to load and apply the code review skill at `CODE_REVIEW_SKILL`
7. **Updates state**: saves the current open PR numbers as the new `open_pr_numbers` snapshot.
8. **Fires the completion callback** (`COMPLETED` on success, `FAILED` on unrecoverable errors).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| No reviews triggered after 10+ minutes | `GITHUB_PERSONAL_ACCESS_TOKEN` missing or invalid | Verify the secret is set; test with `curl /user` |
| `Not Found` from GitHub API | Wrong repo name or token has no access | Re-check `owner/repo` spelling; ensure the PAT has `repo` or `public_repo` scope |
| Automation runs but no new reviews | All current open PRs were in the previous snapshot | Expected behavior; only PRs that move to Open since the last run are reviewed |
| A reopened PR was not reviewed | PR was reopened and closed again within a single 5-minute interval | Polling gap - unavoidable with this approach; reduce cron interval if needed |
| All PRs reviewed on first non-baseline run | State file was deleted between runs | Delete the state file again to re-snapshot baseline; the next run will treat all current open PRs as baseline |
| State file path | Debug state location | `{WORKSPACE_BASE}/automation-state/github_pr_poller_{automation_id}.json` |
