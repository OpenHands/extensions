# Aeon

Set up and operate an [Aeon](https://github.com/aeonfun/aeon) autonomous-agent instance from your coding agent. Aeon is an open-source framework that runs your own skills on a schedule in GitHub Actions. This skill is the operator console for an Aeon instance.

## Triggers

This skill is activated by the following keywords:

- `aeon`
- `aeon.yml`
- `aeon instance`
- `aeon skill`

## What it does

The skill routes to the mode you need:

- **Start** - stand up a new instance from scratch and get one real notification fast.
- **Reschedule** - change times, cadence, or what a skill focuses on (all cron in `aeon.yml` is UTC).
- **Unblock** - work through why a skill "did not run", in order, stopping at the first cause.
- **Chat to skill** - turn what you just did into a scheduled skill.
- **Edit a skill** - change what an existing skill does without breaking its survival machinery.
- **What to turn on** - pick skills, browse packs, install more.
- **Strategy and voice** - set `STRATEGY.md` (the north star) and `soul/` (the tone).
- **Mine history** - surface repeated manual work from past coding-agent chats worth automating.

## Details

Aeon runs on the user's own GitHub repo via Actions. A skill is a Markdown file (`skills/<name>/SKILL.md`); `aeon.yml` says which ones run and when. Config writes go through the repo's `./aeon` CLI, and everything routes through `gh`, so the skill first confirms `gh` points at the user's instance (not upstream `aeonfun/aeon`) before any write.

- Repository: https://github.com/aeonfun/aeon
- Homepage: https://aeon.fun

See [`SKILL.md`](SKILL.md) for the full operator playbook.
