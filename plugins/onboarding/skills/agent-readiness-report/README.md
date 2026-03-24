# Agent Readiness Report

Evaluate how well a repository supports autonomous AI-assisted development.

## Triggers

This skill is activated by the following keywords:

- `agent-readiness-report`

## What This Does

Assesses a codebase across five pillars that determine whether an AI agent can work effectively in a repository. Produces a structured report identifying what's present, what's missing, and which pillars are strongest and weakest.

The five pillars are:

- **Agent Instructions** — does the agent know what to do?
- **Feedback Loops** — does the agent know if it's right?
- **Workflows & Automation** — does the process support agent work?
- **Policy & Governance** — does the agent know the rules?
- **Build & Dev Environment** — can the agent build and run the project?

Once you have a report, use `improve-agent-readiness` to turn the gaps into concrete fixes.
