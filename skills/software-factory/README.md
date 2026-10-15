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
| Issue to PR | `github-issue-to-pr` | 1 |
| PR reviewer | `github-pr-reviewer` | 1 |
| AGENTS.md maintainer | `github-agents-md-maintainer` | 1 |
| Issue triage | `github-issue-triage` | add-on |
| Auto-merge watchdog | `github-delivery-watchdog` | add-on |
| Stale-CI PR closer | `github-stale-ci-pr-closer` | add-on |
| QA changes | `qa-changes` | add-on (webhooks only) |

The skill adds no automation logic of its own. Each station is the unmodified
catalog bundle from `automations/catalog/<id>/`, configured from its `setup`
block, so fixes to a station reach factories created by this skill too.

## Flow

1. **Phase 1**: verify `GITHUB_PERSONAL_ACCESS_TOKEN` (asked for with the
   `request_secret` tool if missing, never in chat), ask for the repositories,
   create the three Phase 1 stations with defaults, smoke-run issue to PR and
   the reviewer, and enable those that pass. The AGENTS.md maintainer is
   enabled at once and opens an `AGENTS.md` pull request per repository.
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
  write on every selected repository.
- An OpenHands (not ACP) agent profile that may use that token.

## Scope

GitHub only. Linear, Jira, GitLab and Bitbucket catalog entries have no setup
form yet, so they are not part of this flow.
