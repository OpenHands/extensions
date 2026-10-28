---
name: github-issue-to-pr
description: >
  Create an automation that implements GitHub issues when a configurable
  trigger label is applied. Polls one or more repositories deterministically,
  clones the default branch, starts one OpenHands conversation per label event,
  then commits, pushes, and opens the pull request itself.
triggers:
  - /issue-to-pr:setup
---

# Github Issue To Pr

This automation now runs from the executable automation plugin at `plugins/github-issue-to-pr`. Do not copy or package code from `skills/github-issue-to-pr`; the skill is only a setup guide for creating the plugin-spec automation.

## Create with the plugin-spec endpoint

Use `POST /api/automation/v1/plugin-spec` with this plugin source:

```json
{
  "source": "github:OpenHands/extensions",
  "repo_path": "plugins/github-issue-to-pr",
  "ref": "main"
}
```

`ref` is `main` while this plugin layout is unreleased. After an `openhands-extensions` release includes this plugin, prefer the matching release tag, for example `v<extensions-version>`. If setup code can inspect the installed package version, parameterize this value as `v{version('openhands-extensions')}`; otherwise default to `main`.

For local Agent Canvas development from this checkout, use a local source instead:

```json
{
  "source": "/absolute/path/to/OpenHands/extensions",
  "repo_path": "plugins/github-issue-to-pr"
}
```

## Request template

```json
{
  "name": "Create an automation that implements GitHub issues when a configurable trigger label is applied",
  "plugin": {
    "source": "github:OpenHands/extensions",
    "repo_path": "plugins/github-issue-to-pr",
    "ref": "main"
  },
  "config": {
    "repos": [
        "OpenHands/extensions"
    ],
    "trigger_label": "openhands",
    "branch_prefix": "openhands/issue",
    "pull_request_mode": "draft",
    "github_token_secret": "GITHUB_PERSONAL_ACCESS_TOKEN"
},
  "trigger": {
    "type": "cron",
    "schedule": "*/15 * * * *",
    "timezone": "UTC"
},
  "enabled": false
}
```

The authoritative config schema is in `plugins/github-issue-to-pr/.plugin/plugin.json` under `automation.config_schema`. Use that schema to validate any user-provided values before creating the automation.

## Runtime notes

- Entrypoint: `python3 plugin_runner.py worker.py` in `scripts`.
- Agent profile: `default`.
- Secondary plugins: `[]`.

The old skill-local script packaging flow is deprecated. Use the plugin spec directly so OpenHands/automation resolves the plugin, writes `config.json`, and derives the runtime entrypoint from the plugin manifest.
