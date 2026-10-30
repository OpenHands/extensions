# GitHub Repository Monitor Skill

An OpenHands skill that creates a cron automation to monitor a GitHub
repository for issue and PR comments, routing them to OpenHands conversations
and posting results back as GitHub comments.

## What it does

1. **Polls** a GitHub repository for new comments on issues and PRs.
2. **Triggers** when a comment contains `@OpenHands` (configurable), and — by
   default — only when its author can write to the repository.
3. **Creates** an OpenHands conversation pre-loaded with the full issue/PR
   context — title, description, labels, and the last 10 comments — including
   the basis on which the author was authorized.
4. **Acts** on the request: investigates and replies, and when asked to change
   something (the default `implement` work mode) creates a branch, commits,
   pushes, and updates an existing pull request instead of opening a second one.
   It never pushes to the base branch, force-pushes, or merges.
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

The skill will walk through token verification, permission-gate selection
(who may trigger work), work-mode selection (answer only, or answer and change
code), event-type selection, cron schedule, and automation creation
automatically.

## Requirements

- `GITHUB_PERSONAL_ACCESS_TOKEN` secret set in OpenHands Settings → Secrets
  - Classic PAT: `repo` (private repos) or `public_repo` (public repos);
    `workflow` as well when the agent is allowed to implement and the repository
    has workflows
  - Fine-grained PAT: Issues — Read and Write, plus Contents — Read and Write
    and Pull requests — Read and Write for `implement`, and Metadata — Read for
    the permission check
- The monitored repository must be accessible with that token

## Configuration options

| Option | Default | Description |
|--------|---------|-------------|
| Repository | (required) | `owner/repo` format |
| Trigger phrase | `@OpenHands` | Case-insensitive alias to watch for in comments. Any handle works, e.g. `@my-bot`; it is plain text and needs no GitHub account of its own. `GITHUB_TRIGGER_PHRASE` overrides it without a code edit |
| Who may trigger work | users with write access (`AUTHORIZATION="repo_write"`) | Checks the commenter's repository permission and proceeds only for `admin`, `maintain`, or `write`; select `anyone` to accept any non-bot commenter. A trigger phrase is not authorization. The token owner and explicit `ALLOWED_GITHUB_LOGINS` entries bypass the lookup and are reported to the agent as allowed by configuration |
| What the agent may do | answer and change code (`WORK_MODE="implement"`) | `implement` may branch, commit, push, and update an existing PR; `reply` only investigates and comments. `implement` with `anyone` lets any commenter push commits — pick one or the other |
| Allowed GitHub logins | token owner only | Extra logins (or `*`) allowed regardless of repository permission; these bypass the permission check |
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
