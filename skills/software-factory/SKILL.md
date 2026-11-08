---
name: software-factory
description: >
  Set up an OpenHands software factory on GitHub or GitLab: choose the code host,
  repositories or projects, and (for GitHub) ticket source; create issue-to-PR/MR,
  review and triage/refinement stations from the automation catalog. Request a
  missing provider token securely, then show what runs and offer optional tuning
  and GitHub add-ons.
triggers:
  - /software-factory
  - software factory
---

# Software Factory

Build a GitHub or GitLab software factory from unmodified automation catalog
bundles (`automations/catalog/<id>/manifest.json`). A Jira or Linear ticket
station for GitHub code lives in its own skill. This skill adds no automation logic.

Two phases: **Phase 1** gets a working factory after one question about the code
host and projects. **Phase 2** extends it in short rounds, only as far as the
user wants. After each phase, the **Checkpoint** shows what exists.

GitHub code can use GitHub issues (default), Jira or Linear tickets. GitLab code
uses GitLab issues; the GitLab reviewer posts notes, not approvals, and the work
item refiner comments on labelled issues. Bitbucket is not part of this flow.

## Stations

| Code host | Station | Catalog id | Phase | Needs agent profile |
|---|---|---|---|---|
| GitHub | Issue to PR | `github-issue-to-pr`, or the Jira or Linear station | 1 | yes (GitHub issues only) |
| GitHub | PR reviewer | `github-pr-reviewer` | 1 | yes |
| GitHub | Issue triage | `github-issue-triage`, or `linear-triage-assistant` | 1 | yes (GitHub issues only) |
| GitLab | Issue to MR | `gitlab-issue-to-mr` | 1 | no |
| GitLab | MR reviewer | `gitlab-mr-reviewer` | 1 | no |
| GitLab | Work item refiner | `gitlab-prd-refiner` | 1 | no |
| GitHub | AGENTS.md maintainer | `github-agents-md-maintainer` | add-on | no |
| GitHub | Auto-merge watchdog | `github-delivery-watchdog` | add-on | no |
| GitHub | Stale-CI PR closer | `github-stale-ci-pr-closer` | add-on | no |
| GitHub | QA changes | `qa-changes` | add-on | no |

## Helper script

`scripts/factory.py` in this skill's directory does every catalog and API step
and prints one JSON document; it exits non-zero with `{"error": ...}` on
failure. Its usage is below: do not read its source, and do not load the
`openhands-automation` skill for Phase 1.

Set `OPENHANDS_HOST` to the **Ingress** URL in `<RUNTIME_SERVICES>` on a local
Agent Canvas (it serves both `/api/automation` and `/api`; the automation
backend URL does not), or to `<HOST>` on OpenHands Cloud. Run every command
with only the selected code host's token:

```bash
# GitHub
GITHUB_PERSONAL_ACCESS_TOKEN="$GITHUB_PERSONAL_ACCESS_TOKEN" \
OPENHANDS_AUTOMATION_API_KEY="$OPENHANDS_AUTOMATION_API_KEY" \
OPENHANDS_API_KEY="$OPENHANDS_API_KEY" \
python3 <this skill's directory>/scripts/factory.py <command> ...

# GitLab (instead of the GitHub command)
GITLAB_TOKEN="$GITLAB_TOKEN" \
OPENHANDS_AUTOMATION_API_KEY="$OPENHANDS_AUTOMATION_API_KEY" \
OPENHANDS_API_KEY="$OPENHANDS_API_KEY" \
python3 <this skill's directory>/scripts/factory.py <command> ...
```

`$F` below stands for the selected provider's whole command. Keep its secret
name in it: the agent server passes a saved secret into a command only when the
command names it. The script never prints a token. Do not put a token in
`--set`, `--gitlab-api-url`, a repo URL or a tool argument.
For GitLab, add `--provider gitlab --gitlab-api-url <HTTPS /api/v4 root>` to
`preflight`, `create` and `tune` (URL defaults to `https://gitlab.com/api/v4`).
Add only `--provider gitlab` to `reset-token`; `verify`, `status` and `tag` have
no provider flag. GitHub needs neither flag.

| Command | Does |
|---|---|
| `$F preflight --repos a/b,c/d [--provider gitlab --gitlab-api-url URL]` | Supported stations, provider identity and per-project access; GitHub also checks the agent profile. |
| `$F create --repos a/b --ids ID,ID [--set FIELD=VALUE] [--set ID.FIELD=VALUE]` | Fills each station's form (answers, then derived values, then manifest defaults), uploads the bundle and creates it disabled with the `software-factory` tag. `FIELD=VALUE` applies to every listed station with that field. Stations that already exist are reported under `existing`, not recreated, and get the tag added. |
| `$F tune --repos a/b --ids ID,ID [--set FIELD=VALUE] [--set ID.FIELD=VALUE]` | Applies new settings to an existing station by updating it in place. Use this to change a value that is fixed at creation. |
| `$F tag ID...` | Adds the `software-factory` tag to automations created outside the script, so the Automations list can filter to the factory. Lists any it could not tag under `not_tagged`, each with its `reason`. |
| `$F verify ID... [--no-wait ID...]` | Dispatches once, enables the ones whose run `COMPLETED` and disables the rest, reporting their `error_detail`. `--no-wait` enables without waiting. |
| `$F status ID...` | The latest run of each. |
| `$F prs --repos a/b [--branch-prefix P]` | Open pull requests whose branch starts with `P` (default `openhands/agents-md`, the AGENTS.md maintainer's). |
| `$F reset-token [--provider gitlab]` | Deletes only the selected provider's saved token (local Agent Canvas), after the user agrees to replace it. |

`create` and `verify` return each automation's `url`, its page in Agent Canvas.
Trust the script's output: do not open pages in the browser to check them, and
do not use the task tracker for this flow.

Add `--profile NAME` to `preflight` or `create` to use a profile other than the
active one.

## Rules

- **Supported stations**: create only those `preflight` reports `ok`; say why
  the others are skipped.
- **Derived values** (the script fills them; never ask): every GitHub
  `githubTokenSecret` is `GITHUB_PERSONAL_ACCESS_TOKEN`. All GitLab stations
  inherit the `--gitlab-api-url` used for preflight; a token is never written
  into a bundle. The GitHub watchdog's `branchPrefix` must equal issue to PR's:
  when it was changed, pass `--set github-delivery-watchdog.branchPrefix=<same value>`.
- **Agent profile**: GitLab stations do not require one. For GitHub, if
  `preflight` reports a profile error, skip the stations that need one and
  point the user to the station's catalog card in Agent Canvas (Automations).
- **Token**: never ask for its value in chat, echo it, or put it in a tool
  argument or file.
- **Failures**: if `create` fails, its output lists the stations it already
  created; report them with the error and ask whether to retry or delete them
  (`DELETE ${OPENHANDS_HOST}/api/automation/v1/{id}`).
- **Existing stations**: a station `create` reports under `existing` was already
  set up by an earlier run and was left unchanged. Say so rather than presenting
  it as new, and change it with `$F tune` if the user wants different settings.
- **Factory tag**: every station carries the `software-factory` tag, which the
  Automations list filters on. `create` adds it; for a station another skill
  creates (Jira or Linear issue to PR, Linear triage, QA changes), run
  `$F tag <id>` once it exists. A station listed under `not_tagged` works but
  has no tag, and its `reason` says why. `only its creator can change its tags`:
  another user created it, so tell the user they can ask that person to add the
  tag. `this automation service does not support tags yet`: the deployment's
  automation service predates tags; tell the user, and run `$F tag <id>` for
  those stations once it is upgraded.

## Phase 1 - Working factory

1. Ask in one message: "Is your code on GitHub or GitLab, and which repositories
   or projects (`owner/repo` or `group/subgroup/project`)? For GitHub, are tickets
   in GitHub issues (default), Jira or Linear? For GitLab, is the instance
   gitlab.com (default), or what is its HTTPS `/api/v4` URL?" Do not re-ask
   information already given. If the user names a self-managed GitLab instance
   without its API URL, get that URL before proceeding. Everything else uses
   catalog defaults and can be tuned later.
2. Run `$F preflight --repos <repos>` with the GitLab provider and instance URL
   flags when selected. For **every GitLab token request or replacement**, tell
   the user to create a personal, project or group access token **on the selected
   GitLab instance** with the `api` scope (the single required scope; `read_api`
   or repository-only scopes are not enough). The token's identity must have
   Developer or higher access to each selected project. Point to
   [GitLab's access-token instructions](https://docs.gitlab.com/user/profile/personal_access_tokens/)
   and say to save the token as `GITLAB_TOKEN` in Canvas, not in chat. Include
   this guidance in the `request_secret` reason as well as any manual Settings
   -> Secrets instructions. If the selected provider's `github_login` or
   `gitlab_login` is null, use `token_error`:
   - `not_set` on a local backend with `request_secret` available: call it
     once with the selected name, `GITHUB_PERSONAL_ACCESS_TOKEN` or
     `GITLAB_TOKEN`, never the value. For GitHub, the reason asks for Contents,
     Issues, Pull requests and Workflows read and write (classic PAT: `repo`,
     `workflow`) and points to
     https://github.com/settings/personal-access-tokens. For GitLab, use the
     GitLab token requirements above in the reason. End your turn, wait for
     `[secret-request]`, then rerun `preflight`.
   - `rejected`: the saved token is invalid or expired. `request_secret`
     cannot replace an existing secret. Ask "Shall I remove the saved token
     and open the form for a replacement?" Only on yes, on a local backend,
     run `$F reset-token` (add `--provider gitlab` for GitLab), then handle
     `not_set` as above. Otherwise ask the user to replace the selected token
     in Settings -> Secrets; never delete it without permission.
   - `not_set` without `request_secret` (including Cloud): ask the user to
     save the selected token in Settings -> Secrets and say when done. Stop.
   - Any other error: report it, do not request or reset a token blindly.
3. Drop projects without `push` from this factory and explain why. If GitLab
   reports `role unknown` (some project/group tokens do not expose it), do not
   claim write access: ask whether to provision issue-to-MR for the selected
   projects provisionally, or install just the reviewer and refiner. If no
   projects remain accessible, stop.
4. For GitLab run `$F create --repos <projects> --provider gitlab
   --gitlab-api-url <URL> --ids gitlab-issue-to-mr,gitlab-mr-reviewer,gitlab-prd-refiner`
   (omit issue-to-MR if the user chose not to provision it). For GitHub run
   `$F create --repos <repos> --ids github-pr-reviewer`, adding
   `github-issue-to-pr,github-issue-triage` for GitHub issues. For Jira or
   Linear, also set up the issue to PR station as "Ticket source" describes;
   for Linear, set up triage with the `linear-triage` skill (Jira has none).
5. `$F verify <created station ids>`; this dispatches once and enables only
   completed runs. A successful empty poll is not proof that GitLab can publish
   notes or push a branch: offer an explicitly authorized test issue/MR before
   claiming end-to-end verification.
6. Go to the Checkpoint.

## Checkpoint

Write one short message, in this order:

1. One plain sentence naming the host and selected repositories/projects, and
   saying the enabled stations check for work on their listed schedules. Do
   not claim an `off` station runs or that a cron scan reacts immediately.
2. GitHub only: if the AGENTS.md maintainer was added, show the `AGENTS.md`
   pull requests from `$F prs --repos <repos>`, asking the user to merge them.
   One opened before this setup started (`created_at`) is "still open from an
   earlier run", not new; the maintainer works once a week per repository.
   If there are none yet, say they are on their way.
3. A compact table with **one row per configured station**, each linked to its
   `url`. State in each row what it produces and the exact action a user can
   take to test it, using the configured labels rather than defaults if tuned.
   For GitLab (omit any station not installed), use this shape:

   | Automation | What it does / how to trigger a test | Schedule | Status |
   |---|---|---|---|
   | [Issue to MR](<url>) | Label an open issue `openhands` -> draft MR | every 15 minutes | on |
   | [MR reviewer](<url>) | Label an open, non-draft MR `openhands-review` -> review note (no approval) | every 15 minutes | on |
   | [Work item refiner](<url>) | Label an open issue `openhands-refine` -> questions and recommendations note | every 15 minutes | on |

   To test the reviewer on the MR created by issue-to-MR, mark that draft MR
   ready first, then label it `openhands-review`. For GitHub, similarly name
   each installed issue/PR trigger and outcome: labelled issue -> draft PR;
   labelled or requested non-draft PR -> review; open issue -> triage. For
   Jira or Linear, use the ticket source skill's actual trigger. Status is
   `on`, or `off` with the reason in a few words. No automation ids.
4. The settings in effect, as a short list (the Tune table's current values).
   For GitHub only, mention that the reviewer also reviews any open,
   non-draft, green pull request with no review yet (at most 2 new per scan).
   For GitLab, the reviewer posts at most one note per MR head and the refiner
   posts at most one note per issue label application.
5. End with only a list of possible next steps, one line each, and nothing
   after it. Mark the first one not done yet as recommended:
   - **Try it**: Only with permission, create a small test issue in a selected
     project/repository and use the table's trigger. On GitLab, offer separate
     authorized reviewer/refiner tests using the actions in the table.
   - **Tune**: change a setting from the list above.
   - **Add a station** (GitHub only): AGENTS.md maintainer, auto-merge watchdog,
     stale-CI closer (QA only if `preflight` reports it `ok`).
   - **Stop here**: the factory keeps running as it is.

## Phase 2 - Extend, one round at a time

Do only what the user picked. Ask only the questions for it, in one message,
each with its current value. Apply, then return to the Checkpoint.

### Tune

| Setting | Default | `--set` / option |
|---|---|---|
| Issue trigger label (GitHub or GitLab) | `openhands` | `github-issue-to-pr.triggerLabel` / `gitlab-issue-to-mr.triggerLabel` |
| Draft or ready PR/MR | `draft` | GitHub: `pullRequestMode`; GitLab: `gitlab-issue-to-mr.mergeRequestMode` |
| Branch prefix | `openhands/issue` | `github-issue-to-pr.branchPrefix` / `gitlab-issue-to-mr.branchPrefix` |
| GitHub PR review | label `openhands-review`, reviewer `all-hands-bot` | `github-pr-reviewer.triggerLabel`, `triggerReviewer` |
| GitHub review tone and human reviewers | `concise`, none | `reviewTone`, `maintainers` |
| GitLab MR review label | `openhands-review` | `gitlab-mr-reviewer.triggerLabel` |
| GitLab issue refinement label | `openhands-refine` | `gitlab-prd-refiner.triggerLabel` |
| GitLab API URL | `https://gitlab.com/api/v4` | `--gitlab-api-url URL` on preflight/create/tune (use same instance) |
| Schedules and timezone | GitHub per manifest; GitLab all `*/15 * * * *`; `UTC` | `ID.schedule`, `timezone` |
| Agent profile (GitHub only) | active profile | `--profile NAME` |

Apply:

- Schedule or timezone only:
  `PATCH ${OPENHANDS_HOST}/api/automation/v1/{id}` with `{"trigger": {...}}`.
- Jira or Linear station settings: change them as its skill describes.
- Anything else is fixed at creation: `$F tune --repos <repos> --ids <id>`
  (add the GitLab provider and instance URL flags when selected), with the new
  `--set` values (repeat every earlier non-default value), then `$F verify
  <id>`. For a new GitLab URL, rerun preflight against that host first. `tune`
  updates the station in place, with no replacement or template-id collision.

### Add a station (GitHub only)

Ask only the question below, then `$F create` it and `$F verify` it. GitLab
has no add-on stations in this skill.

- **Auto-merge watchdog** (`github-delivery-watchdog`, GitHub issues only,
  since it merges only branches with the issue to PR prefix): confirm the user
  wants the agent to merge pull requests itself once review, tests and CI are
  green.
- **Stale-CI closer** (`github-stale-ci-pr-closer`): confirm it may warn on,
  then close, pull requests whose CI keeps failing.
- **AGENTS.md maintainer** (`github-agents-md-maintainer`): nothing. Verify it
  with `--no-wait`; its run opens one `AGENTS.md` pull request per repository.
- **QA changes**: which base branch (default `main`). Offer QA only if
  `preflight` reports it `ok` and the `openhands-automation` webhook
  reachability check passes. It has no bundle, so the script cannot create it:
  create it as the `openhands-automation` skill describes for an
  event-triggered prompt preset, with its manifest `prompt` and `filter`, one
  per repository (it takes a single `repository`). It runs only on pull request
  events, so leave it enabled and skip `verify`.

## Ticket source

- **GitHub issues**: `github-issue-to-pr`, created with the others in Phase 1.
- **Jira**: follow the `jira-issue-to-pr` skill with `git_provider` `github`
  and its defaults (label `create-pr`, `*/5 * * * *`). Ask only what it cannot
  look up (the Jira site if several, or the API-token details when Atlassian
  Rovo is not connected). Tell the user each ticket body must name its
  `owner/repo`.
- **Linear**: follow the `ticket-to-code-change` skill with GitHub as the
  provider. Ask its questions in one message, proposing the repositories above
  and `*/15 * * * *` as defaults.

Once its skill has created the station, run `$F tag <id>` and then
`$F verify <id>` on it.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Create returns 422 | A value does not match the manifest `setup` block; fix the field at the path the error names. |
| Issue to PR fails at push | The token lacks Contents or Workflows write, or does not cover that repository. |
| Reviewer never reviews | The pull request has neither the trigger label nor a request for the trigger reviewer, and is not green. |
| Watchdog never merges | Its branch prefix differs from issue to PR's, or the pull request lacks an independent approval or green CI. |
