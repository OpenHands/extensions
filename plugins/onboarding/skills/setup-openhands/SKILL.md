---
name: setup-openhands
description: Set up a repository for effective use with OpenHands. Creates AGENTS.md, setup and pre-commit scripts, and a PR review workflow. Designed to run automatically with minimal user intervention. Use when a user wants to configure their repo for OpenHands.
triggers:
- setup-openhands
- set up openhands
- configure openhands for this repo
---

# Set Up OpenHands for a Repository

Work through these steps in order.

## Step 1: Create AGENTS.md

Run `setup-agents-md` to generate a root-level `AGENTS.md` from the repo's actual
CI workflows, build files, and documentation.

## Step 2: Create `.openhands/setup.sh`

Create `.openhands/setup.sh` — a bootstrap script that runs at the start of
every OpenHands session. Read the repo's CI workflows, AGENTS.md, and build
files to determine the correct commands. The script should:

- Install dependencies (the project's actual install command)
- Set required environment variables
- Run any other bootstrap steps (e.g. copy `.env.example` to `.env`)

Keep it idempotent and fast. Use the real commands from CI, not generic examples.

**Docs**: https://docs.openhands.dev/openhands/usage/customization/repository#setup-script

## Step 3: Create `.openhands/pre-commit.sh`

Create `.openhands/pre-commit.sh` — runs before every commit OpenHands makes.
Read the repo's CI workflows to find the lint and test commands, then mirror
them in the script. Exit non-zero on failure so the agent gets immediate
feedback instead of waiting for CI.

The script should run the same checks CI runs — if CI runs `ruff check` and
`pytest`, run those. If it runs `cargo clippy` and `cargo test`, run those.

**Docs**: https://docs.openhands.dev/openhands/usage/customization/repository#pre-commit-script

## Step 4: Set up PR review

Run `setup-pr-review` to create the GitHub Actions workflow and walk the user
through configuration.

## Step 5: Verify

Confirm all files exist and are correct:
- `AGENTS.md` at repo root with real commands (not boilerplate)
- `.openhands/setup.sh` with the project's actual install/bootstrap commands
- `.openhands/pre-commit.sh` mirroring the CI lint/test checks
- `.github/workflows/pr-review.yml` with valid YAML
