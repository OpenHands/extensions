# Jira Issue to Pull Request (GitHub, GitLab, Bitbucket)

Deploy a cron-based OpenHands automation that polls a Jira Cloud project for
open issues carrying a configurable label (default: `create-pr`) and, for each
new issue, starts an OpenHands agent conversation that clones the repository
named in the ticket body on the configured git provider (GitHub by default,
GitLab or Bitbucket with `git_provider`), creates a branch, implements the
requested change, and opens a pull request (a merge request on GitLab). Once the
conversation starts, it posts a
comment on the Jira ticket: "I'm on it: `<conversation URL>`".

## Triggers

This skill is activated by keywords:

- `set up a Jira automation to create pull requests`
- `poll Jira for create-pr issues`
- `automatically create GitHub PRs from Jira tickets`
- `deploy a Jira issue-to-PR automation`
- `create a Jira to GitHub PR workflow`
- `set up the Jira issue to GitLab MR automation`
- `set up the Jira issue to Bitbucket PR automation`
- `automate GitHub PR creation from a Jira label`

## How It Works

1. **Poll** - every N minutes, the script searches the Jira Cloud instance for
   open issues with the configured label: through the user's connected
   Atlassian Rovo MCP server on OpenHands Cloud and Enterprise, or with
   `POST /rest/api/3/search/jql` and an API token.
2. **Deduplicate** - on the first run the script records a `first_run_at`
   baseline timestamp in the KV store; issues whose `updated` timestamp
   predates that baseline are skipped (no backfill blast on first deploy).
   Subsequent runs filter by both `first_run_at` and a KV-backed set of
   already-processed issue keys. A `max_new_per_run` cap (default 5) limits
   conversations started per cron firing.
3. **Dispatch** - for each new issue, the script starts an independent agent
   conversation with a PR-creation prompt: `POST /api/conversations` on the
   agent server when running locally, `POST /api/v1/app-conversations` on
   OpenHands Cloud and Enterprise. The prompt instructs the agent to extract the
   target repository (`owner/repo` on GitHub; `group/project` or a URL on
   GitLab; `workspace/repo` on Bitbucket) from the ticket body. On Cloud the
   next poll confirms the conversation came up and starts it again when it did
   not.
4. **Comment** - immediately after the conversation is created, the script
   posts a Jira comment on the issue: `I'm on it: <conversation URL>`.
5. **Persist** - the processed issue key is recorded so re-runs never
   duplicate work.

The polling run is lightweight (Python stdlib only, no SDK install); LLM costs
are incurred only when new issues are actually found.

Where Jira can reach the deployment (OpenHands Cloud and Enterprise), the skill
can set up an event-based automation instead of this poller: Jira pushes label
events through a webhook, which `scripts/setup_webhook.py` registers in both
OpenHands and Jira. See "Event-Based Alternative" in `SKILL.md`.

## Prerequisites

| Requirement | Details |
|---|---|
| **Jira access** | OpenHands Cloud and Enterprise: the user's connected Atlassian Rovo MCP server, with no API token. Local, or without that connection: a Jira API token stored as an OpenHands secret (see `references/setup.md`) |
| **Git provider access** | OpenHands Cloud and Enterprise: the connected GitHub, GitLab or Bitbucket integration named by `git_provider`, or a connected MCP server (GitHub's, GitLab's, or Atlassian Rovo for Bitbucket). Local: that provider's token stored as an OpenHands secret so the spawned conversation can push branches and open the request |
| **Jira label** | The label to watch for (default: `create-pr`) must exist in the Jira project |
| **Target repository** | Must exist on the configured provider; the connected integration or token must have write access |

## Quick Start

See `SKILL.md` for the full step-by-step deployment guide, and
`references/setup.md` for Jira API token creation, git provider tokens, cron
schedule reference, and troubleshooting.
