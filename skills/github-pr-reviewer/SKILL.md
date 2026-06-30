---
name: github-pr-reviewer
description: >
  Create an automation that reviews GitHub pull requests when a configurable
  trigger label is applied. Polls GitHub deterministically, starts one
  OpenHands review conversation per label event, inspects full repository and
  PR context, and posts the final review comment back to GitHub.
triggers:
  - /pr-reviewer:setup
---

# GitHub PR Reviewer Automation

Create a cron automation that watches a GitHub repository for pull requests
with a review trigger label, starts an OpenHands review conversation once per
label event, and posts the AI review as a GitHub comment.

The automation script is deterministic: PR discovery, label-event tracking,
state persistence, stale-result suppression, and GitHub comment posting are
handled in Python. The LLM is invoked only for the review itself.

---

## Prerequisites

### Required secret

Verify that the following secret is set in **OpenHands Settings -> Secrets**:

| Secret name | Token type | Minimum permissions |
|---|---|---|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Classic PAT | `repo` for private repos or `public_repo` for public repos |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Fine-grained PAT | Contents: Read, Metadata: Read, Pull requests: Read, Issues: Read and Write |

Check with any shell-appropriate HTTP client or a short Python script. The
important part is to call `GET https://api.github.com/user` with
`Authorization: Bearer <token>` and inspect either the authenticated login or
an error message.

Example Python snippet:
```python
import json
import urllib.request

token = "<GITHUB_PERSONAL_ACCESS_TOKEN>"
req = urllib.request.Request(
    "https://api.github.com/user",
    headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    },
)
with urllib.request.urlopen(req) as response:
    data = json.load(response)
print(data.get("login") or data.get("message"))
```

If the token is missing or invalid, inform the user and stop.

---

## Setup Workflow

Follow these steps in order.

### Step 1 - Verify `GITHUB_PERSONAL_ACCESS_TOKEN`

Run the check above.

- If absent: *"GITHUB_PERSONAL_ACCESS_TOKEN is not set. Please add it in
  OpenHands Settings -> Secrets."* Stop.
- If the API returns `{"message": "Bad credentials"}`: tell the user the
  token is invalid and ask them to update it. Stop.

### Step 2 - Collect repository

Ask: *"Which GitHub repository should be monitored?
(Format: `owner/repo`, e.g. `myorg/backend`)"*

Validate access with any shell-appropriate HTTP client or Python. The
important part is to call `GET https://api.github.com/repos/{owner}/{repo}`
with the same bearer token and inspect either `message` or `permissions`.

Example Python snippet:
```python
import json
import urllib.request

owner_repo = "{owner}/{repo}"
token = "<GITHUB_PERSONAL_ACCESS_TOKEN>"
req = urllib.request.Request(
    f"https://api.github.com/repos/{owner_repo}",
    headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    },
)
with urllib.request.urlopen(req) as response:
    data = json.load(response)
if "message" in data:
    print("ERROR:", data["message"])
else:
    print(f"Accessible. Private: {data.get('private')}. Permissions: {data.get('permissions')}")
```

Record `REPO = "{owner}/{repo}"`.

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

| Placeholder | Replace with |
|---|---|
| `REPO = "owner/repo"` | `REPO = "{owner_repo}"` |
| `TRIGGER_LABEL = "openhands-review"` | `TRIGGER_LABEL = "{trigger_label}"` |
| `REVIEW_TONE = "thorough"` | `REVIEW_TONE = "{review_tone}"` |
| `REVIEW_STYLE_INSTRUCTIONS = ""` | `REVIEW_STYLE_INSTRUCTIONS = "{style_instructions}"` |
| `DEFAULT_OPENHANDS_URL = "http://localhost:8000"` | leave unchanged unless the user has a preference |

Use a safe string writer such as `json.dumps(value)` when inserting user-provided
repository names, labels, or style instructions into Python string literals.

Write the customized script to a build directory under the system temporary
directory, for example `Path(tempfile.gettempdir()) / "github-pr-reviewer-build" / "main.py"`
in Python. Use the file editor or a short Python helper so the path works on
Windows, macOS, and Linux without leaving temp files in the repository.

Validate syntax before packaging using the current environment's Python
launcher (`python`, `python3`, or `py`):
```text
<python-launcher> -m py_compile <build-dir>/main.py
```

Fix any syntax errors before proceeding.

### Step 7 - Package and upload

Determine the Automation backend URL and auth from the `<RUNTIME_SERVICES>`
block in your system context:
- **OPENHANDS_HOST**: the Automation backend `url_from_agent`
- **Auth**: `X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY`

Prefer the reusable helper script at `scripts/package_upload.py`. It creates
the tarball under the system temporary directory and prints JSON containing the
remote `tarball_path` plus the local tarball path for debugging.

```text
<python-launcher> skills/github-pr-reviewer/scripts/package_upload.py --build-dir <build-dir> --openhands-host <automation-url-from-runtime-services> --upload-name github-pr-reviewer
```

Record the returned `tarball_path` as `TARBALL_PATH`.

### Step 8 - Register the automation

Set `entrypoint` to the same launcher that worked in Step 6 (for example
`python main.py`, `python3 main.py`, or `py -3 main.py`). Then call the
reusable helper script at `scripts/create_automation.py`:

```text
<python-launcher> skills/github-pr-reviewer/scripts/create_automation.py --openhands-host <automation-url-from-runtime-services> --name "GitHub PR Reviewer: {owner}/{repo} label {trigger_label}" --schedule "{cron_schedule}" --tarball-path <TARBALL_PATH> --entrypoint "<python-launcher> main.py" --timeout 300
```

Use shell-appropriate quoting for arguments that contain spaces. Record the
returned `id`.

### Step 9 - Confirm

Tell the user:

> ✅ **GitHub PR Reviewer** is running!
>
> - Automation ID: `{id}`
> - Repository: `{owner}/{repo}`
> - Trigger label: `{trigger_label}`
> - Review tone: `{tone}`
> - Polling schedule: `{cron_schedule}`
> - State file: `~/.openhands/workspaces/automation-state/github_pr_reviewer_label_event_{id}.json`
>
> Apply the `{trigger_label}` label to a pull request to queue a review. Each
> label event is processed once. To request another review, remove and re-apply
> the label.

---

## Runtime Behaviour (per poll)

Each cron run executes `main.py`, which:

1. Loads state from the JSON file (see `references/state-schema.md`).
2. Resolves and validates `GITHUB_PERSONAL_ACCESS_TOKEN` and repository access.
3. Lists open PRs, newest-updated first.
4. For each open PR carrying `TRIGGER_LABEL`:
   - Refetches current PR metadata to avoid acting on stale list data.
   - Finds the latest matching GitHub `labeled` issue event.
   - Skips the event if it has already been tracked.
   - Starts an OpenHands conversation with a review prompt that includes PR
     metadata, the exact head SHA, label event details, and instructions to
     clone the repo, inspect PR discussion, review comments, changed files,
     diff, and surrounding code.
   - Posts an acknowledgement comment with the label event, head SHA, and
     conversation link.
   - Records the label-event review in state with `status: "active"`.
5. For each active review conversation:
   - Marks it closed without posting if the PR has closed or merged.
   - Suppresses stale results if the PR head SHA changed after the review was
     queued.
   - When the conversation reaches `idle`, `finished`, `error`, or `stuck`,
     posts the agent's final response as a GitHub comment and marks the review
     closed.
6. Saves state atomically and fires the completion callback.

---

## Additional Resources

- **`references/state-schema.md`** - State JSON schema, field definitions, and
  review lifecycle diagram.
- **`scripts/main.py`** - The complete automation script. Customize the five
  constants at the top before packaging.
- **`scripts/package_upload.py`** - Packages a prepared build directory, writes
  the tarball to the system temporary directory, and uploads it.
- **`scripts/create_automation.py`** - Registers the automation from the
  uploaded tarball metadata.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Bot never queues reviews | Trigger label not present or no matching `labeled` event | Apply the configured label to the PR |
| "Bad credentials" in run logs | Token expired | Rotate and update `GITHUB_PERSONAL_ACCESS_TOKEN` |
| 404 on repo access | Repo name wrong or no access | Re-check `owner/repo` and token permissions |
| Same PR not reviewed after new commits | Label event was already processed | Remove and re-apply the trigger label |
| Review result never posts | Conversation still running or stuck | Open the conversation link from the acknowledgement comment |
| Stale review suppressed | PR head SHA changed while the agent was reviewing | Re-apply the trigger label after the latest commit |
