# Software Factory

Set up a GitHub "software factory" fast, then grow it step by step. The skill
asks only for the repositories, creates a working pipeline from catalog
automations with their defaults, shows what runs, and lets the user stop there
or extend it.

## Trigger

This skill is activated by:

- `/software-factory`
- the phrase "software factory" (only when the skill is enabled)

## What it sets up

| Station | Catalog id | Phase |
|---|---|---|
| Issue to PR | `github-issue-to-pr`, or the Jira or Linear station | 1 |
| PR reviewer | `github-pr-reviewer` | 1 |
| Issue triage | `github-issue-triage` | 1 |
| AGENTS.md maintainer | `github-agents-md-maintainer` | add-on |
| Auto-merge watchdog | `github-delivery-watchdog` | add-on |
| Stale-CI PR closer | `github-stale-ci-pr-closer` | add-on |
| QA changes | `qa-changes` | add-on (webhooks only) |

`scripts/factory.py` (Python standard library, no LLM) does the catalog and API
work - preflight checks, bundle upload and create, in-place tune, smoke run and
enable - so Phase 1 takes four agent steps. The skill adds no automation logic of its own. Each station is the unmodified
catalog bundle from `automations/catalog/<id>/`, configured from its `setup`
block, so fixes to a station reach factories created by this skill too. A Jira
or Linear issue to PR station is created by its own skill instead. Every
station gets the `software-factory` tag (`factory.py tag` adds it to stations
other skills create), so the Automations list can filter to the factory.

## Flow

1. **Phase 1**: verify `GITHUB_PERSONAL_ACCESS_TOKEN` (asked for with the
   `request_secret` tool if missing, never in chat), ask for the repositories
   and the ticket source (GitHub issues, Jira or Linear),
   create the three Phase 1 stations with defaults, smoke-run them, and enable
   those that pass.
2. **Checkpoint**: show the stations, their settings and how to use the
   factory. The user can stop here or pick a next step: try it with a test
   issue, tune settings, or add a station.
3. **Phase 2**: one round per pick, asking only the questions for it, then back
   to the Checkpoint.

## Requirements

- An automation backend whose `/api/automation/v1/capabilities` reports the
  features each station's manifest requires (`customTarball`, plus
  `agentProfiles` for issue to PR, reviewer and triage; QA needs webhook delivery).
- A GitHub token with Contents, Issues, Pull requests and Workflows read and
  write on every selected repository, created at
  [GitHub settings](https://github.com/settings/personal-access-tokens).
- An OpenHands (not ACP) agent profile that may use that token.
- Jira tickets: a connected Atlassian Rovo server or a Jira API token. Linear
  tickets: a Linear connection.

## Scope

Code lives on GitHub. Tickets can come from GitHub issues, Jira (through the
`jira-issue-to-pr` skill) or Linear (through the `ticket-to-code-change`
skill); only the issue to PR station changes. GitLab and Bitbucket code hosts
are not part of this flow.
