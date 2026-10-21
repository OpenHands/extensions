---
name: slack-channel-monitor
description: >
  This skill should be used when the user asks to "monitor a Slack channel",
  "watch Slack for messages", "create a Slack bot that responds to mentions",
  "set up an OpenHands Slack integration", "trigger OpenHands from Slack",
  "respond to @openhands in Slack", or "poll Slack channels for a trigger
  phrase". Guides the user through creating a cron automation that watches up
  to 10 Slack channels and starts an OpenHands conversation whenever a
  configurable trigger phrase is detected.
triggers:
  - /slack-monitor:poll
---

# Slack Channel Monitor

This automation now runs from the executable automation plugin at `plugins/slack-channel-monitor`. Do not copy or package code from `skills/slack-channel-monitor`; the skill is only a setup guide for creating the plugin-spec automation.

## Create with the plugin-spec endpoint

Use `POST /api/automation/v1/plugin-spec` with this plugin source:

```json
{
  "source": "github:OpenHands/extensions",
  "repo_path": "plugins/slack-channel-monitor",
  "ref": "main"
}
```

`ref` is `main` while this plugin layout is unreleased. After an `openhands-extensions` release includes this plugin, prefer the matching release tag, for example `v<extensions-version>`. If setup code can inspect the installed package version, parameterize this value as `v{version('openhands-extensions')}`; otherwise default to `main`.

For local Agent Canvas development from this checkout, use a local source instead:

```json
{
  "source": "/absolute/path/to/OpenHands/extensions",
  "repo_path": "plugins/slack-channel-monitor"
}
```

## Request template

```json
{
  "name": "Create a cron automation that polls up to 10 Slack channels every minute and starts an OpenHands conversation when a configurable trigger phrase is detected",
  "plugin": {
    "source": "github:OpenHands/extensions",
    "repo_path": "plugins/slack-channel-monitor",
    "ref": "main"
  },
  "config": {
    "channel_ids": [],
    "trigger_phrase": "@openhands",
    "openhands_url": "http://localhost:8000"
},
  "trigger": {
    "type": "cron",
    "schedule": "* * * * *",
    "timezone": "UTC"
},
  "enabled": false
}
```

The authoritative config schema is in `plugins/slack-channel-monitor/.plugin/plugin.json` under `automation.config_schema`. Use that schema to validate any user-provided values before creating the automation.

## Runtime notes

- Entrypoint: `python3 plugin_runner.py main.py` in `scripts`.
- Agent profile: `default`.
- Secondary plugins: `[]`.

The old skill-local script packaging flow is deprecated. Use the plugin spec directly so OpenHands/automation resolves the plugin, writes `config.json`, and derives the runtime entrypoint from the plugin manifest.
