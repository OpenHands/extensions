# Agent Readiness Report

Evaluate how well a repository supports autonomous AI-assisted development.

## Triggers

This skill is activated by the following keywords:

- `/readiness-report`

## What This Does

Assesses a codebase across five pillars covering 74 features that determine whether an AI agent can work effectively in a repository. The output is a structured report identifying what's present, what's missing, and which pillars are strongest and weakest.

## Five Pillars

| Pillar | Question | Features |
|--------|----------|----------|
| **Agent Instructions** | Does the agent know what to do? | 18 |
| **Feedback Loops** | Does the agent know if it's right? | 16 |
| **Workflows & Automation** | Does the process support agent work? | 15 |
| **Policy & Governance** | Does the agent know the rules? | 13 |
| **Build & Dev Environment** | Can the agent build and run the project? | 12 |

## How It Works

### 1. Run the scanner scripts

Five shell scripts gather filesystem signals — file existence, config patterns, directory structures:

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

The scripts are helpers, not scorers. They find files and patterns but many features require judgment that only reading the actual files can provide.

### 2. Evaluate each feature

Walk through `references/criteria.md` pillar by pillar and mark each feature: **✓** (present), **✗** (missing), or **—** (not applicable).

### 3. Write the report

Structured output with per-pillar scores, evidence for passing features, and notes on what's missing.

## Scanner Scripts

| Script | Pillar |
|--------|--------|
| `scan_agent_instructions.sh` | Agent Instructions |
| `scan_feedback_loops.sh` | Feedback Loops |
| `scan_workflows.sh` | Workflows & Automation |
| `scan_policy.sh` | Policy & Governance |
| `scan_build_env.sh` | Build & Dev Environment |

## References

- `references/criteria.md` — full 74-feature evaluation criteria derived from analysis of 123 repositories
