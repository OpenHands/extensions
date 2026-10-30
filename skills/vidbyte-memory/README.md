# vidbyte-memory

Installs [vidbyte-memory](https://github.com/cerredz/vidbyte-memory) into the current repository. Each correction the user gives becomes three things:
- a slim fact or rule;
- a pytest test that fails if the mistake comes back;
- a footprint commit.

All of it lives as markdown, tests and git in the repo, with no API key, database or service.

## Triggers

- `/vidbyte-memory`
- "install vidbyte-memory"
- "correction-driven memory"

## What it does

Clones the template to a temporary folder, shows a dry-run plan, runs `scripts/install.py`, fills the `## Task` section of `AGENTS.md` with the user, runs the tests and commits. The installer never overwrites a file, backs up every file it edits, and records each write in `.vidbyte-memory/install.json`, so `install.py uninstall` can undo it.

Maintained at [cerredz/vidbyte-memory](https://github.com/cerredz/vidbyte-memory) (MIT); issues go there.
