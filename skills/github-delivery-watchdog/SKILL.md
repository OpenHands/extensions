---
name: github-delivery-watchdog
description: Periodically check pull requests and merge only current heads with independent review, tests, and passing CI.
triggers:
- /github-delivery-watchdog
---

# Github Delivery Watchdog

This automation now runs from the executable automation plugin at `plugins/github-delivery-watchdog`. Do not copy or package code from `skills/github-delivery-watchdog`; the skill is only a setup guide for creating the plugin-spec automation.

## Create with the plugin-spec endpoint

Use `POST /api/automation/v1/plugin-spec` with this plugin source:

```json
{
  "source": "github:OpenHands/extensions",
  "repo_path": "plugins/github-delivery-watchdog",
  "ref": "main"
}
```

`ref` is `main` while this plugin layout is unreleased. After an `openhands-extensions` release includes this plugin, prefer the matching release tag, for example `v<extensions-version>`. If setup code can inspect the installed package version, parameterize this value as `v{version('openhands-extensions')}`; otherwise default to `main`.

For local Agent Canvas development from this checkout, use a local source instead:

```json
{
  "source": "/absolute/path/to/OpenHands/extensions",
  "repo_path": "plugins/github-delivery-watchdog"
}
```

## Request template

```json
{
  "name": "Periodically check pull requests and merge only current heads with independent review, tests, and passing CI",
  "plugin": {
    "source": "github:OpenHands/extensions",
    "repo_path": "plugins/github-delivery-watchdog",
    "ref": "main"
  },
  "config": {
    "repos": [
        "OpenHands/extensions"
    ],
    "github_token_secret": "GITHUB_PERSONAL_ACCESS_TOKEN",
    "branch_prefix": "openhands/issue"
},
  "trigger": {
    "type": "cron",
    "schedule": "*/5 * * * *",
    "timezone": "UTC"
},
  "enabled": false
}
```

The authoritative config schema is in `plugins/github-delivery-watchdog/.plugin/plugin.json` under `automation.config_schema`. Use that schema to validate any user-provided values before creating the automation.

## Runtime notes

- Entrypoint: `python3 plugin_runner.py worker.py` in `scripts`.
- Agent profile: `none`.
- Secondary plugins: `[]`.

The old skill-local script packaging flow is deprecated. Use the plugin spec directly so OpenHands/automation resolves the plugin, writes `config.json`, and derives the runtime entrypoint from the plugin manifest.
