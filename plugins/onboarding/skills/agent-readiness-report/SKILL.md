---
name: agent-readiness-report
description: Evaluate how well a codebase supports autonomous AI-assisted development. Analyzes repositories across five pillars (Agent Instructions, Feedback Loops, Workflows & Automation, Policy & Governance, Build & Dev Environment) covering 74 features. Use when users want to assess how agent-ready a repository is.
triggers:
- agent-readiness-report
- readiness report
---

# Agent Readiness Report

Evaluate how well a repository supports autonomous AI-assisted development.

## What this does

Assess a codebase across five pillars that determine whether an AI agent can
work effectively in a repository.  The output is a structured report identifying
what's present and what's missing.

## Five Pillars

| Pillar | Question | Features |
|--------|----------|----------|
| **Agent Instructions** | Does the agent know what to do? | 18 |
| **Feedback Loops** | Does the agent know if it's right? | 16 |
| **Workflows & Automation** | Does the process support agent work? | 15 |
| **Policy & Governance** | Does the agent know the rules? | 13 |
| **Build & Dev Environment** | Can the agent build and run the project? | 12 |

74 features total.  See `references/criteria.md` for the full list with
descriptions and evidence examples.

## How to run

### Step 1: Run the scanner scripts

Five shell scripts gather filesystem signals — file existence, config patterns,
directory structures.  They surface what's present so you don't have to run
dozens of `find` commands manually.

```bash
bash scripts/scan_agent_instructions.sh /path/to/repo
bash scripts/scan_feedback_loops.sh /path/to/repo
bash scripts/scan_workflows.sh /path/to/repo
bash scripts/scan_policy.sh /path/to/repo
bash scripts/scan_build_env.sh /path/to/repo
```

Or scan all five at once:

```bash
for s in scripts/scan_*.sh; do bash "$s" /path/to/repo; echo; done
```

**Important**: The scripts are helpers, not scorers.  They find files and
patterns but do not evaluate quality.  Many features require judgment that only
reading the actual files can provide — for example, whether a README includes
real build commands or just badges, whether inline documentation is systematic or
scattered, whether an AI usage policy has meaningful boundaries.

### Step 2: Evaluate each feature

Walk through `references/criteria.md` pillar by pillar.  For each feature:

1. Check the scanner output for relevant signals
2. For features the scanner can't fully evaluate, inspect the files yourself
3. Mark each feature: **✓** (present), **✗** (missing), or **—** (not applicable)

Features that require judgment (not fully covered by scanners):
- Does the README actually contain build/run/test commands? (not just that it exists)
- Is inline documentation systematic across the public API?
- Are examples actually runnable?
- Does the contributing guide include code standards?
- Is there a meaningful AI usage policy?
- Is the architecture documentation current?
- Are tests documented well enough for an agent to run them?

### Step 3: Write the report

Structure the output as:

```
# Agent Readiness Report: {repo name}

## Summary
- Features present: X / 74
- Strongest pillar: {pillar}
- Weakest pillar: {pillar}

## Pillar 1 · Agent Instructions (X / 18)
✓ Agent instruction file — AGENTS.md at root
✓ AI IDE configuration — .cursor/rules/ with 3 rule files
✗ Multi-model support — only Cursor configured
...

## Pillar 2 · Feedback Loops (X / 16)
...

## Pillar 3 · Workflows & Automation (X / 15)
...

## Pillar 4 · Policy & Governance (X / 13)
...

## Pillar 5 · Build & Dev Environment (X / 12)
...

```

For each passing feature, briefly note what evidence you found.
For each failing feature, note what's missing.

## What makes these features useful

Every feature answers: *if this is missing, what goes wrong for the AI agent?*
Features like "agent instruction file" and "tool server configuration" exist
because agents need them.  Features like "linter" and "CI pipeline" exist because
agents need fast, clear feedback on whether their changes are correct — not
because they're general best practices.

The criteria were derived from analysis of 123 real repositories across five
AI-readiness categories, then filtered for features that actually affect agent
effectiveness.
