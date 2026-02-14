# OpenHands Skills Registry

This repository is the **public skill registry** for [OpenHands](https://github.com/OpenHands/OpenHands).
It contains reusable, shareable skills that customize agent behavior.

- Skills overview docs: https://docs.openhands.dev/overview/skills
- SDK skill guide: https://docs.openhands.dev/sdk/guides/skill

## Repository layout

Skills live under `skills/`, **one directory per skill**:

- `skills/<skill-name>/SKILL.md` — the skill definition (AgentSkills-style progressive disclosure)
- `skills/<skill-name>/README.md` — optional human-facing notes/examples

Browse the catalog in [`skills/`](skills/).

## Contributing

1. Fork this repository
2. Create a new directory: `skills/<your-skill-name>/`
3. Add `skills/<your-skill-name>/SKILL.md`
4. (Optional) Add `README.md`, `references/`, `scripts/`, etc.
5. Submit a pull request

## Agent instructions for working in this repo

See [`AGENTS.md`](AGENTS.md) for the rules agents should follow when editing/adding skills.
