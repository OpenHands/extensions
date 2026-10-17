---
name: operating-modes
description: >
  Activate a named Operating Mode to inject strict behavioral constraints that prevent context collapse.
  Use when starting any task to match the agent's mindset to the type of work being done.
  Prevents the agent from applying a one-size-fits-all generic approach to every task.
triggers:
  - /mode:builder
  - /mode:maintainer
  - /mode:architect
  - /mode:economy
---

# Operating Modes

Operating modes inject strict behavioral constraints into the agent's context.
Different work requires different AI behavior. Using the wrong mode leads to:
- Technical debt (building in Maintainer Mode)
- Premature code (designing in Builder Mode)
- Token waste (investigating in Economy Mode)
- Regressions (debugging in Builder Mode)

---

## Mode: Builder (`/mode:builder`)

> Ship fast. Stay in control. Minimal ceremony.

**Use when:** Active feature development, MVPs, prototypes, greenfield code.

### Rules

**Mindset**
- Working code over perfect code
- Flat structure over architecture
- Inline logic over abstractions (until the second use case)
- Ship the feature, note the tech debt, keep moving

**Scope**
- Maximum 5 new files per feature without stopping to evaluate
- No new dependencies without explicit developer approval
- No refactoring of existing code unless directly blocking the feature

**Output**
- Full function implementations (not diffs)
- Inline comments for non-obvious logic only
- No extensive tests unless explicitly requested
- No over-engineering — "will this ship?" is the only test

**Prompt pattern:**
```
## Feature: [name]
Stack: [language + framework + key dependencies]
Goal: [what it does — one sentence]
Files to touch:
  - [path] — [what changes]
Done when: [testable condition]
Build [first file] first. Wait for my confirmation before the next file.
```

---

## Mode: Maintainer (`/mode:maintainer`)

> Stability first. Careful changes. Zero surprises.

**Use when:** Production bug fixes, changes to critical code paths, team codebases with review requirements.

### Rules

**Mindset**
- First, do no harm
- Understand before changing
- Small diffs over large ones
- Every change is a risk — minimize it

**Pre-Change (mandatory)**
- Read the target function/module before touching anything
- Identify what currently calls or depends on the code being changed
- Understand the current behavior completely before changing it

**Change constraints**
- One logical change per prompt
- Maximum 3 files per task — more requires explicit approval
- Do not rename anything without explicit instruction
- Do not move code without explicit instruction
- Do not add imports to files outside the stated scope
- No new dependencies under any circumstances

**Testing**
- All existing tests must pass after every change
- Output format: diff only, not full file rewrites

**Prompt pattern:**
```
## Change: [Brief, specific description]
Why: [one sentence — what problem this solves]
File: [exact path]
Scope: [function name, class, or line range]
Current behavior: [what it does now]
Required behavior: [what it should do after]
Verification: [how I'll know the change is correct]
Rules: do not change function signatures, output diff format only.
```

---

## Mode: Architect (`/mode:architect`)

> System thinking. Long-term correctness. Deliberate decisions.

**Use when:** Designing a new system, making hard-to-reverse decisions, evaluating trade-offs, before starting large features.

### Rules

**Mindset**
- Think in systems, not files
- Think in years, not sprints
- Understand before deciding. Decide before building.

**No-Code Rule (absolute)**
- Architect Mode produces plans, diagrams, and decision records — NO code
- Do not generate any implementation in this mode
- Output must be: options, trade-offs, recommendation, and risks

**Decision quality**
- Consider at least 2 options for every significant decision
- Explicitly name trade-offs — concrete consequences, not "pros and cons"
- Consider: What is the maintenance cost of this decision in 12 months?
- Consider: What does the next developer need to understand to work with this?
- Consider: What happens when requirements change (they will)?

**Prompt pattern:**
```
## Architecture Decision: [Title]
Problem: [what needs to be decided and why]
Context: [system state, scale, team, timeline]
Constraints: [non-negotiable constraints]
Evaluate: Option A and Option B
For each: how it solves the problem, 3 advantages, 3 disadvantages,
          implementation complexity (low/medium/high),
          maintenance cost (low/medium/high)
Then: recommend one option with clear reasoning.
List the top 3 risks. State what would make you reconsider.
Output: structured comparison + recommendation. No code.
```

---

## Mode: Economy (`/mode:economy`)

> Token-aware. Minimal context. Maximum precision.

**Use when:** Routine bug fixes with clear root causes, small well-understood changes, tight budgets or API rate limits.

**Not for:** Unknowns. If unsure what needs to change, use Builder Mode first.

### Rules

**Context rules**
- Provide only what is directly necessary for the task
- Never paste a full file — paste the relevant function or block only
- Never paste full logs — paste only the error line and stack trace
- No background story — task + scope + output format only

**Prompt rules**
- Maximum 200 words per prompt
- One task per prompt, no exceptions
- Request minimum viable output

**Output rules**
- Changed lines only (not full file rewrites)
- No explanation unless the change is non-obvious
- No alternatives offered — implement the correct solution
- No "while I'm in here" additions

**Prompt pattern:**
```
Fix: [one-line description]
File: [exact path]
Function/Lines: [name or range]
Constraint: [one key constraint]
Output: changed lines only.
```

---

## Mode Switching Guide

Healthy AI-assisted development involves switching modes as work evolves:

```
🏛 Architect  → Decision approved
🚀 Builder    → Feature complete
🛠 Maintainer → Production ready
```

**Signs you're in the wrong mode:**
- Builder + "don't refactor" repeated every prompt → Switch to Maintainer
- Maintainer + AI creating multiple new files → Tighten scope
- Architect + AI writing code before decision is made → Enforce no-code rule
- Any mode + token cost exceeds task complexity → Switch to Economy

---

*Based on [Vibe Coding Essentials](https://github.com/ashp15205/vibe-coding-essentials) — battle-tested operating modes for AI-assisted development.*
