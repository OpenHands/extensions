---
name: software-factory
description: >
  Onboard a user to an OpenHands "software factory" on GitHub in one
  conversation: interview them once, collect the GitHub token securely,
  then create and smoke-test the catalog automations that turn labelled issues
  into reviewed pull requests (issue to PR, PR reviewer, AGENTS.md maintainer,
  plus optional triage, auto-merge, stale-CI and QA add-ons).
triggers:
  - /software-factory
  - software factory
---

# Software Factory

Assemble a GitHub software factory from automations that already exist in the
OpenHands automation catalog. This skill adds **no automation logic of its
own**: every station is an unmodified catalog bundle from
`automations/catalog/<id>/manifest.json`, configured through its `setup` block.

```
issue --(trigger label)--> github-issue-to-pr --> pull request --> github-pr-reviewer
  ^                                 ^                                   |
  |                                 +------- changes requested ---------+
  +-- github-issue-triage (opt.)                 approved --> human merge / github-delivery-watchdog (opt.)
main --(weekly)--> github-agents-md-maintainer --> AGENTS.md pull request
```

Scope: GitHub only. Linear, Jira, GitLab and Bitbucket stations have no setup
form yet; tell the user they are not part of this flow.

## Stations

| Station | Catalog id | Default | Needs agent profile |
|---|---|---|---|
| Issue to PR | `github-issue-to-pr` | on | yes |
| PR reviewer | `github-pr-reviewer` | on | yes |
| AGENTS.md maintainer | `github-agents-md-maintainer` | on | no |
| Issue triage | `github-issue-triage` | add-on | yes |
| Auto-merge watchdog | `github-delivery-watchdog` | add-on | no |
| Stale-CI PR closer | `github-stale-ci-pr-closer` | add-on | no |
| QA changes | `qa-changes` | add-on | no (needs webhook delivery) |

## Workflow

Follow these steps in order. Do not create anything before Step 4.

### Step 0 - Prepare

1. Determine the automation host and auth exactly as the `openhands-automation`
   skill describes ("Determining the API Host" and "Authentication"). Below,
   `${OPENHANDS_HOST}` and `${AUTH_HEADER}` mean those values.
2. Check that the deployment can run catalog bundles:
   ```bash
   curl -s "${OPENHANDS_HOST}/api/automation/v1/capabilities" -H "${AUTH_HEADER}"
   ```
   Every station needs `customTarball` in the reported features; issue to PR,
   PR reviewer and triage also need `agentProfiles`. If a feature is missing,
   drop the stations that need it and tell the user why.
3. Fetch the catalog and its bundle files:
   ```bash
   git clone --depth 1 https://github.com/OpenHands/extensions /tmp/software-factory/extensions
   ```

### Step 1 - Interview

Ask all questions in **one** message, each with its default, so the user can
answer "defaults are fine" once. Ask each question once and reuse the answer for
every station that needs it.

| # | Question | Default | Fills |
|---|---|---|---|
| 1 | Which GitHub repositories (`owner/repo`)? | none, required | `repositories` on every station |
| 2 | Which stations? | issue to PR, PR reviewer, AGENTS.md maintainer | station selection |
| 3 | Which label marks an issue ready for the agent to build? | `openhands` | `github-issue-to-pr` `triggerLabel` |
| 4 | Open agent pull requests as drafts or ready for review? | `draft` | `pullRequestMode` (issue to PR, AGENTS.md maintainer) |
| 5 | Branch prefix for agent branches? | `openhands/issue` | `github-issue-to-pr` `branchPrefix` |
| 6 | Which pull requests get reviewed: ones with a label, ones requesting a reviewer, or every green one? | label `openhands-review`, reviewer `all-hands-bot` | `github-pr-reviewer` `triggerLabel`, `triggerReviewer` |
| 7 | Review tone: concise, thorough or friendly? | `concise` | `github-pr-reviewer` `reviewTone` |
| 8 | Who should be asked for a human review after the agent approves? | nobody | `github-pr-reviewer` `maintainers` |
| 9 | How often should stations check for work, in which timezone? | issue to PR `*/15 * * * *`, reviewer `*/5 * * * *`, AGENTS.md `0 9 * * 1`; `UTC` | cron `schedule`, `timezone` |
| 10 | Which agent profile should delegated agents run as? | the active profile | `agent_profile_id` |

Only when the user picks the matching add-on, also ask:

- Watchdog: "Should the agent merge pull requests itself once review, tests and
  CI are green?" Default: no.
- Stale-CI closer: "Warn on, then close, abandoned pull requests whose CI keeps
  failing?" Default: no.
- Triage: "Triage open issues (priority, acceptance criteria) before they are
  built?" Default: no.
- QA: "Run a QA agent on each opened pull request? Against which base branch?"
  Default: no; `main`. Offer it only when the `openhands-automation` webhook
  reachability check passes.

Derive, never ask:

- `github-delivery-watchdog` `branchPrefix` = the issue to PR branch prefix
  (the two must match or the watchdog never finds the agent's pull requests).
- Every `githubTokenSecret` = `GITHUB_PERSONAL_ACCESS_TOKEN`, including the
  stale-CI closer, whose form defaults to `GITHUB_TOKEN_REVIEW`.
- Any field not listed above = its `default` in the catalog `setup.form`.

### Step 2 - Credentials

The stations need `GITHUB_PERSONAL_ACCESS_TOKEN` with Contents, Issues, Pull
requests and Workflows read and write (classic PAT: `repo` and `workflow`) on
every selected repository.

1. Check it:
   ```bash
   curl -s https://api.github.com/user -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
     | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('login') or d.get('message'))"
   ```
2. If it is missing or invalid and the `request_secret` tool is available, call
   it once with `name: "GITHUB_PERSONAL_ACCESS_TOKEN"` and a `reason` that names
   the permissions above. End your turn and wait for the `[secret-request]`
   message. On `saved`, continue with the name it reports. Otherwise, or if the
   tool is not available, tell the user to add the secret in Settings ->
   Secrets and stop.
3. For each repository, confirm the token can push (`permissions.push` from
   `GET https://api.github.com/repos/{owner}/{repo}`). Drop repositories it
   cannot push to, and say which.

**Never** ask for a token value in chat, never echo it, and never put it in a
tool argument or a file.

### Step 3 - Plan and confirm

1. For each selected station, read its manifest and build its form values:
   the answers from Step 1, the derived values, and `default` for everything
   else in `setup.form.args` and `setup.form.triggers.cron`.
2. For stations that need an agent profile, list profiles with
   `GET /api/agent-profiles` on the same backend (local Agent Server or
   OpenHands Cloud). Use the profile the user named, else
   `active_agent_profile_id`. The profile must not be an ACP profile and must
   allow `GITHUB_PERSONAL_ACCESS_TOKEN` (tell the user to add it to the
   profile if its secret allow-list excludes it). If no profile id can be
   resolved, leave those stations out and tell the user to finish them from the
   catalog card in Agent Canvas (Automations), which has a profile picker.
3. Show the plan with the `canvas_ui` tool if available, otherwise as a table:
   station, repositories, schedule, and every non-default value. Ask the user to
   confirm. Apply edits and show the plan again until they do.

### Step 4 - Create every station disabled

For each station, mirroring how Agent Canvas creates a catalog bundle:

1. Build the bundle directory from `setup.bundle.files` (archive name ->
   repository path, relative to the clone root):
   ```bash
   mkdir -p /tmp/software-factory/build/<id>
   cp -L /tmp/software-factory/extensions/<repo-path> /tmp/software-factory/build/<id>/<archive-name>
   ```
2. Render `setup.bundle.config`: replace each `{{form.<field>}}` with that
   field's value, keeping JSON types (`repositories` stays a list). Write the
   result to `config.json` in the bundle directory. Use `json.dumps`, never
   string concatenation.
3. Package and upload:
   ```bash
   tar -czf /tmp/software-factory/<id>.tar.gz -C /tmp/software-factory/build/<id> .
   curl -s -X POST "${OPENHANDS_HOST}/api/automation/v1/uploads?name=<id>" \
     -H "${AUTH_HEADER}" -H "Content-Type: application/gzip" \
     --data-binary @/tmp/software-factory/<id>.tar.gz
   ```
   Record the returned `tarball_path`.
4. Create it with `POST ${OPENHANDS_HOST}/api/automation/v1`:
   ```json
   {
     "name": "<manifest name> - <owner/repo>  (or '- N repositories')",
     "trigger": {"type": "cron", "schedule": "<schedule>", "timezone": "<timezone>"},
     "tarball_path": "<tarball_path>",
     "entrypoint": "<setup.bundle.entrypoint>",
     "timeout": <setup.bundle.timeout>,
     "agent_profile_id": "<profile id, only for stations that need one>",
     "template": {"id": "<id>", "version": "<setup.bundle.version>", "config": <rendered config>}
   }
   ```
   `qa-changes` has no bundle: create it as the `openhands-automation` skill
   describes for an event-triggered prompt preset, with its manifest `prompt`
   and `filter`.
5. Immediately disable it: `PATCH /api/automation/v1/{id}` with
   `{"enabled": false}`. Record the id.

If any create fails, stop, report which stations exist (with ids) and the error,
and ask whether to delete them or retry. Do not leave the user guessing what was
created.

### Step 5 - Repo readiness

Dispatch `github-agents-md-maintainer` once
(`POST /api/automation/v1/{id}/dispatch`), then poll
`GET /api/automation/v1/{id}/runs?limit=1` until the run is `COMPLETED` or
`FAILED`. On success it opens one pull request per repository that adds or
updates `AGENTS.md`. Link those pull requests and ask the user to review and
merge them: they give the build agent the repository's real build, test and
lint commands. Continue whether or not they merge now.

### Step 6 - Smoke test and enable

1. Offer to open a small test issue carrying the trigger label in one
   repository; do it only if the user agrees.
2. Dispatch every remaining station once and poll its latest run as in Step 5.
   Report each result. A `FAILED` run: show `error_detail`, keep that station
   disabled, and ask how to proceed.
3. Enable every station that passed: `PATCH /api/automation/v1/{id}` with
   `{"enabled": true}`.

### Step 7 - Summary

Tell the user, per station: name, automation id, repositories, schedule,
enabled or not. Then explain how to use the factory: "Add the `<label>` label
to an issue to have it built; the reviewer picks up the pull request; you merge
it" (or the watchdog merges it, if enabled).

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `capabilities` lacks `customTarball` or `agentProfiles` | The deployment cannot run that station; drop it and say so. |
| Create returns 422 | A field does not match the manifest; compare the body with the manifest `setup` block and fix the value at the path the error names. |
| Issue to PR run fails at push | Token lacks Contents or Workflows write, or does not cover that repository. |
| Reviewer never reviews | Pull requests carry neither the trigger label nor a request for the trigger reviewer, and are not green. |
| Watchdog never merges | Its branch prefix differs from issue to PR's, or the pull request lacks an independent approval or green CI. |
