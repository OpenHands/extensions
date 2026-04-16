# init

Initialize and onboard a repository for AI-assisted development — from a quick
AGENTS.md scaffold to a full OpenHands setup with readiness assessment.

## Triggers

This skill is activated by:

- `/init` — quick AGENTS.md scaffold
- `setup-openhands` — full repository setup (AGENTS.md + scripts + PR review)
- `setup-agents-md` — deep, thorough AGENTS.md generation
- `agent-readiness-report` — evaluate agent readiness across 74 features
- `improve-agent-readiness` — propose and implement readiness improvements
- `setup-pr-review` — add automated PR review workflow

## What's Included

### Quick Start (`/init`)

Scaffold a concise, repo-specific `AGENTS.md` at the root or a subdirectory.

### Deep AGENTS.md (`setup-agents-md`)

Generate a thorough AGENTS.md that extracts real commands, structure,
conventions, and guardrails from the repository. The single highest-impact
addition for agent readiness.

### Full Setup (`setup-openhands`)

Complete repository configuration for OpenHands:
1. Create `AGENTS.md` (via `setup-agents-md`)
2. Create `.openhands/setup.sh` bootstrap script
3. Create `.openhands/pre-commit.sh` pre-commit script
4. Set up automated PR review workflow

### Agent Readiness Report (`agent-readiness-report`)

Evaluate a repository across five pillars (Agent Instructions, Feedback Loops,
Workflows & Automation, Policy & Governance, Build & Dev Environment) covering
74 features. Includes scanner scripts for automated signal gathering.

### Improve Agent Readiness (`improve-agent-readiness`)

Take a readiness report and propose the 5–10 highest-impact fixes, ranked by
how directly they help agents complete coding tasks. Implements approved fixes.

### Set Up PR Review (`setup-pr-review`)

Add the OpenHands automated PR review workflow to a GitHub repository.

## Origins

This skill incorporates the former `onboarding` plugin (by Calvin Smith),
combining its agent readiness assessment, AGENTS.md generation, and OpenHands
setup workflows with the original `/init` quick scaffold.
