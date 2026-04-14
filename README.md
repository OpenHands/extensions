# OpenHands Extensions

This repository is the **public extensions registry** for [OpenHands](https://github.com/OpenHands/OpenHands).
It contains reusable, shareable skills and plugins that customize agent behavior.

- Skills overview docs: https://docs.openhands.dev/overview/skills
- SDK skill guide: https://docs.openhands.dev/sdk/guides/skill

## Installation

### OpenHands (automatic)

All extensions in this registry are **automatically available** to OpenHands agents (Cloud, CLI, and GUI). No manual installation is needed — OpenHands loads these skills at runtime.

### Claude Code

You can install this registry as a [Claude Code plugin marketplace](https://docs.anthropic.com/en/docs/claude-code/plugins):

```bash
claude plugins add-marketplace https://github.com/OpenHands/extensions
```

This registers the **OpenHands Extensions** marketplace. You can then discover and install individual skills:

```bash
claude plugins discover
claude plugins install <skill-name>
```

To install a single skill without the full marketplace, point Claude Code at the specific plugin directory:

```bash
claude plugins install https://github.com/OpenHands/extensions/tree/main/skills/<skill-name>
```

### Other Coding Agents

Extensions follow the [AgentSkills specification](https://agentskills.io/specification). Each skill is a directory with a `SKILL.md` entry point that any compatible agent can consume.

**Manual import** — copy a skill directory into your project:

```bash
# Clone just the skill you need (using git sparse-checkout)
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/OpenHands/extensions.git
cd extensions
git sparse-checkout set skills/<skill-name>
cp -r skills/<skill-name> /path/to/your/project/.agents/skills/
```

**AGENTS.md reference** — alternatively, point your agent at the skill content by
referencing it in your project's `AGENTS.md`:

```markdown
See: https://github.com/OpenHands/extensions/blob/main/skills/<skill-name>/SKILL.md
```

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

### Marketplaces

Marketplace JSON files define curated collections of extensions:

- `marketplaces/openhands-extensions.json` — the main marketplace containing all general-purpose skills and plugins
- `marketplaces/large-codebase.json` — specialized skills for large codebase migration and refactoring

## Contributing

### Adding a Skill

1. Fork this repository
2. Create a new directory: `skills/<your-skill-name>/`
3. Add `skills/<your-skill-name>/SKILL.md`
4. Add an entry to `marketplaces/openhands-extensions.json` (or the appropriate marketplace)
5. (Optional) Add `README.md`, `references/`, `scripts/`, etc.
6. Submit a pull request

### Adding a Plugin

1. Fork this repository
2. Create a new directory: `plugins/<your-plugin-name>/`
3. Add `plugins/<your-plugin-name>/SKILL.md`
4. Add `hooks/` and/or `scripts/` directories with your executable code
5. Add an entry to `marketplaces/openhands-extensions.json` (or the appropriate marketplace)
6. Submit a pull request

## Agent Instructions

See [`AGENTS.md`](AGENTS.md) for the rules agents should follow when editing/adding skills and plugins.

<hr>

### Thank You to Our Contributors

<p align="center">
  <a href="https://github.com/OpenHands/extensions/graphs/contributors">
    <img src="https://assets.openhands.dev/readme/openhands-extensions-contributors.svg" />
  </a>
</p>
