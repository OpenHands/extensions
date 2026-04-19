# Onboarding Skill

Comprehensive workflows to make a repository ready for AI-assisted development.

## Triggers

| Trigger | What it does |
|---------|-------------|
| `setup-agents-md` | Deep, thorough AGENTS.md from real repo analysis |
| `setup-openhands` | Full setup: AGENTS.md + bootstrap scripts + PR review |
| `agent-readiness-report` | 74-feature readiness assessment across 5 pillars |
| `improve-agent-readiness` | Propose & implement highest-impact fixes |
| `setup-pr-review` | Add automated PR review workflow |

For a quick `AGENTS.md` scaffold, use the **init** skill (`/init`).

## Readiness Assessment

The `agent-readiness-report` workflow scores a repository across five pillars:

1. **Agent Instructions** — AGENTS.md, style guides, naming conventions
2. **Build Environment** — one-command build/test, dependency management
3. **Feedback Loops** — linting, type-checking, test coverage
4. **CI/CD Workflows** — automated checks, review automation
5. **Policy & Governance** — security policies, contribution guidelines

See `references/criteria.md` for the full 74-feature checklist.

## Credits

Based on Calvin Smith's onboarding plugin for OpenHands.
