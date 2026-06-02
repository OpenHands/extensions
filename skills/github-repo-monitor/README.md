# GitHub Repository Monitor Skill

An OpenHands skill that creates a custom-script cron automation to monitor a
GitHub repository for issue and PR comments. Each run polls GitHub first and
only routes work to an OpenHands conversation when a matching trigger comment
or tracked conversation update exists.

## What it does

1. **Polls** a GitHub repository for new comments on issues and PRs.
2. **Exits without a conversation** when no comments match the trigger,
   allowlist, and dedupe gates.
3. **Triggers** when a comment contains `@OpenHands` (configurable).
4. **Creates** an OpenHands conversation pre-loaded with the full issue/PR
   context - title, description, labels, and the last 10 comments.
5. **Posts** a GitHub comment with a link to the conversation and an
   AI-disclosure notice.
6. **Forwards** follow-up trigger comments to the running conversation,
   or re-opens it if it was previously closed.
7. **Summarises** by posting the agent's final response back to the
   issue/PR once the conversation finishes.

## Files

```
github-repo-monitor/
├── SKILL.md                  ← agent instructions (loaded automatically)
├── README.md                 ← this file
├── scripts/
│   └── main.py               ← automation script template
└── references/
    ├── state-schema.md       ← JSON state file documentation
    └── github-api.md         ← GitHub API endpoints and rate-limit notes
```

## Quick start

Just tell OpenHands:

> *"Set up a GitHub repository monitor for `owner/repo`"*

The skill will walk through token verification, allowed-login selection,
event-type selection, cron schedule, and automation creation automatically.

## Requirements

- `GITHUB_TOKEN` secret set in OpenHands Settings → Secrets
  - Classic PAT: `repo` (private repos) or `public_repo` (public repos)
  - Fine-grained PAT: Issues — Read and Write
- The monitored repository must be accessible with that token

## Configuration options

| Option | Default | Description |
|--------|---------|-------------|
| Repository | (required) | `owner/repo` format |
| Trigger phrase | `@OpenHands` | Case-insensitive string to watch for in comments |
| Allowed GitHub logins | token owner only | Who may trigger conversations; use explicit logins or `*` for any non-bot commenter |
| Event types | `issue_comment` | `issue_comment`, `pr_review_comment`, or both |
| Cron schedule | `* * * * *` | Every minute; any valid 5-field cron expression |

## State file

The automation maintains a JSON state file at:
```
~/.openhands/workspaces/automation-state/github_poller_{automation_id}.json
```

See `references/state-schema.md` for the full schema.

## Similar skills

- `slack-channel-monitor` — same pattern applied to Slack channels
