# Software Factory

Onboard a user to a GitHub "software factory" in one conversation. The skill
interviews the user once, collects the GitHub token securely, then creates and
smoke-tests the catalog automations that turn labelled issues into reviewed pull
requests.

## Trigger

This skill is activated by:

- `/software-factory`
- the phrase "software factory" (only when the skill is enabled)

## What it sets up

| Station | Catalog id | Default |
|---|---|---|
| Issue to PR | `github-issue-to-pr` | on |
| PR reviewer | `github-pr-reviewer` | on |
| AGENTS.md maintainer | `github-agents-md-maintainer` | on |
| Issue triage | `github-issue-triage` | add-on |
| Auto-merge watchdog | `github-delivery-watchdog` | add-on |
| Stale-CI PR closer | `github-stale-ci-pr-closer` | add-on |
| QA changes | `qa-changes` | add-on (webhooks only) |

The skill adds no automation logic of its own. Each station is the unmodified
catalog bundle from `automations/catalog/<id>/`, configured from its `setup`
block, so fixes to a station reach factories created by this skill too.

## Flow

1. Interview: ten questions, each with a default, asked once and reused across
   stations.
2. Credentials: verify `GITHUB_PERSONAL_ACCESS_TOKEN`; if missing, ask for it
   with the `request_secret` tool (Agent Canvas), never in chat.
3. Plan: fill each station's setup form and ask the user to confirm.
4. Create every station disabled.
5. Repo readiness: dispatch the AGENTS.md maintainer once; it opens an
   `AGENTS.md` pull request per repository.
6. Smoke test: dispatch the other stations once, then enable those that passed.
7. Summary: ids, schedules, and how to use the factory.

## Requirements

- An automation backend that reports `customTarball` (all stations) and
  `agentProfiles` (issue to PR, reviewer, triage) in `/api/automation/v1/capabilities`.
- A GitHub token with Contents, Issues, Pull requests and Workflows read and
  write on every selected repository.
- An OpenHands (not ACP) agent profile that may use that token.

## Scope

GitHub only. Linear, Jira, GitLab and Bitbucket catalog entries have no setup
form yet, so they are not part of this flow.
