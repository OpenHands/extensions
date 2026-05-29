---
name: model-router
description: Recommend the most cost-efficient LLM for a given task category (research, bug fixing, planning, frontend, testing, bulk repetitive work) based on the OpenHands Index benchmark data. Use when the user asks "which model should I use", wants to pick a model, configure a sub-agent, route work to another LLM, or optimize for cost vs. quality.
triggers:
- which model
- model selection
- pick a model
- model router
- cost efficient model
- cheapest model
- best model for
---

# Model Router

Pick the right LLM for the task instead of paying premium prices for every step.
Recommendations below come from the public [OpenHands Index](https://index.openhands.dev)
benchmark (May 2026 snapshot). For each category we list a **cost pick** (best
score-per-dollar on the Pareto frontier), a **balanced pick**, and a **premium
pick** (top raw score).

If your runtime supports model switching (sub-agents, delegated cloud
conversations, or just user choice), default to the cost pick and only escalate
to balanced/premium when the task warrants it.

## Quick decision table

| Task type | Cost pick (cheap & good) | Balanced | Premium (top score) |
| --- | --- | --- | --- |
| Research / Information gathering | **Gemini-3.1-Pro** ($0.12, 76.4) | claude-opus-4-6 ($0.44, 80.0) | GPT-5.5 ($0.74, 86.1) |
| Bug fixing / Issue resolution | **Minimax-2.7** ($0.18, 75.6) | claude-opus-4-6 ($0.77, 76.8) | GPT-5.5 ($1.52, 78.2) |
| Planning / Architecture / New apps (greenfield) | **GPT-5.4** ($4.04, 56.2) | claude-opus-4-7 ($5.69, 56.2) | claude-opus-4-7 ($5.69, 56.2) |
| Frontend / UI | **Gemini-3.1-Pro** ($1.24, 44.1) | claude-opus-4-6 ($2.37, 41.8) | claude-opus-4-7 ($2.83, 48.5) |
| Testing / Test generation | **Minimax-2.7** ($0.13, 69.1) | claude-opus-4-6 ($0.43, 78.8) | GPT-5.5 ($0.92, 83.4) |
| Bulk repetitive lifting (cheap reasoning at scale) | **DeepSeek-V3.2-Reasoner** ($0.57) | Minimax-2.7 ($0.13-0.18) | n/a - escalate if quality matters |

Numbers are **average cost per problem (USD)** and **score** from the index.
Lower cost and higher score are both better.

## How to use this skill

1. **Identify the task category** from the user request. Map it to a row above:
   - "find/research/look up/answer with sources" -> Research
   - "fix bug / failing test / SWE-bench style issue / debug" -> Bug fixing
   - "design / plan / build new app or feature from scratch" -> Planning
   - "build UI / page / component / styling" -> Frontend
   - "write tests / increase coverage / add unit tests" -> Testing
   - "rename across N files / run the same edit many times / mechanical refactor" -> Bulk

2. **Default to the cost pick.** Tell the user (or pick programmatically) the
   cost pick model, citing roughly how much you expect to spend per task.

3. **Escalate when justified.** Switch to the balanced or premium pick if any
   of these are true:
   - The task is high-stakes (production bug, security fix, breaking change).
   - The cost pick has clearly failed once on the same task.
   - The user explicitly asked for the best possible quality.
   - The task spans multiple categories (e.g., "design + build + test a new
     service") - prefer a strong all-rounder like **claude-opus-4-7** or
     **GPT-5.5**.

4. **Mixed pipelines** are encouraged. Example flow for a feature request:
   - Research existing code & docs -> Gemini-3.1-Pro
   - Plan the change -> claude-opus-4-7
   - Implement the fix -> claude-opus-4-6 or Minimax-2.7
   - Generate tests -> claude-opus-4-6
   - Repetitive lint/format/codemod cleanup -> DeepSeek-V3.2-Reasoner

5. **Show your work.** When you recommend a model to the user, include:
   - The chosen model and a one-line justification.
   - Expected cost per task (from the table) and any quality tradeoff.
   - A link to https://index.openhands.dev so they can verify or pick differently.

## Heuristics & caveats

- **Pareto frontier matters more than headline score.** A model that is 95% as
  accurate at 20% of the cost is almost always the right starting point.
- **Numbers age fast.** Treat the table as a current-as-of-May-2026 snapshot.
  When in doubt, re-check the relevant category page on
  https://index.openhands.dev before committing to a model for a long-running
  job.
- **One-shot vs. multi-turn.** The index measures agent runs, not raw
  completions. If you only need a single classification or a short summary, the
  cost gap shrinks and any capable cheap model is fine.
- **Open vs. closed models.** Minimax-2.7, DeepSeek-V3.2-Reasoner, GLM-5/5.1,
  Qwen3.6, and Kimi are open-weights options if self-hosting or data residency
  matters. Gemini, GPT-5.x, and claude-opus are closed.
- **Greenfield is expensive everywhere.** Even the cost pick is ~$4 per problem
  because these are long, multi-step builds. Budget accordingly or scope down.

## Category pages on the OpenHands Index

- Issue Resolution: https://index.openhands.dev/issue-resolution
- Greenfield: https://index.openhands.dev/greenfield
- Frontend: https://index.openhands.dev/frontend
- Testing: https://index.openhands.dev/testing
- Information Gathering: https://index.openhands.dev/information-gathering
- Overall leaderboard: https://index.openhands.dev/
