# Set Up PR Review

Add automated AI code review to a GitHub repository.

## Triggers

This skill is activated by the following keywords:

- `setup-pr-review`
- `set up pr review`
- `add code review workflow`
- `openhands pr review`

## What This Does

Creates a `.github/workflows/pr-review.yml` file that triggers an OpenHands agent to review pull requests and post inline comments. Walks you through configuration options:

- **Review style** — `roasted` (blunt, Torvalds-style) or `standard` (balanced)
- **When to trigger** — on-demand (label or reviewer request) or automatic (every PR)
- **Which model** — any litellm-supported model, with optional A/B testing
- **Evidence requirement** — optionally require proof-of-work in PR descriptions

You'll need to add an `LLM_API_KEY` secret to your repository settings — the skill tells you exactly where.
