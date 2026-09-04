---
name: gitlab-issue-to-mr
description: >
  Create an automation that implements GitLab issues when a configurable
  trigger label is applied. Polls one or more projects deterministically,
  clones the default branch, starts one OpenHands conversation per label event,
  then commits, pushes, and opens the merge request itself.
triggers:
  - /issue-to-mr:setup
---

# GitLab Issue to MR Automation

Create a cron automation that watches one or more GitLab projects for issues
with a trigger label, starts an OpenHands conversation once per label event with
the project's default branch already checked out, and opens a merge request with
whatever the agent produced.

The automation script is deterministic: issue discovery, label-event tracking,
state persistence, the clone, the branch, the commit, the push, the merge
request, the issue comments, and the clone's removal are all handled in Python.
The LLM is invoked only to write the code.

The agent is told **which** issue to implement, not what it says. It fetches the
description, the discussion, and whatever they link to itself, so nothing in the
prompt goes stale between dispatch and the moment the agent reads it.

That needs read access, so the conversation is handed one secret, `GITLAB_TOKEN`.
`AGENT_SECRET_NAMES` stays an allow-list: the rest of the deployment's secret
store is not reachable from a conversation whose instructions came from an issue.

The deployment's MCP servers are forwarded whole, matching `github-pr-reviewer`,
so a connected GitLab server gives the agent typed tools rather than curl. What
those servers reach is reachable from an issue-authored prompt, so connect only
servers that may be driven by untrusted text.

The agent also finishes the job: it commits, pushes its branch, and opens the
merge request, so the merge request appears when the agent stops rather than on
the next poll. The script does not trust that it happened - when the conversation
ends it asks GitLab whether the merge request exists, and opens it itself when it
does not. `origin` still carries no credential, so every GitLab command the agent
runs has to name `GITLAB_TOKEN`; the SDK only puts a secret in the environment of
a command that mentions it, and masks it in the output.

---

## Prerequisites

### Required secret

Verify that the following secret is set in **OpenHands Settings -> Secrets**:

| Secret name | Token type | Minimum requirements |
|---|---|---|
| `GITLAB_TOKEN` | Personal access token | `api` scope, and at least the **Developer** role on every watched project |
| `GITLAB_TOKEN` | Project or group access token | `api` scope, role **Developer** or above |

The `api` scope is what GitLab grants read and write on issues, notes, branches,
and merge requests through one scope; `read_api` polls happily and then fails at
the point of pushing. Developer is the lowest role that can push a branch and
open a merge request.

Two things the role does not cover, and which fail the push rather than the poll:

- **Protected branches.** The default branch is usually protected, but the
  automation never pushes to it. Protect the branch prefix as well and the push
  is rejected; leave `openhands/issue-*` unprotected.
- **CI/CD files.** An issue asking for a pipeline change makes the agent touch
  `.gitlab-ci.yml`. That needs no extra scope, but a project with a protected
  CI/CD configuration path rejects the push.

When several projects are monitored, the token must cover all of them.

Check with:
```bash
curl -s "https://gitlab.com/api/v4/user" \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('username') or d.get('message'))"
```

If the token is missing or invalid, inform the user and stop.

---

## Setup Workflow

Follow these steps in order.

### Step 1 - Verify `GITLAB_TOKEN`

Run the `curl` check above, against the user's instance if it is not
`gitlab.com`.

- If absent: *"GITLAB_TOKEN is not set. Please add it in OpenHands Settings ->
  Secrets."* Stop.
- If the API returns `{"message": "401 Unauthorized"}`: tell the user the token
  is invalid and ask them to update it. Stop.

### Step 2 - Collect the GitLab API URL

Ask: *"Which GitLab instance? (Press Enter for gitlab.com. For a self-managed
instance give its API root, e.g. `https://gitlab.example.com/api/v4`.)"*

Record as `GITLAB_API_URL`. Default: `https://gitlab.com/api/v4`. Use this URL in
every check below.

### Step 3 - Collect projects

Ask: *"Which GitLab projects should be watched?
(Format: `group/project`, e.g. `myorg/backend`. Subgroups are fine -
`myorg/team/service`. List several separated by commas to serve them all from one
automation.)"*

Validate access to **each** project, and confirm the token's role:
```bash
PROJECT_ID=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "{group}/{project}")
curl -s "${GITLAB_API_URL}/projects/${PROJECT_ID}" \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
if 'message' in d or 'error' in d:
    print('ERROR:', d.get('message') or d.get('error'))
else:
    perms = d.get('permissions') or {}
    levels = [(perms.get(k) or {}).get('access_level') for k in ('project_access', 'group_access')]
    levels = [n for n in levels if isinstance(n, int)]
    role = max(levels) if levels else 'unknown'
    print(f\"Accessible. Default branch: {d.get('default_branch')}. Access level: {role}\")
"
```

Record every accepted project into `PROJECTS = ["{group}/{project}", ...]`. If
one project fails the check, say which and ask whether to continue without it.
An access level below `30` (Developer) means the automation cannot open merge
requests there; ask for a token with a higher role.

Each project is polled independently and keeps its own state, so issue numbers
never collide between them. The trigger label, branch prefix, and schedule are
shared; a project needing different settings wants its own automation.

### Step 4 - Collect trigger label

Ask: *"Which issue label should trigger an implementation?
(Press Enter for the default: `openhands`.)"*

Record the answer as `TRIGGER_LABEL`. If the label does not exist yet, tell the
user that GitLab will still record the event once the label is created and
applied to an issue.

The automation works an issue when it sees the latest matching label event for
that label. To ask for another attempt later, remove and re-apply the label -
that opens a second branch and a second merge request rather than overwriting the
first.

### Step 5 - Collect the merge request mode

Ask: *"Should the merge requests be opened as drafts?
  1. Draft (default) - title prefixed `Draft:`, ready for a human to mark ready
  2. Ready for review - opened as a normal merge request
(Press Enter for Draft)"*

Map the choice to `DRAFT_MERGE_REQUEST` (`True` or `False`). GitLab has no draft
flag on the merge request API; a draft is a title carrying the `Draft: ` prefix,
which the script adds.

### Step 6 - Collect the branch prefix

Ask: *"What branch prefix should the automation use?
(Press Enter for the default: `openhands/issue`, which produces
`openhands/issue-42`.)"*

Record as `BRANCH_PREFIX`. Keep it free of spaces and of characters git rejects
in a ref name, and make sure the prefix is not covered by a protected-branch
rule.

### Step 7 - Collect cron schedule

Ask: *"How often should the automation poll for labelled issues?
(Press Enter for the default: every 5 minutes.
Use a cron expression for a different interval, e.g. `0 * * * *` = hourly)"*

Default: `*/5 * * * *`.

Record as `CRON_SCHEDULE`.

### Step 8 - Confirm the secret scope

The agent is handed `GITLAB_TOKEN`, because it reads the issue and its discussion
itself. Ask: *"Beyond the GitLab token, does the project's build need a secret of
its own - a package registry token, for example? (Press Enter for none.)"*

Record the answers appended to the default, as
`AGENT_SECRET_NAMES = ["GITLAB_TOKEN", "NAME", ...]`.

Keep it an allow-list. Forwarding the whole secret store would put every
credential in the deployment behind a prompt written by whoever opened the issue.
If the projects are public and you would rather the conversation held no
credential at all, set the list to `[]` - the agent can still read a public issue
unauthenticated, and private projects then stop working.

The deployment's MCP servers are a separate matter: they are forwarded whole, so
the conversation can reach everything they expose. Say so, and check the user is
willing to have those servers driven by text written by whoever opened an issue.
Removing a server from the deployment's MCP settings is the only way to keep it
out of these conversations.

### Step 9 - Generate the automation script

Read `scripts/main.py` from this skill's directory. Apply exactly six constant
substitutions near the top of the file:

> The script also reads a `config.json` shipped beside it, if there is one, over
> these constants. That is how the catalog entry
> (`automations/catalog/gitlab-issue-to-mr/`) configures an unmodified copy,
> since a declarative host cannot rewrite Python. This setup path substitutes the
> constants and ships no `config.json`, so the two never collide.

| Placeholder | Replace with |
|---|---|
| `PROJECTS = ["group/project"]` | `PROJECTS = ["{group_project}", ...]` - one entry per project collected in Step 3 |
| `TRIGGER_LABEL = "openhands"` | `TRIGGER_LABEL = "{trigger_label}"` |
| `BRANCH_PREFIX = "openhands/issue"` | `BRANCH_PREFIX = "{branch_prefix}"` |
| `DRAFT_MERGE_REQUEST = True` | `DRAFT_MERGE_REQUEST = {True or False}` |
| `GITLAB_API_URL = "https://gitlab.com/api/v4"` | `GITLAB_API_URL = "{gitlab_api_url}"` |
| `AGENT_SECRET_NAMES: list[str] = ["GITLAB_TOKEN"]` | `AGENT_SECRET_NAMES: list[str] = ["{name}", ...]` |

Leave `MAX_NEW_PER_RUN` and `DEFAULT_OPENHANDS_URL` alone unless the user asks
for a different cap or a non-default OpenHands URL.

A project may be given as `group/project`, as a clone URL, or as an SSH remote;
the script normalizes each one at startup and names the value it could not read
rather than blaming the token. Subgroups are preserved.

Use a safe string writer such as `json.dumps(value)` when inserting user-provided
project paths, labels, or prefixes into Python string literals.
`json.dumps(list_of_projects)` produces the whole `PROJECTS` list safely in one
step.

Write the customized script to a temporary build directory:
```bash
mkdir -p /tmp/issue-to-mr-build
# write the customized main.py to /tmp/issue-to-mr-build/main.py
```

Validate syntax before packaging:
```bash
python3 -m py_compile /tmp/issue-to-mr-build/main.py && echo "Syntax OK"
```

Fix any syntax errors before proceeding.

### Step 10 - Package and upload

Determine the Automation backend URL and auth from the `<RUNTIME_SERVICES>`
block in your system context:
- **OPENHANDS_HOST**: the Automation backend `url_from_agent`
- **Auth**: `X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY`

```bash
tar -czf /tmp/issue-to-mr.tar.gz -C /tmp/issue-to-mr-build .

TARBALL_PATH=$(curl -s -X POST \
  "${OPENHANDS_HOST}/api/automation/v1/uploads?name=gitlab-issue-to-mr" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/gzip" \
  --data-binary @/tmp/issue-to-mr.tar.gz \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['tarball_path'])")

echo "Uploaded: $TARBALL_PATH"
```

### Step 11 - Register the automation

```bash
curl -s -X POST "${OPENHANDS_HOST}/api/automation/v1" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"GitLab Issue to MR: {project_summary} label {trigger_label}\",
    \"trigger\": {\"type\": \"cron\", \"schedule\": \"{cron_schedule}\"},
    \"tarball_path\": \"$TARBALL_PATH\",
    \"entrypoint\": \"python3 main.py\",
    \"timeout\": 900
  }" | python3 -m json.tool
```

Use the single project as `{project_summary}` when there is one, and something
like `3 projects` when there are several. A poll clones a project per queued
issue and pushes finished branches, so the timeout allows for that; a run never
waits for an agent to finish, only for it to be started.

Record the returned `id`.

### Step 12 - Confirm

Tell the user:

> ✅ **GitLab Issue to MR** is running!
>
> - Automation ID: `{id}`
> - Projects: `{group}/{project}`, ... (one line each)
> - GitLab API: `{gitlab_api_url}`
> - Trigger label: `{trigger_label}`
> - Branch prefix: `{branch_prefix}`
> - Merge requests: `{draft or ready for review}`
> - Polling schedule: `{cron_schedule}`
> - State file per project:
>   `~/.openhands/workspaces/automation-state/gitlab_issue_to_mr_{id}_{group}__{project}.json`
>
> Apply the `{trigger_label}` label to an issue to queue an implementation. Each
> label event is processed once. To ask for another attempt, remove and re-apply
> the label - that opens a second branch and merge request.
>
> The agent runs without a checkout credential; the automation pushes the branch
> and opens the merge request once the agent has stopped.

---

## Runtime Behaviour (per poll)

Each cron run executes `main.py`, which loads `config.json` if the catalog
shipped one, checks that `git` is available, resolves and validates `GITLAB_TOKEN`
once, then processes every project in `PROJECTS` independently. One project
failing does not stop the others; the run fails only if every project fails.

For each project:

1. Loads that project's state (see `references/state-schema.md`) and reads its
   default branch and clone URL.
2. Lists open issues carrying `TRIGGER_LABEL`, newest-updated first. GitLab keeps
   merge requests on their own endpoint, so labelling a merge request never
   queues an implementation.
3. For each labelled issue, up to `MAX_NEW_PER_RUN` new ones per run:
   - Refetches the issue so a label removed since the listing does not start work.
   - Finds the latest matching resource label event with `action: "add"`, and
     skips it if that event has already been tracked.
   - Picks the first free branch name, `{BRANCH_PREFIX}-{iid}` or a numbered
     variant of it.
   - Clones the default branch, shallow and single-branch, into
     `{WORKSPACE_BASE}/issue-to-mr/{group}__{project}/issue-{iid}-{event_id}`,
     sets the commit identity, and creates the branch. `origin` keeps its plain
     HTTPS URL, so the workspace holds no credential.
   - Starts an OpenHands conversation **whose working directory is that clone**,
     told which issue to read, with the secrets named in `AGENT_SECRET_NAMES`
     and the deployment's MCP servers attached.
   - Comments on the issue with the branch, the label event, and the conversation
     link.
   - Records the task with `status: "active"`.
   - If the clone or the conversation cannot be created, the clone is removed and
     nothing is recorded, so the next poll retries the label event.
4. For each active task:
   - Abandons a conversation that has not reached a terminal status within two
     hours, comments on the issue, and reclaims its clone.
   - When the conversation reaches `idle`, `finished`, `error`, or `stuck`:
     - Adopts the merge request the agent opened, if GitLab says one exists for
       the branch, and comments its link on the issue. Everything below is the
       path taken when it does not.
     - Skips the merge request if the issue was closed meanwhile.
     - Reports the problem on the issue if the conversation ended in `error` or
       `stuck`.
     - Commits whatever the agent left uncommitted, on top of any commits it made
       itself.
     - Posts the agent's answer on the issue, and opens no merge request, when
       there are no commits at all - that is how an agent reports an issue too
       ambiguous to implement.
     - Otherwise pushes the branch, opens the merge request (draft by default,
       titled `Draft: [#42] <issue title>`, with the agent's summary and
       `Closes #42` in the description), and comments the link on the issue.
     - A push or merge request that fails is retried on the next two polls before
       the task is reported as failed, so a transient GitLab error does not throw
       the work away.
5. Removes the clone of every finished task, but only after confirming the
   conversation has stopped - deleting it under a running agent would remove its
   working directory. When that cannot be confirmed the directory is left alone
   and the next poll tries again.
6. Saves that project's state atomically.

The completion callback fires once for the whole run.

---

## Additional Resources

- **`references/state-schema.md`** - State JSON schema, field definitions, and the
  task lifecycle.
- **`scripts/main.py`** - The complete automation script. Customize the six
  constants at the top before packaging.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Nothing is ever queued | Trigger label not present, or applied to a merge request rather than an issue | Apply the configured label to an issue |
| "401 Unauthorized" in run logs | Token expired | Rotate and update `GITLAB_TOKEN` |
| "The token's role on ... is below Developer" | The token has Reporter or Guest on that project | Grant Developer or above, or drop the project from `PROJECTS` |
| Push rejected: "You are not allowed to push code to protected branches" | The branch prefix is covered by a protected-branch rule | Leave `{BRANCH_PREFIX}-*` unprotected |
| Push rejected on `.gitlab-ci.yml` | The project protects its CI/CD configuration path | Allow the token's role to update it, or exclude such issues |
| 404 on project access | Project path wrong, or no access | Re-check the entry in `PROJECTS` and the token's role. Subgroups must be included in full |
| `git is not available in the automation runtime` | The runtime image has no git | Use a runtime image that ships git; the script clones, commits, and pushes with it |
| Issue commented "did not change any code" | The agent judged the issue too ambiguous, or made no edits | Read its answer in the comment, add the missing detail to the issue, then re-apply the label |
| Same issue not picked up again after new comments | Its label event was already processed | Remove and re-apply the trigger label |
| Agent reports it cannot push or open an MR | By design - it has no push credentials in `origin` | No action; the automation pushes and opens the merge request after the agent stops |
| `Warning: could not fetch MCP config` in run logs | The settings endpoint was unreachable | Non-fatal; the agent falls back to the REST calls in the prompt |
| A backlog of labelled issues starts slowly | `MAX_NEW_PER_RUN` caps how many conversations one poll starts | Wait for the next polls, or raise the cap in the script |
| Clones remain under `issue-to-mr/` | Their conversations had not stopped yet | They are removed by a later poll once the conversation is terminal |
