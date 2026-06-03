# Onboarding Plugin

Get a repository ready for OpenHands (and other AI agents) to start being productive. This plugin bundles the skills and documentation needed to take a codebase from zero to agent-ready.

## Quick Start

Run the `setup-openhands` skill on any repository. It walks through everything needed in one pass: generates an AGENTS.md, creates setup and pre-commit scripts, and adds a PR review workflow.

## Going Deeper

Once the basics are in place, you can harden your repo's agent readiness:

1. **`agent-readiness-report`** — evaluates the repo across five pillars and produces a scored report
2. **`improve-agent-readiness`** — reads that report and proposes the highest-impact fixes, then implements them on request

## Skills

| Skill | Description |
|-------|-------------|
| [setup-openhands](skills/setup-openhands/) | One-pass setup: AGENTS.md, scripts, and PR review workflow |
| [agent-readiness-report](skills/agent-readiness-report/) | Evaluate a repo's agent readiness across five pillars |
| [improve-agent-readiness](skills/improve-agent-readiness/) | Propose and implement fixes from a readiness report |
| [setup-agents-md](skills/setup-agents-md/) | Generate a repo-specific AGENTS.md |
| [setup-pr-review](skills/setup-pr-review/) | Add automated AI code review to a repo |

The last two skills (`setup-agents-md` and `setup-pr-review`) are called by `setup-openhands` — you typically won't need to run them directly.

## Shared References

The `agent-readiness-report` and `improve-agent-readiness` skills share the same evaluation criteria. The canonical file lives at `references/criteria.md` at the plugin root; each skill symlinks to it.
