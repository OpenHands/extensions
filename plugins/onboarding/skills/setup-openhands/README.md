# Set Up OpenHands

Configure a repository for effective use with OpenHands in one pass.

## Triggers

This skill is activated by the following keywords:

- `setup-openhands`
- `set up openhands`
- `configure openhands for this repo`

## What This Does

Walks through four steps to make a repo OpenHands-ready:

1. **AGENTS.md** — generates a root-level agent instruction file with real commands and conventions from the repo
2. **`.openhands/setup.sh`** — creates a bootstrap script that installs dependencies and sets up the environment at the start of every session
3. **`.openhands/pre-commit.sh`** — creates a pre-commit script that mirrors CI checks so the agent gets fast feedback before pushing
4. **PR review workflow** — adds a GitHub Actions workflow for automated code review on pull requests
