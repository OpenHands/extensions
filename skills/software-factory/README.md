# Software Factory

Set up a GitHub or GitLab "software factory" fast, then grow it step by step.
The skill asks for the code host and repositories or projects, creates a pipeline
from catalog automations with their defaults, shows what runs, and lets the user
stop there or extend it.

## Trigger

This skill is activated by:

- `/software-factory`
- the phrase "software factory" (only when the skill is enabled)

## What it sets up

| Code host | Station | Catalog id | Phase |
|---|---|---|---|
| GitHub | Issue to PR | `github-issue-to-pr`, or the Jira or Linear station | 1 |
| GitHub | PR reviewer | `github-pr-reviewer` | 1 |
| GitHub | Issue triage | `github-issue-triage` | 1 |
| GitLab | Issue to MR | `gitlab-issue-to-mr` | 1 |
| GitLab | MR reviewer | `gitlab-mr-reviewer` | 1 |
| GitLab | Work item refiner | `gitlab-prd-refiner` | 1 |
| GitHub | AGENTS.md maintainer | `github-agents-md-maintainer` | add-on |
| GitHub | Auto-merge watchdog | `github-delivery-watchdog` | add-on |
| GitHub | Stale-CI PR closer | `github-stale-ci-pr-closer` | add-on |
| GitHub | QA changes | `qa-changes` | add-on (webhooks only) |

`scripts/factory.py` (Python standard library, no LLM) does the catalog and API
work - preflight checks, bundle upload and create, in-place tune, smoke run and
enable. The skill adds no automation logic of its own. Each station is the
unmodified catalog bundle from `automations/catalog/<id>/`, configured from its `setup`
block, so fixes to a station reach factories created by this skill too. A Jira
or Linear issue to PR station is created by its own skill instead. Every
station gets the `software-factory` tag (`factory.py tag` adds it to stations
other skills create), so the Automations list can filter to the factory.

## Flow

1. **Phase 1**: ask which code host and repositories/projects; for GitLab ask
   for the instance's HTTPS `/api/v4` root (default gitlab.com) and whether
   GitLab can reach OpenHands at a public HTTPS webhook URL or OpenHands is
   local/private-only. For GitHub, ask whether tickets live in GitHub issues,
   Jira or Linear. Preflight the selected provider and request a missing
   `GITHUB_PERSONAL_ACCESS_TOKEN` or `GITLAB_TOKEN` with `request_secret` on a
   local backend. On other backends, direct users to Settings -> Secrets.
   Recommend polling for local/private GitLab deployments; when signed
   webhooks are supported and reachable, offer polling or events and let the
   user choose. For events, guide them through GitLab's signing-token webhook
   and the custom event source in Canvas **Automations → Events** before
   creating stations. Polling stations get a smoke run; event stations wait
   for a real signed delivery instead of an empty test dispatch.
2. **Checkpoint**: show each station's outcome, the label or action that
   triggers it, its actual schedule or webhook trigger, and status. This gives
   the user a concrete test path without guessing which automation will run.
   The user can stop, try authorized test items, or tune settings. GitHub
   offers optional add-ons.
3. **Phase 2**: one round per pick, then back to the Checkpoint.

For event mode, create a GitLab signing-token webhook (GitLab 19.0+), selecting
issue and merge request events, and register the same signing token as a custom
source in **Automations → Events** (`/automations/events`): event key expression
`object_kind`, signature header `webhook-signature`, scheme
`standard_webhooks`, and optional delivery ID header `webhook-id`. Copy the
source's URL into GitLab. The current Events page may not expose a signature
scheme field; **do not use its default HMAC-hex scheme for GitLab**. The skill
provides a secure API-based fallback and asks for confirmation before choosing
event mode. Never share signing tokens or API tokens in chat.


## Requirements

- An automation backend whose `/api/automation/v1/capabilities` reports
  `customTarball` (plus `agentProfiles` for GitHub issue to PR, reviewer and
  triage; GitHub QA needs webhook delivery).
- GitHub: a token with Contents, Issues, Pull requests and Workflows read and
  write on every selected repository, created at
  [GitHub settings](https://github.com/settings/personal-access-tokens), and
  an OpenHands (not ACP) agent profile that may use that token.
- GitLab: create a [personal, project or group access token](https://docs.gitlab.com/user/profile/personal_access_tokens/)
  on the chosen instance with the `api` scope (the only required scope) and
  Developer or higher access to every selected project. `read_api` or
  repository-only scopes do not cover the factory's writes. Save the token as
  `GITLAB_TOKEN` in Canvas, never in template config, chat or the instance URL.
  The runtime must reach the instance over HTTPS. GitLab stations need no
  agent profile.
- Jira tickets (GitHub code): a connected Atlassian Rovo server or Jira API
  token. Linear tickets (GitHub code): a Linear connection.

## Scope

GitLab code uses GitLab issues, drafts an MR for a labelled issue, posts
non-approving MR review notes on labelled non-draft MRs, and refines labelled
issue-type work items. The GitLab reviewer does not approve or merge MRs, and
GitLab-specific add-ons are not offered. GitHub code can use GitHub issues,
Jira (through the `jira-issue-to-pr` skill) or Linear (through the
`ticket-to-code-change` skill). Bitbucket code hosts are not supported.
