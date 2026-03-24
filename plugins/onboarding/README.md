# Onboarding Plugin

Assess how well a repository supports AI-assisted development and implement targeted improvements. This plugin bundles skills that evaluate agent readiness, propose high-impact fixes, and generate repo-specific `AGENTS.md` files — everything needed to take a codebase from agent-unfriendly to agent-ready.

## Quick Start

```
agent-readiness-report
```

Run the readiness report on any repository to get a scored evaluation across five pillars covering 74 features. Then use `improve-agent-readiness` to turn gaps into concrete fixes, or `setup-agents-md` to generate the single highest-impact file for agent readiness.

## Features

- **Readiness Assessment** — Evaluates 74 features across five pillars with scanner scripts and manual judgment
- **Prioritized Improvement Plans** — Ranks fixes by agent impact, not checklist completeness
- **AGENTS.md Generation** — Produces repo-specific agent instruction files from real commands and conventions

## Workflow

1. **Assess** — `agent-readiness-report` scans the repo and produces a structured report
2. **Plan** — `improve-agent-readiness` reads the report and proposes the 5–10 highest-impact fixes
3. **Implement** — Approved fixes are applied with atomic commits and the report is updated
4. **Generate** — `setup-agents-md` creates or improves the AGENTS.md using real repo data

## Skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| [agent-readiness-report](skills/agent-readiness-report/) | `agent-readiness-report` | Evaluate a repo across five pillars (74 features) |
| [improve-agent-readiness](skills/improve-agent-readiness/) | `improve-agent-readiness` | Propose and implement fixes from a readiness report |
| [setup-agents-md](skills/setup-agents-md/) | `setup-agents-md` | Generate a repo-specific AGENTS.md |

## Shared References

The `agent-readiness-report` and `improve-agent-readiness` skills both use the same 74-feature evaluation criteria. The canonical file lives at `references/criteria.md` at the plugin root, and each skill symlinks to it from its own `references/` directory. Edit the plugin-level copy — the symlinks keep both skills in sync automatically.
