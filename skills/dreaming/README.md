# Dreaming

Create an automation that periodically distills your local OpenHands Agent
Canvas coding sessions into a target repository's `AGENTS.md` via Letta
memory reflection, opening or updating a pull request with what it learned.

## Trigger

This skill is activated by:

- `/dreaming:setup`

## How it works

- A cron automation sweeps new local Agent Canvas conversations since the
  last run.
- A persistent Letta "dreamer" agent reflects on them and updates the doc in
  a temporary checkout of the target repo.
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

> "Set up Dreaming for my `myorg/backend` repo using `anthropic/opus-4.8`."

## See Also

- [SKILL.md](SKILL.md) - Full setup workflow reference
