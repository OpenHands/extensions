---
name: github-pr-reviewer
description: >
  Create an automation that reviews GitHub pull requests when they are opened
  or updated. Inspects the diff, changed files, tests, and existing discussion
  via GitHub MCP, then posts a concise review highlighting risks, security
  issues, missing tests, and next steps.
triggers:
  - /pr-reviewer:setup
---

# GitHub PR Reviewer Automation

Create a cron automation that polls a GitHub repository, reviews each open
pull request exactly once, and posts the AI review as a GitHub comment.
Windows PowerShell equivalents for the setup, packaging, upload, and API-check shell snippets are in `references/windows.md`.

The automation script is fully deterministic: PR discovery, state tracking,
and deduplication are handled in Python. The LLM is only invoked to write
the review text for PRs not yet seen, never for orchestration.

---

## Prerequisites

### Required secret

Verify that the following secret is set in **OpenHands Settings → Secrets**:

| Secret name | Token type | Minimum permissions |
|---|---|---|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Classic PAT | `repo` (private) or `public_repo` (public) |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Fine-grained PAT | Pull requests: Read and Write |

Check with:
```bash
curl -s https://api.github.com/user \
  -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('login') or d.get('message'))"
```

If the token is missing or invalid, inform the user and stop.

---

## Setup Workflow

Follow these steps in order.

### Step 1 — Verify GITHUB_PERSONAL_ACCESS_TOKEN

Run the `curl` check above.

- If absent: *"GITHUB_PERSONAL_ACCESS_TOKEN is not set. Please add it in
  OpenHands Settings → Secrets."* Stop.
- If the API returns `{"message": "Bad credentials"}`: tell the user the
  token is invalid and ask them to update it. Stop.

### Step 2 — Collect repository

Ask: *"Which GitHub repository should be monitored?
(Format: `owner/repo`, e.g. `myorg/backend`)"*

Validate access:
```bash
curl -s "https://api.github.com/repos/{owner}/{repo}" \
  -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
if 'message' in d:
    print('ERROR:', d['message'])
else:
    print(f\"Accessible. Private: {d.get('private')}. Permissions: {d.get('permissions')}\")
"
```

Record `REPO = "{owner}/{repo}"`.

### Step 3 — Collect review tone

Ask: *"What review tone should the reviewer use?
  1. Thorough (default) — comprehensive coverage of correctness, security, tests, style
  2. Concise — high-signal only, skips minor style feedback
  3. Friendly — constructive and encouraging
(Press Enter for Thorough, or type your choice or any custom style description)"*

Map the choice to `REVIEW_TONE`:

| Answer | `REVIEW_TONE` | `REVIEW_STYLE_INSTRUCTIONS` |
|--------|--------------|------------------------------|
| 1 / Enter | `"thorough"` | `""` |
| 2 | `"concise"` | `""` |
| 3 | `"friendly"` | `""` |
| Custom text (e.g. "hostile pirate") | `"thorough"` | the custom text verbatim |

### Step 4 — Collect cron schedule

Ask: *"How often should the automation poll for new PRs?
(Press Enter for the default: every 5 minutes.
Use a cron expression for a different interval, e.g. `0 * * * *` = hourly)"*

Default: `*/5 * * * *`.

Record as `CRON_SCHEDULE`.

### Step 5 — Generate the automation script

Read `scripts/main.py` from this skill's directory. Apply exactly four
constant substitutions near the top of the file:

| Placeholder | Replace with |
|---|---|
| `REPO = "owner/repo"` | `REPO = "{owner_repo}"` |
| `REVIEW_TONE = "thorough"` | `REVIEW_TONE = "{review_tone}"` |
| `REVIEW_STYLE_INSTRUCTIONS = ""` | `REVIEW_STYLE_INSTRUCTIONS = "{style_instructions}"` |
| `DEFAULT_OPENHANDS_URL = "http://localhost:8000"` | leave unchanged unless the user has a preference |

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

### Step 6 — Package and upload

Determine the Automation backend URL and auth from the `<RUNTIME_SERVICES>`
block in your system context:
- **OPENHANDS_HOST**: the Automation backend `url_from_agent`
- **Auth**: `X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY`

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

### Step 7 — Register the automation

```bash
curl -s -X POST "${OPENHANDS_HOST}/api/automation/v1" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"GitHub PR Reviewer: {owner}/{repo}\",
    \"trigger\": {\"type\": \"cron\", \"schedule\": \"{cron_schedule}\"},
    \"tarball_path\": \"$TARBALL_PATH\",
    \"entrypoint\": \"python3 main.py\",
    \"timeout\": 300
  }" | python3 -m json.tool
```

Record the returned `id`.

### Step 8 — Confirm

Tell the user:

> ✅ **GitHub PR Reviewer** is running!
>
> - Automation ID: `{id}`
> - Repository: `{owner}/{repo}`
> - Review tone: `{tone}`
> - Polling schedule: `{cron_schedule}`
> - State file: `~/.openhands/workspaces/automation-state/github_pr_reviewer_{id}.json`
>
> The next cron run will discover all currently open PRs and queue reviews.
> Each PR is reviewed exactly once; state is stored in the JSON file above.
> To force a re-review of all PRs, delete the state file.

---

## Runtime Behaviour (per poll)

Each cron run executes `main.py`, which:

1. **Loads state** from the JSON file (see `references/state-schema.md`).
2. **Resolves and validates `GITHUB_PERSONAL_ACCESS_TOKEN`** — aborts
   immediately if absent or invalid.
3. **Lists all open PRs** in the configured repository.
4. **For each PR not yet in state**:
   - Fetches the unified diff via the GitHub API.
   - Skips PRs whose diff exceeds `MAX_DIFF_LINES_SKIP` (default 5000 lines)
     and posts an explanatory comment.
   - Truncates diffs larger than `MAX_DIFF_LINES` (default 500 lines) and
     notes this in the prompt.
   - Creates an OpenHands conversation with the PR metadata, diff, and
     configured tone instructions as the initial message.
   - Posts an acknowledgement comment on the PR with a link to the conversation.
   - Records the PR in state with `status: "active"`.
5. **For each active conversation**:
   - Skips PRs that have been closed or merged (marks them closed silently).
   - Checks the conversation's `execution_status`.
   - When it reaches `idle`, `finished`, `error`, or `stuck`:
     posts the agent's final response as a GitHub comment and marks the
     conversation `closed`.
6. **Saves updated state** and fires the completion callback.

---

## Additional Resources

- **`references/state-schema.md`** — State JSON schema, field definitions,
  and conversation lifecycle diagram.
- **`scripts/main.py`** — The complete automation script. Customise the
  four constants at the top before packaging.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Bot never posts reviews | `GITHUB_PERSONAL_ACCESS_TOKEN` missing or wrong scopes | Verify token; check Step 1 |
| "Bad credentials" in run logs | Token expired | Rotate and update the secret |
| 404 on repo access | Repo name wrong or no access | Re-check `owner/repo` and token permissions |
| Same PR reviewed twice | State file deleted or corrupted | Check that the state file path is stable across runs |
| Review never posted | Conversation stuck in `running` | Open the conversation in the OpenHands UI |
| PR skipped silently | Diff too large | Raise `MAX_DIFF_LINES_SKIP` in the script or split the PR |
