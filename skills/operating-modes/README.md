# Operating Modes — Human Notes & Examples

> This file is for human readers. The agent-facing instructions are in `SKILL.md`.

## What This Skill Does

Activates one of four behavioral modes by injecting explicit constraints into the agent's context.
Based on the [Vibe Coding Essentials](https://github.com/ashp15205/vibe-coding-essentials) runtime, battle-tested across real AI-assisted development workflows.

## The Problem It Solves

Without explicit modes, the agent applies a generic "one-size-fits-all" mindset to every task:
- Ask it to fix a minor bug → it attempts a massive refactor
- Ask it to design architecture → it jumps straight to writing code
- Ask it to find a bug → it reads the entire codebase first

This leads to **context collapse**, **wasted tokens**, and **production regressions**.

## The Four Modes

| Trigger | Mode | Use For |
|---------|------|---------|
| `/mode:builder` | 🚀 Builder | Feature dev, MVPs, prototypes |
| `/mode:maintainer` | 🛠 Maintainer | Production fixes, stable codebases |
| `/mode:architect` | 🏛 Architect | Planning, trade-offs, decisions |
| `/mode:economy` | ⚡ Economy | Routine fixes, tight budgets |

## Usage Examples

### Builder
```
/mode:builder

Add a forgot-password button to the login screen.
Just call the /api/reset endpoint. No new components.
Files in scope: Login.tsx and api.ts only.
```

### Maintainer
```
/mode:maintainer

We have a regression in the billing calculator — it fails 
when the user has a negative balance. Do not refactor the 
calculator class. Find the bug, explain the fix, write a 
failing test first.
```

### Architect
```
/mode:architect

We need to decide between a monolithic service and a 
microservice split for our auth system. Team of 3. 
No code — give me options, trade-offs, recommendation.
```

### Economy
```
/mode:economy

Fix: null check missing before email.toLowerCase() call
File: src/auth/validator.ts
Function: validateEmail()
Output: changed lines only.
```

## Mode Transition Pattern

```
🏛 Architect  →  decision record written, architecture approved
     ↓
🚀 Builder    →  feature complete, tests passing
     ↓
🛠 Maintainer →  ongoing production maintenance
```

## Source

Full documentation, failure patterns, and anti-hallucination guardrails:
https://github.com/ashp15205/vibe-coding-essentials
