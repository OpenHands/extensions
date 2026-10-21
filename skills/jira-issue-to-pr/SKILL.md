---
name: jira-issue-to-pr
description: >
  This skill should be used when the user asks to "set up a Jira automation to create pull requests",
  "poll Jira for create-pr issues", "automatically create GitHub PRs from Jira tickets",
  "deploy a Jira issue-to-PR automation", "create a Jira to GitHub PR workflow",
  "set up the Jira issue to GitLab MR automation", "set up the Jira issue to Bitbucket PR automation",
  "open GitLab merge requests from Jira tickets", "open Bitbucket pull requests from Jira tickets",
  or mentions automating pull request or merge request creation from a Jira label.
  Deploys a cron-based OpenHands automation that watches a Jira Cloud project for issues
  labeled with a configurable label (default: "create-pr") and spawns an agent conversation
  that opens a pull request on GitHub (the default), a merge request on GitLab, or a pull
  request on Bitbucket for each new issue found, chosen with git_provider. The target
  repository is read from the body of the Jira ticket - no repo parameter is required at deploy time.
---

# Jira Issue To Pr

This automation now runs from the executable automation plugin at `plugins/jira-issue-to-pr`. Do not copy or package code from `skills/jira-issue-to-pr`; the skill is only a setup guide for creating the plugin-spec automation.

## Create with the plugin-spec endpoint

Use `POST /api/automation/v1/plugin-spec` with this plugin source:

```json
{
  "source": "github:OpenHands/extensions",
  "repo_path": "plugins/jira-issue-to-pr",
  "ref": "main"
}
```

`ref` is `main` while this plugin layout is unreleased. After an `openhands-extensions` release includes this plugin, prefer the matching release tag, for example `v<extensions-version>`. If setup code can inspect the installed package version, parameterize this value as `v{version('openhands-extensions')}`; otherwise default to `main`.

For local Agent Canvas development from this checkout, use a local source instead:

```json
{
  "source": "/absolute/path/to/OpenHands/extensions",
  "repo_path": "plugins/jira-issue-to-pr"
}
```

## Request template

```json
{
  "name": "Deploy a cron-based OpenHands automation that opens a GitHub pull request, a GitLab merge request or a Bitbucket pull request for each Jira issue carrying a configurable label (default: create-pr)",
  "plugin": {
    "source": "github:OpenHands/extensions",
    "repo_path": "plugins/jira-issue-to-pr",
    "ref": "main"
  },
  "config": {
    "jira_base_url": "https://example.atlassian.net",
    "jira_email": "user@example.com",
    "jira_token_secret": "JIRA_CLOUD_KEY",
    "jira_label": "create-pr",
    "git_provider": "github",
    "max_new_per_run": 5
},
  "trigger": {
    "type": "cron",
    "schedule": "*/5 * * * *",
    "timezone": "UTC"
},
  "enabled": false
}
```

The authoritative config schema is in `plugins/jira-issue-to-pr/.plugin/plugin.json` under `automation.config_schema`. Use that schema to validate any user-provided values before creating the automation.

## Runtime notes

- Entrypoint: `python3 plugin_runner.py main.py` in `scripts`.
- Agent profile: `default`.
- Secondary plugins: `[]`.

The old skill-local script packaging flow is deprecated. Use the plugin spec directly so OpenHands/automation resolves the plugin, writes `config.json`, and derives the runtime entrypoint from the plugin manifest.
