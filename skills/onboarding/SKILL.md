---
name: onboarding
description: >-
  Full repository onboarding for AI agents — deep AGENTS.md generation,
  readiness assessment, and automated setup workflows.
triggers:
- setup-openhands
- setup-agents-md
- agent-readiness-report
- improve-agent-readiness
- setup-pr-review
---

# Repository Onboarding

> Based on Calvin Smith's onboarding plugin — comprehensive workflows for
> making a repository ready for AI-assisted development.

For a quick `AGENTS.md` scaffold, use the **init** skill (`/init`).

## Workflows

Read the linked reference file for the triggered workflow:

| Trigger | What it does | Details |
|---------|-------------|---------|
| `setup-agents-md` | Deep AGENTS.md from real repo analysis | `references/workflow-setup-agents-md.md` |
| `setup-openhands` | Full setup: AGENTS.md + bootstrap scripts + PR review | `references/workflow-setup-openhands.md` |
| `agent-readiness-report` | 74-feature readiness assessment across 5 pillars | `references/workflow-readiness-report.md` |
| `improve-agent-readiness` | Propose & implement highest-impact fixes | `references/workflow-improve-readiness.md` |
| `setup-pr-review` | Add automated PR review workflow | `references/workflow-setup-pr-review.md` |

## References

All paths are relative to this skill's directory (`skills/onboarding/`):

- Readiness criteria (74 features, 5 pillars): `references/criteria.md`
- Scanner scripts for automated signal gathering: `scripts/scan_*.sh`
