---
name: github-pr-reviewer
description: >
  Create an automation that reviews GitHub pull requests when a configurable
  trigger label is applied. Polls one or more repositories deterministically,
  starts one OpenHands review conversation per label event with the pull
  request's head commit already checked out, and publishes the review to GitHub.
triggers:
  - /pr-reviewer:setup
---

# GitHub PR Reviewer Automation

Create a cron automation that watches one or more GitHub repositories for pull
requests with a review trigger label, starts an OpenHands review conversation
once per label event, and publishes the AI review to GitHub.
Windows PowerShell equivalents for the setup, packaging, upload, and API-check shell snippets are in `references/windows.md`.

The automation script is deterministic: PR discovery, label-event tracking,
state persistence, stale-result suppression, the repository checkout, and its
removal are all handled in Python. The LLM is invoked only for the review
itself.

The script prepares each review's workspace before the agent starts: the pull
request's head commit is downloaded as a tarball and extracted to a directory of
its own, which becomes the conversation's working directory. The agent is told
not to clone, fetch, check out, or delete anything, and the script removes the
checkout once the conversation has stopped. Nothing accumulates between runs.

---

## Prerequisites

### Required secret

Verify that the following secret is set in **OpenHands Settings -> Secrets**:

| Secret name | Token type | Minimum permissions |
|---|---|---|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Classic PAT | `repo` for private repos or `public_repo` for public repos |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Fine-grained PAT | Contents: Read, Metadata: Read, Pull requests: **Read and Write**, Issues: Read and Write |

Pull-request **write** access is required because the agent publishes a pull
request review, not just an issue comment. A token with only Pull requests: Read
will poll happily and then fail at the point of publishing.

When several repositories are monitored, the token must cover all of them.

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

### Step 1 - Verify `GITHUB_PERSONAL_ACCESS_TOKEN`

Run the `curl` check above.

- If absent: *"GITHUB_PERSONAL_ACCESS_TOKEN is not set. Please add it in
  OpenHands Settings -> Secrets."* Stop.
- If the API returns `{"message": "Bad credentials"}`: tell the user the
  token is invalid and ask them to update it. Stop.

### Step 2 - Collect repositories

Ask: *"Which GitHub repositories should be monitored?
(Format: `owner/repo`, e.g. `myorg/backend`. List several separated by commas to
review them all from one automation.)"*

Validate access to **each** repository:
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

Record every accepted repository into `REPOS = ["{owner}/{repo}", ...]`. If one
repository fails the check, say which and ask whether to continue without it.

Each repository is polled independently and keeps its own state, so pull-request
numbers never collide between them. The trigger label, tone, and schedule are
shared by all of them; a repository needing different settings wants its own
automation.

### Step 3 - Collect trigger label

Ask: *"Which PR label should trigger a review?
(Press Enter for the default: `openhands-review`.)"*

Record the answer as `TRIGGER_LABEL`. If the label does not exist yet, tell the
user that GitHub will still record the event once the label is created and
applied to a PR.

The automation reviews a PR when it sees the latest matching `labeled` event for
that label. To request another review later, remove and re-apply the label.

### Step 4 - Collect review tone

Ask: *"What review tone should the reviewer use?
  1. Thorough (default) - comprehensive coverage of correctness, security, tests, style
  2. Concise - high-signal only, skips minor style feedback
  3. Friendly - constructive and encouraging
(Press Enter for Thorough, or type your choice or any custom style description)"*

Map the choice to `REVIEW_TONE`:

| Answer | `REVIEW_TONE` | `REVIEW_STYLE_INSTRUCTIONS` |
|---|---|---|
| 1 / Enter | `"thorough"` | `""` |
| 2 | `"concise"` | `""` |
| 3 | `"friendly"` | `""` |
| Custom text, e.g. `strict but kind` | `"thorough"` | the custom text verbatim |

### Step 5 - Collect cron schedule

Ask: *"How often should the automation poll for labeled PRs?
(Press Enter for the default: every 5 minutes.
Use a cron expression for a different interval, e.g. `0 * * * *` = hourly)"*

Default: `*/5 * * * *`.

Record as `CRON_SCHEDULE`.

### Step 6 - Generate the automation script

Read `scripts/main.py` from this skill's directory. Apply exactly five constant
substitutions near the top of the file:

> The script also reads a `config.json` shipped beside it, if there is one, over
> these constants. That is how the catalog entry
> (`automations/catalog/github-pr-reviewer/`) configures an unmodified copy,
> since a declarative host cannot rewrite Python. This setup path substitutes the
> constants and ships no `config.json`, so the two never collide.

| Placeholder | Replace with |
|---|---|
| `REPOS = ["owner/repo"]` | `REPOS = ["{owner_repo}", ...]` - one entry per repository collected in Step 2 |
| `TRIGGER_LABEL = "openhands-review"` | `TRIGGER_LABEL = "{trigger_label}"` |
| `REVIEW_TONE = "thorough"` | `REVIEW_TONE = "{review_tone}"` |
| `REVIEW_STYLE_INSTRUCTIONS = ""` | `REVIEW_STYLE_INSTRUCTIONS = "{style_instructions}"` |
| `DEFAULT_OPENHANDS_URL = "http://localhost:8000"` | leave unchanged unless the user has a preference |

Use a safe string writer such as `json.dumps(value)` when inserting user-provided
repository names, labels, or style instructions into Python string literals.
`json.dumps(list_of_repos)` produces the whole `REPOS` list safely in one step.

Write the customized script to a temporary build directory:
```bash
mkdir -p /tmp/pr-reviewer-build
# write the customized main.py to /tmp/pr-reviewer-build/main.py
```

Validate syntax before packaging:
```bash
python3 -m py_compile /tmp/pr-reviewer-build/main.py && echo "Syntax OK"
```

Fix any syntax errors before proceeding.

### Step 7 - Package and upload

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

### Step 8 - Register the automation

```bash
curl -s -X POST "${OPENHANDS_HOST}/api/automation/v1" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"GitHub PR Reviewer: {repo_summary} label {trigger_label}\",
    \"trigger\": {\"type\": \"cron\", \"schedule\": \"{cron_schedule}\"},
    \"tarball_path\": \"$TARBALL_PATH\",
    \"entrypoint\": \"python3 main.py\",
    \"timeout\": 600
  }" | python3 -m json.tool
```

Use the single repository as `{repo_summary}` when there is one, and something
like `3 repos` when there are several. A poll now downloads a tarball per queued
review, so the timeout allows for that; a run never waits for a review to
finish, only for it to be started.

Record the returned `id`.

### Step 9 - Confirm

Tell the user:

> ✅ **GitHub PR Reviewer** is running!
>
> - Automation ID: `{id}`
> - Repositories: `{owner}/{repo}`, ... (one line each)
> - Trigger label: `{trigger_label}`
> - Review tone: `{tone}`
> - Polling schedule: `{cron_schedule}`
> - State file per repository:
>   `~/.openhands/workspaces/automation-state/github_pr_reviewer_label_event_{id}_{owner}__{repo}.json`
>
> Apply the `{trigger_label}` label to a pull request to queue a review. Each
> label event is processed once. To request another review, remove and re-apply
> the label.
>
> The review is published as a pull request review on the head commit, with
> inline comments where a finding maps to a changed line.

---

## Runtime Behaviour (per poll)

Each cron run executes `main.py`, which resolves and validates
`GITHUB_PERSONAL_ACCESS_TOKEN` once, then processes every repository in `REPOS`
independently. One repository failing does not stop the others; the run fails
only if every repository fails.

For each repository:

1. Loads that repository's state (see `references/state-schema.md`).
2. Verifies repository access.
3. Lists open PRs, newest-updated first.
4. For each open PR carrying `TRIGGER_LABEL`:
   - Refetches current PR metadata to avoid acting on stale list data.
   - Finds the latest matching GitHub `labeled` issue event.
   - Skips the event if it has already been tracked.
   - Downloads the PR's head commit as a tarball and extracts it to
     `{WORKSPACE_BASE}/repositories/{owner}__{repo}/pr-{number}-{sha12}`. The
     archive is checked as it is unpacked: a single root, no absolute or `..`
     paths, and symlinks skipped rather than materialised.
   - Starts an OpenHands conversation **whose working directory is that
     checkout**, with a review prompt carrying PR metadata, the exact head SHA,
     and label event details.
   - Posts an acknowledgement comment with the label event, head SHA, and
     conversation link.
   - Records the review in state with `status: "active"` and the checkout path.
   - If the checkout or the conversation cannot be created, the checkout is
     removed and nothing is recorded, so the next poll retries the label event.
5. For each active review conversation:
   - Marks it closed without posting if the PR has closed or merged.
   - Suppresses stale results if the PR head SHA changed after the review was
     queued.
   - When the conversation reaches `idle`, `finished`, `error`, or `stuck`,
     asks GitHub whether a review by the token's own user exists for that head
     SHA. If it does, the review is complete. If it does not, the agent's final
     response is posted as a comment so the work is not lost.
   - Abandons a conversation that has not reached a terminal status within two
     hours, so its checkout can be reclaimed.
6. Removes the checkout of every finished review, but only after confirming the
   conversation has stopped - deleting it under a running agent would remove its
   working directory. When that cannot be confirmed the directory is left alone
   and the next poll tries again.
7. Saves that repository's state atomically.

The completion callback fires once for the whole run.

---

## Additional Resources

- **`references/state-schema.md`** - State JSON schema, field definitions, and
  review lifecycle diagram.
- **`scripts/main.py`** - The complete automation script. Customize the five
  constants at the top before packaging.
- **`tests/test_main.py`** - Unit tests for the checkout, its removal, and state
  handling. Run them from the skill root with `python -m pytest tests/` after
  editing the script.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Bot never queues reviews | Trigger label not present or no matching `labeled` event | Apply the configured label to the PR |
| "Bad credentials" in run logs | Token expired | Rotate and update `GITHUB_PERSONAL_ACCESS_TOKEN` |
| 404 on repo access | Repo name wrong or no access | Re-check the entry in `REPOS` and the token's permissions |
| One repository is skipped, others work | That repository failed its access check | Read the `=== owner/repo ===` block in the run log |
| Same PR not reviewed after new commits | Label event was already processed | Remove and re-apply the trigger label |
| Review result never posts | Conversation still running or stuck | Open the conversation link from the acknowledgement comment |
| Stale review suppressed | PR head SHA changed while the agent was reviewing | Re-apply the trigger label after the latest commit |
| Review arrives as a plain comment, not a review | Publishing failed, so the script posted the text as a fallback | Check that the token has Pull requests: Read and Write |
| Agent reports it cannot clone the repo | Prompt asked it not to; the workspace is already the checkout | No action - the code is at the head SHA in its working directory |
| Checkouts remain under `repositories/` | Their conversations had not stopped yet | They are removed by a later poll once the conversation is terminal |
