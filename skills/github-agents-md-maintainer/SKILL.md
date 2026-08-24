---
name: github-agents-md-maintainer
description: >
  Create an automation that keeps AGENTS.md current in one or more GitHub
  repositories. On a schedule - weekly by default - it clones the default
  branch, starts an OpenHands conversation that reads the repository and
  creates or updates AGENTS.md, and opens a pull request with the result.
triggers:
  - /agents-md:setup
---

# AGENTS.md Maintainer Automation

Create a cron automation that keeps each configured repository's `AGENTS.md` -
the file an agent reads first when it starts work there - matching what the
repository actually is. It is created when missing, updated when the repository
has moved on, and left alone when it is still accurate.

The automation script is deterministic: scheduling, the once-per-week claim, the
clone, the branch, the commit, the push, the pull request, and the clone's
removal are all handled in Python. The LLM is invoked only to read the
repository and write the file.

A week is one unit of work per repository, so a cron that fires more often than
intended, a retried run, or a restarted service cannot open the same pull
request twice. **A repository whose previous pull request from this automation
is still open is skipped**, because a second one would edit the same file and
reviewing it would tell you nothing the first did not.

---

## Prerequisites

### Required secret

Verify that the following secret is set in **OpenHands Settings -> Secrets**:

| Secret name | Token type | Minimum permissions |
|---|---|---|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Classic PAT | `repo` |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Fine-grained PAT | Contents: **Read and write**, Metadata: Read, Pull requests: **Read and write** |

Contents write is required because the branch is pushed, and pull request write
because the pull request is opened. No issue permission is needed: this
automation never comments on an issue.

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
- If the API returns `{"message": "Bad credentials"}`: tell the user the token is
  invalid and ask them to update it. Stop.

### Step 2 - Collect repositories

Ask: *"Which GitHub repositories should have their AGENTS.md maintained?
(Format: `owner/repo`, e.g. `myorg/backend`. List several separated by commas.)"*

Validate access to **each** repository, and confirm the token can push:
```bash
curl -s "https://api.github.com/repos/{owner}/{repo}" \
  -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
if 'message' in d:
    print('ERROR:', d['message'])
else:
    print(f\"Accessible. Default branch: {d.get('default_branch')}. Push: {d.get('permissions',{}).get('push')}\")
"
```

Record every accepted repository into `REPOS = ["{owner}/{repo}", ...]`. Each
repository keeps its own state and its own weekly claim, so one falling behind
never blocks another.

### Step 3 - Collect the schedule

Ask: *"How often should AGENTS.md be checked?
(Press Enter for the default: every Monday at 09:00 UTC, `0 9 * * 1`.)"*

Default: `0 9 * * 1`. Record as `CRON_SCHEDULE`, and the timezone as
`CRON_TIMEZONE` (default `UTC`).

A schedule more frequent than weekly is allowed but rarely useful: the work is
keyed by ISO week, so extra runs inside the same week do nothing but poll.

### Step 4 - Collect the pull request mode

Ask: *"Should the pull requests be opened as drafts?
  1. Draft (default) - opened as a draft, ready for a human to mark ready
  2. Ready for review - opened as a normal pull request
(Press Enter for Draft)"*

Map the choice to `DRAFT_PULL_REQUEST` (`True` or `False`).

### Step 5 - Collect the branch prefix

Ask: *"What branch prefix should the automation use?
(Press Enter for the default: `openhands/agents-md`, which produces
`openhands/agents-md-2026-W34`.)"*

Record as `BRANCH_PREFIX`. The prefix is also how the automation recognises its
own open pull requests, so changing it later makes it stop seeing the older ones.

### Step 6 - Confirm the secret scope

The agent is handed `GITHUB_PERSONAL_ACCESS_TOKEN`, because it pushes its branch
and opens the pull request itself. Ask: *"Beyond the GitHub token, does reading
this repository need a secret of its own? (Press Enter for none.)"*

Record the answers appended to the default, as
`AGENT_SECRET_NAMES = ["GITHUB_PERSONAL_ACCESS_TOKEN", "NAME", ...]`. Keep it an
allow-list: the conversation reads a whole repository, so the rest of the
deployment's secrets should stay out of its reach.

### Step 7 - Generate the automation script

Read `scripts/main.py` from this skill's directory. Apply exactly four constant
substitutions near the top of the file:

> The script also reads a `config.json` shipped beside it, if there is one, over
> these constants. That is how the catalog entry
> (`automations/catalog/github-agents-md-maintainer/`) configures an unmodified
> copy, since a declarative host cannot rewrite Python. This setup path
> substitutes the constants and ships no `config.json`, so the two never collide.

| Placeholder | Replace with |
|---|---|
| `REPOS = ["owner/repo"]` | `REPOS = ["{owner_repo}", ...]` - one entry per repository from Step 2 |
| `BRANCH_PREFIX = "openhands/agents-md"` | `BRANCH_PREFIX = "{branch_prefix}"` |
| `DRAFT_PULL_REQUEST = True` | `DRAFT_PULL_REQUEST = {True or False}` |
| `AGENT_SECRET_NAMES: list[str] = ["GITHUB_PERSONAL_ACCESS_TOKEN"]` | the list from Step 6 |

Use a safe string writer such as `json.dumps(value)` when inserting user-provided
repository names or prefixes into Python string literals.

Write the customized script to a temporary build directory and validate it:
```bash
mkdir -p /tmp/agents-md-build
# write the customized main.py to /tmp/agents-md-build/main.py
python3 -m py_compile /tmp/agents-md-build/main.py && echo "Syntax OK"
```

### Step 8 - Package and upload

Determine the Automation backend URL and auth from the `<RUNTIME_SERVICES>`
block in your system context:
- **OPENHANDS_HOST**: the Automation backend `url_from_agent`
- **Auth**: `X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY`

```bash
tar -czf /tmp/agents-md.tar.gz -C /tmp/agents-md-build .

TARBALL_PATH=$(curl -s -X POST \
  "${OPENHANDS_HOST}/api/automation/v1/uploads?name=github-agents-md-maintainer" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/gzip" \
  --data-binary @/tmp/agents-md.tar.gz \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['tarball_path'])")

echo "Uploaded: $TARBALL_PATH"
```

### Step 9 - Register the automation

```bash
curl -s -X POST "${OPENHANDS_HOST}/api/automation/v1" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"AGENTS.md Maintainer: {repo_summary}\",
    \"trigger\": {\"type\": \"cron\", \"schedule\": \"{cron_schedule}\", \"timezone\": \"{cron_timezone}\"},
    \"tarball_path\": \"$TARBALL_PATH\",
    \"entrypoint\": \"python3 main.py\",
    \"timeout\": 900
  }" | python3 -m json.tool
```

Record the returned `id`.

### Step 10 - Confirm

Tell the user:

> ✅ **AGENTS.md Maintainer** is running!
>
> - Automation ID: `{id}`
> - Repositories: `{owner}/{repo}`, ... (one line each)
> - Schedule: `{cron_schedule}` ({cron_timezone})
> - Branch prefix: `{branch_prefix}`
> - Pull requests: `{draft or ready for review}`
> - State file per repository:
>   `~/.openhands/workspaces/automation-state/github_agents_md_{id}_{owner}__{repo}.json`
>
> Each week it reads the repository and proposes an AGENTS.md change, or reports
> that none is needed. While one of its pull requests is still open, it stays
> quiet - merge or close it to get the next one.

---

## Runtime Behaviour (per run)

Each cron run executes `main.py`, which loads `config.json` if the catalog
shipped one, checks that `git` is available, resolves and validates
`GITHUB_PERSONAL_ACCESS_TOKEN` once, then processes every repository in `REPOS`
independently. One repository failing does not stop the others; the run fails
only if every repository fails.

For each repository:

1. Loads that repository's state and reads its default branch.
2. Computes the current ISO week, e.g. `2026-W34`, and stops here if that week
   is already recorded - which is what makes extra runs inside a week harmless.
3. Lists open pull requests whose head branch starts with the branch prefix. If
   any exist, records the skip and moves on.
4. Asks GitHub whether `AGENTS.md` exists on the default branch, which decides
   whether the run is a create or an update, and the pull request's title.
5. Claims the week in state **before** the slow work, so an overlapping run
   cannot start it twice.
6. Picks the first free branch name (`{prefix}-{period}`, else a numbered
   variant), clones the default branch shallow and single-branch into
   `{WORKSPACE_BASE}/agents-md/{owner}__{repo}/{period}`, and creates the branch.
7. Starts an OpenHands conversation with that clone as its working directory,
   and only the secrets named in `AGENT_SECRET_NAMES` attached.
8. When the conversation reaches `idle`, `finished`, `error`, or `stuck`:
   - Adopts the pull request the agent opened, if GitHub says one exists.
   - Records the failure and opens nothing if the conversation errored.
   - Records `no-changes` and opens nothing if there are no commits - the
     expected outcome when `AGENTS.md` is already accurate.
   - Otherwise commits what was left, pushes, and opens the pull request itself.
   - Retries a failed push or pull request on the next two runs before giving up.
9. Removes the clone once the conversation is confirmed stopped.

---

## Additional Resources

- **`references/state-schema.md`** - State JSON schema and the task lifecycle.
- **`scripts/main.py`** - The complete automation script.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Nothing happens for a repository | A pull request from this automation is still open | Merge or close it; the next run proposes the following one |
| Nothing happens after a manual dispatch | The current ISO week is already recorded in state | Wait for the next week, or clear that week's entry from the state document |
| "The token cannot push to ..." | Token lacks Contents: write | Issue a token with write access, or drop the repository from `REPOS` |
| `git is not available in the automation runtime` | The runtime image has no git | Use a runtime image that ships git |
| Pull request says nothing changed | The agent judged AGENTS.md accurate but still committed | Read its summary in the pull request body; tighten the prompt if it keeps making cosmetic edits |
| Every run reports `no-changes` | AGENTS.md is accurate, or the agent cannot read the repository | Open the conversation from the run log and check what it saw |
| Clones remain under `agents-md/` | Their conversations had not stopped yet | They are removed by a later run once the conversation is terminal |
