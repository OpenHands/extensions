---
name: github-agents-md-maintainer
description: >
  Create an automation that keeps AGENTS.md current in one or more GitHub
  repositories. On a schedule - weekly by default - it clones the default
  branch, starts an OpenHands conversation that reads the repository and
  creates or updates AGENTS.md, and opens a pull request with the result.
triggers:
  - /agents-md:setup
---

# Github Agents Md Maintainer

This automation now runs from the executable automation plugin at `plugins/github-agents-md-maintainer`. Do not copy or package code from `skills/github-agents-md-maintainer`; the skill is only a setup guide for creating the plugin-spec automation.

## Create with the plugin-spec endpoint

Use `POST /api/automation/v1/plugin-spec` with this plugin source:

```json
{
  "source": "github:OpenHands/extensions",
  "repo_path": "plugins/github-agents-md-maintainer",
  "ref": "main"
}
```

`ref` is `main` while this plugin layout is unreleased. After an `openhands-extensions` release includes this plugin, prefer the matching release tag, for example `v<extensions-version>`. If setup code can inspect the installed package version, parameterize this value as `v{version('openhands-extensions')}`; otherwise default to `main`.

For local Agent Canvas development from this checkout, use a local source instead:

```json
{
  "source": "/absolute/path/to/OpenHands/extensions",
  "repo_path": "plugins/github-agents-md-maintainer"
}
```

## Request template

```json
{
  "name": "Create an automation that keeps AGENTS",
  "plugin": {
    "source": "github:OpenHands/extensions",
    "repo_path": "plugins/github-agents-md-maintainer",
    "ref": "main"
  },
  "config": {
    "repos": [
        "OpenHands/extensions"
    ],
    "branch_prefix": "openhands/agents-md",
    "pull_request_mode": "draft"
},
  "trigger": {
    "type": "cron",
    "schedule": "0 9 * * 1",
    "timezone": "UTC"
},
  "enabled": false
}
```

The authoritative config schema is in `plugins/github-agents-md-maintainer/.plugin/plugin.json` under `automation.config_schema`. Use that schema to validate any user-provided values before creating the automation.

## Runtime notes

- Entrypoint: `python3 plugin_runner.py main.py` in `scripts`.
- Agent profile: `default`.
- Secondary plugins: `[]`.

The old skill-local script packaging flow is deprecated. Use the plugin spec directly so OpenHands/automation resolves the plugin, writes `config.json`, and derives the runtime entrypoint from the plugin manifest.
