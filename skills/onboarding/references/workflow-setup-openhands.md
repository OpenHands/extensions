# Full Setup — `setup-openhands`

Fully configure a repository for OpenHands: AGENTS.md, bootstrap scripts,
and PR review workflow.

## Step 1: Create AGENTS.md

Run the deep `setup-agents-md` workflow (see `workflow-setup-agents-md.md`)
to generate a root-level AGENTS.md from the repo's actual CI workflows,
build files, and documentation.

## Step 2: Create `.openhands/setup.sh`

Create a bootstrap script that runs at the start of every OpenHands session.
Read the repo's CI workflows, AGENTS.md, and build files to determine correct
commands. The script should:

- Install dependencies (the project's actual install command)
- Set required environment variables
- Run any other bootstrap steps (e.g. copy `.env.example` to `.env`)

Keep it idempotent and fast. Use real commands from CI, not generic examples.

**Docs**: https://docs.openhands.dev/openhands/usage/customization/repository#setup-script

## Step 3: Create `.openhands/pre-commit.sh`

Create a pre-commit script that runs before every commit OpenHands makes.
Mirror the lint and test commands from CI. Exit non-zero on failure so the
agent gets immediate feedback instead of waiting for CI.

**Docs**: https://docs.openhands.dev/openhands/usage/customization/repository#pre-commit-script

## Step 4: Set up PR review

Run the `setup-pr-review` workflow (see `workflow-setup-pr-review.md`) to
create the GitHub Actions workflow and walk the user through configuration.

## Step 5: Verify

Confirm all files exist and are correct:
- `AGENTS.md` at repo root with real commands (not boilerplate)
- `.openhands/setup.sh` with the project's actual install/bootstrap commands
- `.openhands/pre-commit.sh` mirroring the CI lint/test checks
- `.github/workflows/pr-review.yml` with valid YAML
