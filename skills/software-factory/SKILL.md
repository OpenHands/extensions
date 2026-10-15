---
name: software-factory
description: >
  Set up an OpenHands "software factory" on GitHub fast: ask only for the
  repositories and where tickets live (GitHub issues, Jira or Linear), create a working issue-to-PR and PR-review pipeline from the
  automation catalog with defaults, show what runs, then let the user stop or
  extend it one step at a time (tune settings, triage, auto-merge, stale-CI and
  QA add-ons).
triggers:
  - /software-factory
  - software factory
---

# Software Factory

Build a GitHub software factory from unmodified automation catalog bundles
(`automations/catalog/<id>/manifest.json`); a Jira or Linear station is created
by its own skill. This skill adds no automation logic.

Two phases: **Phase 1** gets a working factory after one question. **Phase 2**
extends it in short rounds, only as far as the user wants. After Phase 1 and
after every round, the **Checkpoint** shows what exists and lets the user stop.

Code lives on GitHub. Tickets can come from GitHub issues (default), Jira or
Linear: only the issue to PR station changes (see "Ticket source"). GitLab and
Bitbucket code hosts are not part of this flow.

## Stations

| Station | Catalog id | Phase | Needs agent profile |
|---|---|---|---|
| Issue to PR | `github-issue-to-pr`, or the Jira or Linear station | 1 | yes (GitHub issues only) |
| PR reviewer | `github-pr-reviewer` | 1 | yes |
| AGENTS.md maintainer | `github-agents-md-maintainer` | 1 | no |
| Issue triage | `github-issue-triage`, or `linear-triage-assistant` | add-on | yes (GitHub issues only) |
| Auto-merge watchdog | `github-delivery-watchdog` | add-on | no |
| Stale-CI PR closer | `github-stale-ci-pr-closer` | add-on | no |
| QA changes | `qa-changes` | add-on | no |

## Rules

- **Host and auth**: as the `openhands-automation` skill describes ("Determining
  the API Host", "Authentication"). `${API}` below is
  `${OPENHANDS_HOST}/api/automation/v1`; send `${AUTH_HEADER}` on every call.
- **Supported stations**: a station can be created only if
  `GET ${API}/capabilities` lists every feature in its manifest
  `requires.features`. Skip the others and say why.
- **Form values**: the user's answer, else a derived value, else the manifest
  `default`. Derived values are never asked:
  - every `githubTokenSecret` = `GITHUB_PERSONAL_ACCESS_TOKEN` (also for the
    stale-CI closer, whose default is `GITHUB_TOKEN_REVIEW`);
  - watchdog `branchPrefix` = issue to PR `branchPrefix`.
- **Agent profile** (stations that need one): the profile the user named, else
  `active_agent_profile_id` from `GET /api/agent-profiles` on the same backend.
  It must not be an ACP profile and must allow `GITHUB_PERSONAL_ACCESS_TOKEN`.
  If none qualifies, skip those stations and point the user to the station's
  catalog card in Agent Canvas (Automations), which has a profile picker.
- **Token**: never ask for its value in chat, echo it, or put it in a tool
  argument or file.
- **Failures**: if a create fails, stop, list the stations that exist (with
  ids) and the error, and ask whether to retry or delete them.

## Phase 1 - Working factory

1. Prepare, without asking anything:
   - check capabilities (see Rules);
   - `git clone --depth 1 https://github.com/OpenHands/extensions /tmp/software-factory/extensions`;
   - resolve the agent profile (see Rules);
   - check the token:
     ```bash
     curl -s https://api.github.com/user -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
       | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('login') or d.get('message'))"
     ```
2. If the token is missing or invalid: when the `request_secret` tool is
   available, call it once with `name: "GITHUB_PERSONAL_ACCESS_TOKEN"` and a
   `reason` asking for Contents, Issues, Pull requests and Workflows read and
   write (classic PAT: `repo`, `workflow`), then end your turn and wait for the
   `[secret-request]` message. Otherwise tell the user to add it in Settings ->
   Secrets and stop.
3. Ask, in one message: "Which GitHub repositories (`owner/repo`)? Where do
   tickets live: GitHub issues (default), Jira or Linear?" Say that everything
   else uses defaults that can be changed afterwards.
4. For each repository, check `permissions.push` from
   `GET https://api.github.com/repos/{owner}/{repo}`. Drop the ones the token
   cannot push to, and say which.
5. Create the reviewer and the AGENTS.md maintainer (see "Create a station"),
   and the issue to PR station for the ticket source (see "Ticket source").
6. Run "Verify and enable" for the reviewer and, with GitHub issues, for issue
   to PR. Dispatch the
   AGENTS.md maintainer once (`POST ${API}/{id}/dispatch`) and enable it without
   waiting for the run, which opens one `AGENTS.md` pull request per repository.
7. Go to the Checkpoint.

## Checkpoint

1. Show what exists, with the `canvas_ui` tool if available, otherwise a table:
   station, automation id, repositories, schedule, enabled. Below it, the
   current value of each setting in the Tune table. Point out that the reviewer
   also reviews any open, non-draft, green pull request with no review yet (at
   most 2 new per scan).

   Check the maintainer's run (`GET ${API}/{id}/runs?limit=1`). If it finished,
   link the `AGENTS.md` pull requests and ask the user to merge them: they give
   the build agent the repository's build, test and lint commands. If not, say
   they are on their way.
2. Say how to use it: "Add the `<trigger label>` label to a ticket to have it
   built (on Jira, the ticket body must name the `owner/repo`); the reviewer
   reviews the pull request; you merge it."
3. Say the factory already runs as is and the user can stop here. Offer the next
   steps, recommending the first one not done yet:
   1. **Try it**: open a small test issue carrying the trigger label in one
      repository (only if the user agrees), then report the pull request.
   2. **Tune**: change settings (see Phase 2).
   3. **Add a station**: triage, auto-merge watchdog, stale-CI closer, QA.
   4. **Stop**.

## Phase 2 - Extend, one round at a time

Do only what the user picked. Ask only the questions for it, in one message,
each with its current value. Apply, then return to the Checkpoint.

### Tune

| Setting | Default | Fields |
|---|---|---|
| Issue trigger label (GitHub issues) | `openhands` | issue to PR `triggerLabel` |
| Draft or ready pull requests | `draft` | `pullRequestMode` (issue to PR, AGENTS.md maintainer) |
| Branch prefix (GitHub issues) | `openhands/issue` | issue to PR `branchPrefix` (and the watchdog's, if present) |
| Which pull requests get reviewed | label `openhands-review`, reviewer `all-hands-bot` | reviewer `triggerLabel`, `triggerReviewer` |
| Review tone: concise, thorough, friendly | `concise` | reviewer `reviewTone` |
| Human reviewers requested after agent approval (two or more logins) | none | reviewer `maintainers` |
| Schedules and timezone | issue to PR `*/15 * * * *`, reviewer `*/5 * * * *`, AGENTS.md maintainer `0 9 * * 1`, add-ons per manifest; `UTC` | cron `schedule`, `timezone` |
| Agent profile | active profile | `agent_profile_id` |

Apply:

- Schedule or timezone only: `PATCH ${API}/{id}` with `{"trigger": {...}}`.
- Jira or Linear station settings: change them as its skill describes.
- Anything else is fixed at creation: create a replacement station with the new
  values and run "Verify and enable" on it. If it passes,
  `DELETE ${API}/{old id}`; if not, delete the replacement and keep the old one.

### Add a station

Ask only the question below, then create it (see "Create a station") and run
"Verify and enable".

- **Auto-merge watchdog** (GitHub issues only, since it merges only branches
  with the issue to PR prefix): confirm the user wants the agent to merge pull
  requests itself once review, tests and CI are green.
- **Stale-CI closer**: confirm it may warn on, then close, pull requests whose
  CI keeps failing.
- **Triage**: nothing. For Linear, follow the `linear-triage` skill instead;
  for Jira there is none.
- **QA changes**: which base branch (default `main`). Offer QA only if the
  `openhands-automation` webhook reachability check passes. It takes a single
  `repository`, so create one per repository.

## Create a station

Mirror how Agent Canvas creates a catalog bundle:

1. Build the bundle directory from `setup.bundle.files` (archive name ->
   path relative to the clone root):
   ```bash
   mkdir -p /tmp/software-factory/build/<id>
   cp -L /tmp/software-factory/extensions/<repo-path> /tmp/software-factory/build/<id>/<archive-name>
   ```
2. Render `setup.bundle.config`: replace each `{{form.<field>}}` with its form
   value, keeping JSON types (`repositories` stays a list). Write it to
   `config.json` in the bundle directory with `json.dumps`.
3. Upload and record the returned `tarball_path`:
   ```bash
   tar -czf /tmp/software-factory/<id>.tar.gz -C /tmp/software-factory/build/<id> .
   curl -s -X POST "${API}/uploads?name=<id>" -H "${AUTH_HEADER}" \
     -H "Content-Type: application/gzip" --data-binary @/tmp/software-factory/<id>.tar.gz
   ```
4. `POST ${API}` with:
   ```json
   {
     "name": "<manifest name> - <owner/repo>  (or '- N repositories')",
     "trigger": {"type": "cron", "schedule": "<schedule>", "timezone": "<timezone>"},
     "tarball_path": "<tarball_path>",
     "entrypoint": "<setup.bundle.entrypoint>",
     "timeout": <setup.bundle.timeout>,
     "agent_profile_id": "<only for stations that need one>",
     "template": {"id": "<id>", "version": "<setup.bundle.version>", "config": <rendered config>}
   }
   ```
5. Disable it at once: `PATCH ${API}/{id}` with `{"enabled": false}`. Record the id.

`qa-changes` has no bundle: create it as the `openhands-automation` skill
describes for an event-triggered prompt preset, with its manifest `prompt` and
`filter`. It runs only on pull request events, so leave it enabled and skip
"Verify and enable".

## Ticket source

- **GitHub issues**: `github-issue-to-pr` (see "Create a station").
- **Jira**: follow the `jira-issue-to-pr` skill with `git_provider` `github`
  and its defaults (label `create-pr`, `*/5 * * * *`). Ask only what it cannot
  look up (the Jira site if several, or the API-token details when Atlassian
  Rovo is not connected). Tell the user each ticket body must name its
  `owner/repo`.
- **Linear**: follow the `ticket-to-code-change` skill with GitHub as the
  provider. Ask its questions in one message, proposing the repositories above
  and `*/15 * * * *` as defaults.

Once its skill has created the station, run "Verify and enable" on it (skip
the dispatch if the skill already ran one).

## Verify and enable

1. `POST ${API}/{id}/dispatch`, then poll `GET ${API}/{id}/runs?limit=1` until
   the run is `COMPLETED` or `FAILED`.
2. `COMPLETED`: `PATCH ${API}/{id}` with `{"enabled": true}`.
3. `FAILED`: keep it disabled, show `error_detail`, and ask how to proceed.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Create returns 422 | A value does not match the manifest `setup` block; fix the field at the path the error names. |
| Issue to PR fails at push | The token lacks Contents or Workflows write, or does not cover that repository. |
| Reviewer never reviews | The pull request has neither the trigger label nor a request for the trigger reviewer, and is not green. |
| Watchdog never merges | Its branch prefix differs from issue to PR's, or the pull request lacks an independent approval or green CI. |
