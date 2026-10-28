---
name: github-repo-monitor
description: >
  This skill should be used when the user asks to "monitor a GitHub repository",
  "watch GitHub for issues or PRs", "respond to @OpenHands mentions on GitHub",
  "set up an OpenHands GitHub integration", "trigger OpenHands from a GitHub
  comment", or "poll a GitHub repo for a trigger phrase". Guides the user
  through creating a cron automation that polls a single repository and starts
  an OpenHands conversation whenever a configurable trigger phrase is detected
  in an issue or PR comment.
triggers:
  - /github-monitor:poll
---

# Github Repo Monitor

This automation now runs from the executable automation plugin at `plugins/github-repo-monitor`. Do not copy or package code from `skills/github-repo-monitor`; the skill is only a setup guide for creating the plugin-spec automation.

## Authorization and work mode

By default only the token owner, explicitly allowlisted logins, or users with repository write access can trigger work. `anyone` accepts non-bot commenters; do not combine it with `implement`, which permits pushing to a branch. `reply` only investigates and comments. Never merge, force-push, or push to the base branch. Verify the token has access to the repository and the permissions required for the selected work mode. Ask for the repository, alias, authorization policy, work mode and cron schedule before creating the automation.

## Create with the plugin-spec endpoint

Use `POST /api/automation/v1/plugin-spec` with this plugin source:

```json
{
  "source": "github:OpenHands/extensions",
  "repo_path": "plugins/github-repo-monitor",
  "ref": "main"
}
```

`ref` is `main` while this plugin layout is unreleased. After an `openhands-extensions` release includes this plugin, prefer the matching release tag, for example `v<extensions-version>`. If setup code can inspect the installed package version, parameterize this value as `v{version('openhands-extensions')}`; otherwise default to `main`.

For local Agent Canvas development from this checkout, use a local source instead:

```json
{
  "source": "/absolute/path/to/OpenHands/extensions",
  "repo_path": "plugins/github-repo-monitor"
}
```

## Request template

```json
{
  "name": "Create a cron automation that polls a GitHub repository for issue and PR comments containing a configurable trigger phrase (@OpenHands by default)",
  "plugin": {
    "source": "github:OpenHands/extensions",
    "repo_path": "plugins/github-repo-monitor",
    "ref": "main"
  },
  "config": {
    "repository": "OpenHands/extensions",
    "trigger_phrase": "@openhands",
    "base_branch": "main",
    "event_types": [
        "issue_comment"
    ],
    "allowed_github_logins": [
        "<TOKEN_OWNER>"
    ],
    "openhands_url": "http://localhost:8000",
    "authorization": "repo_write",
    "work_mode": "implement"
},
  "trigger": {
    "type": "cron",
    "schedule": "*/15 * * * *",
    "timezone": "UTC"
},
  "enabled": false
}
```

The authoritative config schema is in `plugins/github-repo-monitor/.plugin/plugin.json` under `automation.config_schema`. Use that schema to validate any user-provided values before creating the automation.

## Runtime notes

- Entrypoint: `python3 plugin_runner.py main.py` in `scripts`.
- Agent profile: `default`.
- Secondary plugins: `[]`.

The old skill-local script packaging flow is deprecated. Use the plugin spec directly so OpenHands/automation resolves the plugin, writes `config.json`, and derives the runtime entrypoint from the plugin manifest.
