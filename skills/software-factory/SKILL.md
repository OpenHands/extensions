---
name: software-factory
description: >
  Set up an OpenHands "software factory" on GitHub fast: ask only for the
  repositories and where tickets live (GitHub issues, Jira or Linear), create a working issue-to-PR and PR-review pipeline from the
  automation catalog with defaults, show what runs, then let the user stop or
  extend it one step at a time (tune settings, AGENTS.md maintainer,
  auto-merge, stale-CI and QA add-ons).
triggers:
  - /software-factory
  - software factory
---

# Software Factory

Build a GitHub software factory from the automation plugin specs in
`plugins/<id>/.plugin/plugin.json`, with setup defaults still read from
`automations/catalog/<id>/manifest.json`; a Jira or Linear station is created
by its own skill. This skill adds no automation logic.

Two phases: **Phase 1** gets a working factory after one question. **Phase 2**
extends it in short rounds, only as far as the user wants. After Phase 1 and
after every round, the **Checkpoint** shows what exists and lets the user stop.

Code lives on GitHub. Tickets can come from GitHub issues (default), Jira or
Linear: only the issue to PR station changes (see "Ticket source"). GitLab and
Bitbucket code hosts are not part of this flow.

## Stations

| Station | Catalog id | Phase | Agent profile |
|---|---|---|---|
| Issue to PR | `github-issue-to-pr`, or the Jira or Linear station | 1 | `default` (GitHub issues only) |
| PR reviewer | `github-pr-reviewer` | 1 | `default` |
| Issue triage | `github-issue-triage`, or `linear-triage-assistant` | 1 | `default` (GitHub issues only) |
| AGENTS.md maintainer | `github-agents-md-maintainer` | add-on | `default` |
| Auto-merge watchdog | `github-delivery-watchdog` | add-on | none |
| Stale-CI PR closer | `github-stale-ci-pr-closer` | add-on | none |
| QA changes | `qa-changes` | add-on | none |

## Helper script

`scripts/factory.py` in this skill's directory does every catalog and API step
and prints one JSON document; it exits non-zero with `{"error": ...}` on
failure. Its usage is below: do not read its source, and do not load the
`openhands-automation` skill for Phase 1.

Set `OPENHANDS_HOST` to the **Ingress** URL in `<RUNTIME_SERVICES>` on a local
Agent Canvas (it serves both `/api/automation` and `/api`; the automation
backend URL does not), or to `<HOST>` on OpenHands Cloud. Run every command as:

```bash
GITHUB_PERSONAL_ACCESS_TOKEN="$GITHUB_PERSONAL_ACCESS_TOKEN" \
OPENHANDS_AUTOMATION_API_KEY="$OPENHANDS_AUTOMATION_API_KEY" \
OPENHANDS_API_KEY="$OPENHANDS_API_KEY" \
python3 <this skill's directory>/scripts/factory.py <command> ...
```

`$F` below stands for that whole line. Keep the secret names in it: the agent
server passes a saved secret into a command only when the command names it.
The script reads the token and never prints it.

| Command | Does |
|---|---|
| `$F preflight --repos a/b,c/d` | Which stations this deployment supports, the agent profile, the GitHub login, push access per repository. |
| `$F create --repos a/b --ids ID,ID [--set FIELD=VALUE] [--set ID.FIELD=VALUE]` | Creates disabled plugin-spec stations with the `software-factory` tag where supported. Reports existing stations separately and tags them where possible. |
| `$F tune --repos a/b --ids ID,ID [--set schedule=...|timezone=...] [--set ID.schedule=...]` | Updates schedule or timezone in place; other plugin config requires recreating the station until config patching is supported. |
| `$F tag ID...` | Adds the `software-factory` tag to automations created by other skills, reporting failures under `not_tagged`. |
| `$F verify ID... [--no-wait ID...]` | Dispatches once, enables the ones whose run `COMPLETED` and disables the rest, reporting their `error_detail`. `--no-wait` enables without waiting. |
| `$F status ID...` | The latest run of each. |
| `$F prs --repos a/b [--branch-prefix P]` | Open pull requests whose branch starts with `P` (default `openhands/agents-md`, the AGENTS.md maintainer's). |
| `$F reset-token` | Deletes the saved `GITHUB_PERSONAL_ACCESS_TOKEN` (local Agent Canvas), so `request_secret` opens its form again. |

`create` and `verify` return each automation's `url`, its page in Agent Canvas.
Trust the script's output: do not open pages in the browser to check them, and
do not use the task tracker for this flow.

Plugin-spec stations use the agent profile named `default`. Keep `--profile`
omitted unless you are explicitly checking that same profile name. Remote plugin
sources use the installed `openhands-extensions` version tag when available, or
`main` for unreleased source checkouts. Set `FACTORY_EXTENSIONS_REF` to pin a
specific tag or branch.

## Rules

- **Supported stations**: create only those `preflight` reports `ok`; say why
  the others are skipped.
- **Derived values** (the script fills them; never ask): every
  `githubTokenSecret` is `GITHUB_PERSONAL_ACCESS_TOKEN`. The watchdog's
  `branchPrefix` must equal issue to PR's: when it was changed, pass
  `--set github-delivery-watchdog.branchPrefix=<same value>`.
- **Agent profile**: plugin-spec stations that launch agents use the profile
  named `default`. If `preflight` reports a profile error, skip the stations
  that need one and ask the user to create or fix the `default` profile.
- **Token**: never ask for its value in chat, echo it, or put it in a tool
  argument or file.
- **Failures**: if `create` fails, its output lists the stations it already
  created; report them with the error and ask whether to retry or delete them
  (`DELETE ${OPENHANDS_HOST}/api/automation/v1/{id}`).
- **Existing stations**: a station `create` reports under `existing` was already
  set up by an earlier run. Say so rather than presenting it as new. Use `$F tune`
  only for schedule or timezone changes; delete and recreate for other plugin
  settings until config patching is supported.
- **Factory tag**: every station carries the `software-factory` tag where
  supported. `create` adds it; for stations created by other skills (Jira or
  Linear issue to PR, Linear triage, QA changes), run `$F tag <id>`. If a station
  is `not_tagged`, report its reason: only its creator may change tags, or the
  deployment does not support tags yet.

## Phase 1 - Working factory

1. Ask, in one message: "Which GitHub repositories (`owner/repo`)? Where do
   tickets live: GitHub issues (default), Jira or Linear?" Say that everything
   else uses defaults that can be changed afterwards. If the answer names only
   repositories, use GitHub issues; do not ask again.
2. Run `$F preflight --repos <repos>`. Drop repositories without `push`, and
   say which.
3. If `github_login` is null, act on `token_error`:
   - `not_set`, and the `request_secret` tool is available: call it once with
     `name: "GITHUB_PERSONAL_ACCESS_TOKEN"` and a `reason` asking for Contents,
     Issues, Pull requests and Workflows read and write (classic PAT: `repo`,
     `workflow`), and saying a token can be created at
     https://github.com/settings/personal-access-tokens. End your turn, wait
     for the `[secret-request]` message, then rerun `preflight`.
   - `rejected`: GitHub refuses the saved token (invalid or expired), and
     `request_secret` cannot replace it: it answers `saved` at once for a name
     that exists. Say so in one sentence and ask "Shall I remove it and open
     the form for a new one?" On yes, run `$F reset-token`, then handle it as
     `not_set`. If `reset-token` fails, tell the user to create a token at
     https://github.com/settings/personal-access-tokens, replace it in
     Settings -> Secrets, and say when done.
   - `not_set` without the tool: tell the user to create a token at
     https://github.com/settings/personal-access-tokens and add it in
     Settings -> Secrets, then stop.
4. `$F create --repos <repos> --ids github-pr-reviewer`, adding
   `github-issue-to-pr,github-issue-triage` for GitHub issues. For Jira or
   Linear, also set up the issue to PR station as "Ticket source" describes;
   for Linear, set up triage with the `linear-triage` skill (Jira has none).
5. `$F verify <reviewer id> [<issue to PR id>] [<triage id>]`.
6. Go to the Checkpoint.

## Checkpoint

Write one short message, in this order:

1. One plain sentence on what runs and how to use it: "Your factory is running
   on `<repos>`. Add the `<trigger label>` label to a ticket to get a draft pull
   request; the reviewer reviews it and you merge it." (On Jira, add that the
   ticket body must name the `owner/repo`.)
2. If the AGENTS.md maintainer was added, the `AGENTS.md` pull requests from
   `$F prs --repos <repos>`, asking the user to merge them: they give the build
   agent the repository's build, test and lint commands. One opened before
   this setup started (`created_at`) is "still open from an earlier run", not
   new; the maintainer works once a week per repository. If there are none
   yet, say they are on their way.
3. A small table of the automations, each linked to its `url`:

   | Automation | Schedule | Status |
   |---|---|---|
   | [Issue to PR](<url>) | every 15 minutes | on |

   Status is `on`, or `off` with the reason in a few words. No automation ids.
4. The settings in effect, as a short list (the Tune table's current values).
   Mention that the reviewer also reviews any open, non-draft, green pull
   request with no review yet (at most 2 new per scan).
5. End with only a list of possible next steps, one line each, and nothing
   after it. Mark the first one not done yet as recommended:
   - **Try it**: I open a small test issue with the `<trigger label>` label in
     `<repo>`, only if you say so, and report the pull request.
   - **Tune**: change a setting from the list above.
   - **Add a station**: AGENTS.md maintainer, auto-merge watchdog, stale-CI closer (QA only
     if `preflight` reports it `ok`).
   - **Stop here**: the factory keeps running as it is.

## Phase 2 - Extend, one round at a time

Do only what the user picked. Ask only the questions for it, in one message,
each with its current value. Apply, then return to the Checkpoint.

### Tune

| Setting | Default | `--set` |
|---|---|---|
| Issue trigger label (GitHub issues) | `openhands` | `github-issue-to-pr.triggerLabel` |
| Draft or ready pull requests | `draft` | `pullRequestMode` (issue to PR, AGENTS.md maintainer) |
| Branch prefix (GitHub issues) | `openhands/issue` | `github-issue-to-pr.branchPrefix` (and the watchdog's, if present) |
| Which pull requests get reviewed | label `openhands-review`, reviewer `all-hands-bot` | `github-pr-reviewer.triggerLabel`, `triggerReviewer` |
| Review tone: concise, thorough, friendly | `concise` | `reviewTone` |
| Human reviewers requested after agent approval (two or more logins) | none | `maintainers` |
| Schedules and timezone | issue to PR `*/15 * * * *`, reviewer `*/5 * * * *`, triage `*/5 * * * *`, add-ons per manifest; `UTC` | `ID.schedule`, `timezone` |
| Agent profile | `default` | fixed by the plugin spec |

Apply:

- Schedule or timezone only: `$F tune --repos <repos> --ids <id>` with the
  new `--set schedule=...` or `--set timezone=...`, then `$F verify <id>`.
- Jira or Linear station settings: change them as its skill describes.
- Any other plugin-spec setting is fixed at creation until the automation API
  supports config patching. To change it, delete that station and recreate it
  with `$F create`, repeating every earlier non-default value.

### Add a station

Ask only the question below, then `$F create` it and `$F verify` it.

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
  reachability check passes. It has no plugin-spec station, so the script cannot create it:
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
