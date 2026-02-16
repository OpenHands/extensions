# OpenHands Extensions

This repository is the **public extensions registry** for [OpenHands](https://github.com/OpenHands/OpenHands).
It contains reusable, shareable skills and plugins that customize agent behavior.

- Skills overview docs: https://docs.openhands.dev/overview/skills
- SDK skill guide: https://docs.openhands.dev/sdk/guides/skill

## Repository Layout

### Skills

Skills are Markdown-based guidelines that provide domain-specific knowledge and instructions.
They live under `skills/`, **one directory per skill**:

- `skills/<skill-name>/SKILL.md` — the skill definition (AgentSkills-style progressive disclosure)
- `skills/<skill-name>/README.md` — optional human-facing notes/examples

Browse the catalog in [`skills/`](skills/).

### Plugins

Plugins are extensions with executable code components (hooks, scripts).
They live under `plugins/`, **one directory per plugin**:

- `plugins/<plugin-name>/SKILL.md` — the plugin definition
- `plugins/<plugin-name>/hooks/` — lifecycle hooks
- `plugins/<plugin-name>/scripts/` — utility scripts

Browse available plugins in [`plugins/`](plugins/).

## Contributing

### Adding a Skill

1. Fork this repository
2. Create a new directory: `skills/<your-skill-name>/`
3. Add `skills/<your-skill-name>/SKILL.md`
4. (Optional) Add `README.md`, `references/`, `scripts/`, etc.
5. Submit a pull request

### Adding a Plugin

1. Fork this repository
2. Create a new directory: `plugins/<your-plugin-name>/`
3. Add `plugins/<your-plugin-name>/SKILL.md`
4. Add `hooks/` and/or `scripts/` directories with your executable code
5. Submit a pull request

## Agent Instructions

See [`AGENTS.md`](AGENTS.md) for the rules agents should follow when editing/adding skills and plugins.
