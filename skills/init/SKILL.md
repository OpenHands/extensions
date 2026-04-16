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

Get a repository ready for AI agents — from a quick AGENTS.md scaffold to a
full readiness assessment. Each workflow is documented in its own reference
file; read only the one you need.

> The deep AGENTS.md generation, readiness assessment, and full-setup workflows
> originated from Calvin Smith's onboarding plugin.

## Workflows

| Trigger | What it does | Details |
|---------|-------------|---------|
| `/init` | Quick AGENTS.md scaffold (200–400 words) | `references/workflow-init.md` |
| `setup-agents-md` | Deep AGENTS.md from real repo analysis | `references/workflow-setup-agents-md.md` |
| `setup-openhands` | Full setup: AGENTS.md + bootstrap scripts + PR review | `references/workflow-setup-openhands.md` |
| `agent-readiness-report` | 74-feature readiness assessment across 5 pillars | `references/workflow-readiness-report.md` |
| `improve-agent-readiness` | Propose & implement highest-impact fixes | `references/workflow-improve-readiness.md` |
| `setup-pr-review` | Add automated PR review workflow | `references/workflow-setup-pr-review.md` |

## How to choose

- **Just need an AGENTS.md?** → `/init` (fast) or `setup-agents-md` (thorough).
- **Setting up a repo from scratch?** → `setup-openhands` does everything.
- **Want a score?** → `agent-readiness-report`, then `improve-agent-readiness`.
- **Only need PR review?** → `setup-pr-review`.

## References

All paths below are relative to this skill's directory (`skills/init/`):

- Readiness criteria (74 features, 5 pillars): `references/criteria.md`
- Scanner scripts for automated signal gathering: `scripts/scan_*.sh`
