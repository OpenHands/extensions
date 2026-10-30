---
name: vidbyte-memory
description: Install correction-driven memory into a repository, so every correction the user gives becomes a slim fact, a pytest test that fails if the mistake comes back, and a git commit. Use when the user wants the agent to stop repeating mistakes they already corrected, asks for memory that is enforced by tests, or asks to install vidbyte-memory.
triggers:
- /vidbyte-memory
- install vidbyte-memory
- correction-driven memory
---

# vidbyte-memory

Install [vidbyte-memory](https://github.com/cerredz/vidbyte-memory) (MIT) into the repository the user is working in. Afterwards, the memory protocol lives in the repo's own files:
- `AGENTS.md` (which OpenHands loads on every conversation);
- typed memory under `memory/` and slim facts under `facts/`;
- skills under `.agents/skills/`;
- tests under `tests/`.

Every correction the user gives is logged verbatim. It then becomes a fact or rule, a test or verifier that fails if the mistake returns, and a footprint commit that shows how memory changed.

This complements the `agent-memory` skill. `agent-memory` saves general repository knowledge to `AGENTS.md`. vidbyte-memory is for corrections that must stick: each one is enforced by a test, not only written down.

## Steps

1. Clone the reviewed release into a temporary folder outside the repository, and show the user `scripts/install.py` before running it:
   ```bash
   git clone --depth 1 --branch v0.2.1 https://github.com/cerredz/vidbyte-memory /tmp/vidbyte-memory
   ```
2. Show the user the plan without writing anything:
   ```bash
   python /tmp/vidbyte-memory/scripts/install.py --target . --dry-run
   ```
   The plan lists the files it would create, the agents it detected, and any existing files it would keep.
3. If the plan reports a conflict on `tests/helpers.py`, `tests/test_memory_integrity.py`, `scripts/guard.py` or `scripts/footprint.py`, stop and ask the user how to resolve it.
4. Run it without `--dry-run`. It never overwrites a file. An existing `AGENTS.md` is folded into the new `## Task` section, or kept as `AGENTS.previous.md` when long. Every edited file is backed up as `<file>.vidbyte-memory-backup`, and every write is listed in `.vidbyte-memory/install.json`.
5. Ask the user for the recurring task this repository serves. Replace the placeholder paragraph under `## Task` in `AGENTS.md` with what is produced, for whom, from what inputs, and where it goes.
6. Run `python -m pytest -q tests` (install pytest first if needed). Fix anything the install caused, and report anything that was already failing.
7. Commit with `python scripts/footprint.py --commit --title "install vidbyte-memory"`.

## After the install

- From the next request on, follow `AGENTS.md`. When the user corrects you, run the `handle-feedback` skill from `.agents/skills/` before generating anything else.
- Every request ends with the tests passing, no feedback left pending, and a footprint commit. In agents with a blocking Stop hook, `scripts/guard.py` enforces this. Here, the end-of-request checklist in `AGENTS.md` is the same contract.
- To remove it: `python scripts/install.py uninstall --dry-run`, then run it without `--dry-run`. It restores the edited files and keeps memory the agent wrote unless `--force`.

## Requirements

- Python 3.9 or later. The installer and scripts use only the standard library; the tests need pytest.
- git, for the footprint commit.
