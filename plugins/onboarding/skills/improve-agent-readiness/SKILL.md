---
name: improve-agent-readiness
description: Use an agent readiness report to identify and implement improvements that make a repository more agent-friendly. Proposes repo-appropriate fixes for each pillar, then implements them on request. Use after running a readiness report or when a user wants to improve their repo's AI-readiness.
triggers:
- improve-agent-readiness
- agent onboarding
---

# Agent Onboarding

Take a readiness report and turn its gaps into concrete, repo-appropriate fixes.

## Prerequisites

This skill expects an agent readiness report to already exist — either from
running `agent-readiness-report` on this repo or provided by the user.  If no report
exists, run the readiness report skill first.

## How to run

### Step 1: Read the report

Identify every **✗** (missing) feature across all five pillars.

### Step 2: Propose high-impact fixes

Don't try to fix everything.  Pick the **5–10 changes that would help agents the
most** across all pillars, ranked by impact.  Not every pillar needs to be
represented — focus on what matters most for this repo.  The goal is to
meaningfully improve the score, not to hit 74/74.

**Ranking heuristic** — rank by how directly the change helps an agent complete a
coding task in this repo:

1. Things that unblock agents from working at all (AGENTS.md, build commands,
   bootstrap scripts, dev environment setup)
2. Things that give agents faster feedback on their work (pre-commit hooks, test
   documentation, PR templates with checklists)
3. Things that improve quality or process (CI caching, label automation, spell
   checking, merge queues)
4. Things that improve governance or compliance (SECURITY.md, CODEOWNERS,
   actionlint, CodeQL)

A single change that lets an agent build and test the project outranks a 2-for-1
that addresses minor gaps.

Proposals should fit **this specific repo**:

- Look at the languages, frameworks, and tools already in use
- Look at the project structure (monorepo vs single package, etc.)
- Look at what's already partially in place (don't reinvent what exists)
- Propose additions that match the repo's existing conventions and style

For each proposal, include:
- What to add or change
- Where it goes (file path)
- Which pillar(s) it improves
- **Why it's high impact** — use the feature descriptions in
  `references/criteria.md` to explain what goes wrong for agents without this
  feature.  Don't just say "improves Agent Instructions" — say what the agent
  can't do today and what it'll be able to do after the fix.

### Step 3: Implement on request

When the user approves fixes (all or a subset), implement them, then **update the
readiness report** to reflect the new state.  Flip each addressed feature from ✗
to ✓ and update the pillar counts and summary.  This ensures the next run of this
skill won't re-propose fixes that have already been applied.

Follow these rules:

- **Don't generate boilerplate** — content should be specific to this repo
- **Match existing style** — if the repo uses tabs, use tabs; if docs are in
  RDoc, don't write Markdown
- **Don't over-generate** — a concise, accurate AGENTS.md beats a long generic
  one
- **Commit atomically** — one commit per logical fix, not one giant commit

## Pillar-specific guidance

### Agent Instructions fixes

The highest-impact fix is almost always an **agent instruction file** at the
root.  A good one includes:

- Build / test / lint commands (copy from CI config or Makefile, not invented)
- Project structure overview (what's in each top-level directory)
- Key conventions (naming, architecture patterns, things to avoid)
- Where to find more documentation

If the repo is a monorepo, also consider per-component instruction files that
cover component-specific conventions.

Other common fixes:
- Add AI IDE configuration if the team uses Cursor, Copilot, or Claude Code
- Create a contributing guide if one doesn't exist
- Add `.env.example` if the project uses environment variables

### Feedback Loops fixes

Focus on what gives agents the fastest signal:

- **Pre-commit hooks** are the single fastest feedback loop — configure them with
  the linter and formatter the project already uses
- **Test run documentation** in the agent instruction file — agents need to know
  *exactly* which command runs which tests
- If the project has no linter or formatter configured, propose one that matches
  the language ecosystem (don't propose Prettier for a Go project)

### Workflows & Automation fixes

Focus on structure that helps agents understand the process:

- **PR template** with a checklist — agents follow checklists well
- **Issue templates** for bugs and features — gives agents structured input
- **CI concurrency control** — prevents agent-triggered CI from piling up

### Policy & Governance fixes

Focus on boundaries the agent needs to know:

- **CODEOWNERS** — agents should know who owns what before making changes
- **Security policy** — agents need to know not to file public security issues
- Agent-aware **.gitignore** entries — prevent agent config files from being
  committed accidentally

### Build & Dev Environment fixes

Focus on reproducibility:

- **Dependency lockfile** if one doesn't exist — agents can't work with
  non-deterministic installs
- **Tool version pinning** — prevents "works on my machine" failures
- **Single-command setup** — document or script the full bootstrap

## Output format

Present proposals like this:

```
# Agent Onboarding Proposals: {repo name}

Ranked by impact.  Implementing all of these would improve:
Agent Instructions (+4), Feedback Loops (+2), Policy & Governance (+1)

1. **Create AGENTS.md** — Agent Instructions
   - Include build commands from Makefile, test commands from CI, project structure
   - Path: `./AGENTS.md`
   - Right now agents have no way to learn this repo's conventions, banned
     patterns, or how to build/test — they'll guess and get it wrong.

2. **Add pre-commit hooks** — Feedback Loops
   - Configure with ruff (already in pyproject.toml) and mypy
   - Path: `./.pre-commit-config.yaml`
   - Agents currently don't find out about lint/type errors until CI runs.
     Pre-commit hooks catch these in seconds instead of minutes.

3. **Add .env.example** — Agent Instructions, Build & Dev Environment
   - Document the 3 env vars referenced in docker-compose.yml
   - Path: `./.env.example`
   - Agents can't start the dev server without knowing which env vars to set.
     They'll either skip setup or hallucinate values.

...

Ready to implement? Reply with "all" or specify which proposals to apply.
```
