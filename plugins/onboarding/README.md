# Onboarding Plugin

Assess how well a repository supports AI-assisted development and implement targeted improvements. This plugin bundles skills that evaluate agent readiness, propose high-impact fixes, and generate repo-specific `AGENTS.md` files — everything needed to take a codebase from agent-unfriendly to agent-ready.

## Quick Start

```
/readiness-report
```

Run the readiness report on any repository to get a scored evaluation across five pillars covering 74 features. Then use `/agent-onboarding` to turn gaps into concrete fixes, or `/agents-md` to generate the single highest-impact file for agent readiness.

## Features

- **Readiness Assessment** — Evaluates 74 features across five pillars with scanner scripts and manual judgment
- **Prioritized Improvement Plans** — Ranks fixes by agent impact, not checklist completeness
- **AGENTS.md Generation** — Produces repo-specific agent instruction files from real commands and conventions

## Workflow

1. **Assess** — `/readiness-report` scans the repo and produces a structured report
2. **Plan** — `/agent-onboarding` reads the report and proposes the 5–10 highest-impact fixes
3. **Implement** — Approved fixes are applied with atomic commits and the report is updated
4. **Generate** — `/agents-md` creates or improves the AGENTS.md using real repo data

## Skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| [agent-readiness](skills/agent-readiness/) | `/readiness-report` | Evaluate a repo across five pillars (74 features) |
| [agent-onboarding](skills/agent-onboarding/) | `/agent-onboarding` | Propose and implement fixes from a readiness report |
| [agents-md](skills/agents-md/) | `/agents-md` | Generate a repo-specific AGENTS.md |

## Five Pillars

| Pillar | Question | Features |
|--------|----------|----------|
| **Agent Instructions** | Does the agent know what to do? | 18 |
| **Feedback Loops** | Does the agent know if it's right? | 16 |
| **Workflows & Automation** | Does the process support agent work? | 15 |
| **Policy & Governance** | Does the agent know the rules? | 13 |
| **Build & Dev Environment** | Can the agent build and run the project? | 12 |