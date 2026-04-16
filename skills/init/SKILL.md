---
name: init
description: >-
  Scaffold an AGENTS.md contributor guide or run a full repository onboarding
  for AI-assisted development.
triggers:
- /init
- setup-openhands
- setup-agents-md
- agent-readiness-report
- improve-agent-readiness
- setup-pr-review
---

# Repository Initialization & Onboarding

> The deep AGENTS.md generation, readiness assessment, and full-setup workflows
> originated from Calvin Smith's onboarding plugin.

## `/init` — Quick AGENTS.md Scaffold

Use `/init` when you just need an `AGENTS.md` file fast.

- `/init`: create at repo root. `/init <path>`: create scoped to `<path>`.
- Never overwrite silently — ask the user first.

**Workflow:**

1. Skim repo structure, README, CONTRIBUTING, build files, CI configs.
2. Write a 200–400 word `AGENTS.md` titled `# Repository Guidelines`.
3. Sections: Project Structure, Build/Test/Dev Commands, Coding Style,
   Testing Guidelines, Commit & PR Guidelines. Adapt as needed.
4. Be specific to the repo. Prefer concrete commands and paths.

## Other Workflows

For deeper onboarding, read the linked reference file:

| Trigger | What it does | Details |
|---------|-------------|---------|
| `setup-agents-md` | Deep AGENTS.md from real repo analysis | `references/workflow-setup-agents-md.md` |
| `setup-openhands` | Full setup: AGENTS.md + bootstrap scripts + PR review | `references/workflow-setup-openhands.md` |
| `agent-readiness-report` | 74-feature readiness assessment across 5 pillars | `references/workflow-readiness-report.md` |
| `improve-agent-readiness` | Propose & implement highest-impact fixes | `references/workflow-improve-readiness.md` |
| `setup-pr-review` | Add automated PR review workflow | `references/workflow-setup-pr-review.md` |

## References

All paths are relative to this skill's directory (`skills/init/`):

- Readiness criteria (74 features, 5 pillars): `references/criteria.md`
- Scanner scripts for automated signal gathering: `scripts/scan_*.sh`
