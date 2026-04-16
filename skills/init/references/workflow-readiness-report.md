# Agent Readiness Report — `agent-readiness-report`

Evaluate how well a repository supports autonomous AI-assisted development
across five pillars covering 74 features.

## Five Pillars

| Pillar | Question | Features |
|--------|----------|----------|
| **Agent Instructions** | Does the agent know what to do? | 18 |
| **Feedback Loops** | Does the agent know if it's right? | 16 |
| **Workflows & Automation** | Does the process support agent work? | 15 |
| **Policy & Governance** | Does the agent know the rules? | 13 |
| **Build & Dev Environment** | Can the agent build and run the project? | 12 |

See `criteria.md` in this directory for the full list with descriptions and evidence.

## How to run

### Step 1: Run the scanner scripts

The scanner scripts live in this skill's `scripts/` directory. Set `SKILL_DIR`
to the absolute path of the `skills/init` directory, then run:

```bash
SKILL_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"  # or set manually
for s in "$SKILL_DIR"/scripts/scan_*.sh; do bash "$s" /path/to/repo; echo; done
```

The scripts find files and patterns but do not evaluate quality. Many features
require reading the actual files to assess.

### Step 2: Evaluate each feature

Walk through `criteria.md` pillar by pillar. Mark each feature:
**✓** (present), **✗** (missing), or **—** (not applicable).

### Step 3: Write the report

```
# Agent Readiness Report: {repo name}

## Summary
- Features present: X / 74
- Strongest pillar: {pillar}
- Weakest pillar: {pillar}

## Pillar 1 · Agent Instructions (X / 18)
✓ Agent instruction file — AGENTS.md at root
✗ Multi-model support — only Cursor configured
...
```
