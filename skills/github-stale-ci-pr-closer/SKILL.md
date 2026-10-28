---
name: github-stale-ci-pr-closer
description: Warn and close abandoned pull requests whose required CI remains failing.
triggers:
- /github-stale-ci-pr-closer
---

# Github Stale Ci Pr Closer

This automation now runs from the executable automation plugin at `plugins/github-stale-ci-pr-closer`. Do not copy or package code from `skills/github-stale-ci-pr-closer`; the skill is only a setup guide for creating the plugin-spec automation.

## Create with the plugin-spec endpoint

Use `POST /api/automation/v1/plugin-spec` with this plugin source:

```json
{
  "source": "github:OpenHands/extensions",
  "repo_path": "plugins/github-stale-ci-pr-closer",
  "ref": "main"
}
```

`ref` is `main` while this plugin layout is unreleased. After an `openhands-extensions` release includes this plugin, prefer the matching release tag, for example `v<extensions-version>`. If setup code can inspect the installed package version, parameterize this value as `v{version('openhands-extensions')}`; otherwise default to `main`.

For local Agent Canvas development from this checkout, use a local source instead:

```json
{
  "source": "/absolute/path/to/OpenHands/extensions",
  "repo_path": "plugins/github-stale-ci-pr-closer"
}
```

## Request template

```json
{
  "name": "Warn and close abandoned pull requests whose required CI remains failing",
  "plugin": {
    "source": "github:OpenHands/extensions",
    "repo_path": "plugins/github-stale-ci-pr-closer",
    "ref": "main"
  },
  "config": {
    "repos": [
        "OpenHands/extensions"
    ],
    "github_token_secret": "GITHUB_PERSONAL_ACCESS_TOKEN"
},
  "trigger": {
    "type": "cron",
    "schedule": "0 * * * *",
    "timezone": "UTC"
},
  "enabled": false
}
```

The authoritative config schema is in `plugins/github-stale-ci-pr-closer/.plugin/plugin.json` under `automation.config_schema`. Use that schema to validate any user-provided values before creating the automation.

## Runtime notes

- Entrypoint: `python3 plugin_runner.py worker.py` in `scripts`.
- Agent profile: `none`.
- Secondary plugins: `[]`.

The old skill-local script packaging flow is deprecated. Use the plugin spec directly so OpenHands/automation resolves the plugin, writes `config.json`, and derives the runtime entrypoint from the plugin manifest.
