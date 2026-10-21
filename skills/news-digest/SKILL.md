---
name: news-digest
description: >
  Create an automation that reads a list of public RSS and Atom feeds on a
  schedule - daily by default - keeps what is new and matches the configured
  topics, and has an agent write a short digest of it. It needs no credentials:
  the feeds are public URLs and, on a local Agent Canvas, the conversation is
  started with no secrets and no MCP servers.
triggers:
  - /news-digest:setup
---

# News Digest

This automation now runs from the executable automation plugin at `plugins/news-digest`. Do not copy or package code from `skills/news-digest`; the skill is only a setup guide for creating the plugin-spec automation.

## Create with the plugin-spec endpoint

Use `POST /api/automation/v1/plugin-spec` with this plugin source:

```json
{
  "source": "github:OpenHands/extensions",
  "repo_path": "plugins/news-digest",
  "ref": "main"
}
```

`ref` is `main` while this plugin layout is unreleased. After an `openhands-extensions` release includes this plugin, prefer the matching release tag, for example `v<extensions-version>`. If setup code can inspect the installed package version, parameterize this value as `v{version('openhands-extensions')}`; otherwise default to `main`.

For local Agent Canvas development from this checkout, use a local source instead:

```json
{
  "source": "/absolute/path/to/OpenHands/extensions",
  "repo_path": "plugins/news-digest"
}
```

## Request template

```json
{
  "name": "Create an automation that reads public RSS and Atom feeds on a schedule, keeps what is new and matches the configured topics, and has an agent write a short digest of it",
  "plugin": {
    "source": "github:OpenHands/extensions",
    "repo_path": "plugins/news-digest",
    "ref": "main"
  },
  "config": {
    "feeds": "https://news.ycombinator.com/rss\nhttps://feeds.arstechnica.com/arstechnica/index\nhttps://www.theverge.com/rss/index.xml",
    "topics": "artificial intelligence, open source, developer tools"
},
  "trigger": {
    "type": "cron",
    "schedule": "0 8 * * *",
    "timezone": "UTC"
},
  "enabled": false
}
```

The authoritative config schema is in `plugins/news-digest/.plugin/plugin.json` under `automation.config_schema`. Use that schema to validate any user-provided values before creating the automation.

## Runtime notes

- Entrypoint: `python3 plugin_runner.py main.py` in `scripts`.
- Agent profile: `default`.
- Secondary plugins: `[]`.

The old skill-local script packaging flow is deprecated. Use the plugin spec directly so OpenHands/automation resolves the plugin, writes `config.json`, and derives the runtime entrypoint from the plugin manifest.
