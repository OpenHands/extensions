# model-router

A small OpenHands skill that recommends the most cost-efficient LLM for a given
task category, using benchmark data from the public [OpenHands
Index](https://index.openhands.dev).

## What it does

When the agent (or user) needs to pick a model, this skill provides a quick
lookup table mapping task type to:

- **Cost pick** - best score-per-dollar on the Pareto frontier
- **Balanced pick** - good score at moderate cost
- **Premium pick** - top raw score, ignore cost

Categories covered (matching the OpenHands Index):

- Research / Information gathering
- Bug fixing / Issue resolution
- Planning / Architecture / Greenfield builds
- Frontend / UI
- Testing / Test generation
- Bulk repetitive work (cheap reasoning at scale)

## When it triggers

This skill activates on keyword cues like "which model", "pick a model",
"cost-efficient model", "best model for ...", or "model router". The agent can
also load it on demand when it needs to recommend or switch models, for example
when configuring a sub-agent or delegating a cloud conversation.

## Example output

If the user asks "which model should I use for deep research across multiple
sites?", the agent (with this skill loaded) should answer with something like:

> Use **Gemini-3.1-Pro** ($0.12 per task, score 76.4 on GAIA via OpenHands
> Index). If you need the absolute best quality and don't mind paying ~6x more,
> switch to GPT-5.5 ($0.74, 86.1). Source: https://index.openhands.dev/information-gathering

## Why this exists

LLM cost per task varies by 10x or more across the Pareto frontier. Defaulting
to a single premium model for every step of an agent run leaves a lot of money
on the table when cheaper models reach 90%+ of the quality on most subtasks.
This skill encodes a few sensible defaults so the agent can route work to the
right model without having to re-derive the tradeoff each time.

## Caveats

- Numbers are a May 2026 snapshot from index.openhands.dev. Re-check the index
  before committing to a model for a long-running production job.
- The benchmark measures full agent runs, not raw completions. For one-shot
  classifications or short summaries, almost any capable cheap model is fine.
- Whether your runtime can actually switch models mid-conversation depends on
  how OpenHands is deployed (sub-agents, delegated cloud conversations, or just
  the user choosing a model when starting a session).
