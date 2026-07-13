# Dreaming

Create an automation that periodically distills a chosen local OpenHands
conversation into a target repository's `AGENTS.md` via Letta memory
reflection, opening or updating a pull request with what it learned.

## Trigger

This skill is activated by:

- `/dreaming:setup`

## How it works

- At setup you name a conversation; the skill resolves it to a conversation
  id from local conversation metadata.
- On each cron run, a persistent Letta "dreamer" agent reflects on whatever
  is new in that conversation and updates the doc in a temporary checkout of
  the target repo (already-reflected messages are deduplicated).
- If the doc changed, the automation commits and opens (or updates) a PR.
- The automation tarball is a thin wrapper (two small scripts); all logic
  lives in the pinned npm package `@letta-ai/openhands-dreaming`.

MVP scope: **local Agent Canvas conversations only** (the automation polls on
your laptop). Cloud conversation sources are not supported yet.

## Prerequisites

Set these in OpenHands Settings -> Secrets:

- `GITHUB_TOKEN` with write access to the target repo
- The API key for the chosen model's provider (e.g. `ANTHROPIC_API_KEY`) -
  note this is separate from OpenHands' own LLM configuration

## Quick Start

Ask OpenHands:

> "Set up Dreaming over my 'payment refactor' conversation for the
> `myorg/backend` repo using `anthropic/opus-4.8`."

## See Also

- [SKILL.md](SKILL.md) - Full setup workflow reference
