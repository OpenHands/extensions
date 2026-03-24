---
name: setup-pr-review
description: Set up the OpenHands automated PR review workflow in a GitHub repository. Creates the workflow file and asks the user for configuration preferences. Use when a user wants AI code review on their pull requests.
triggers:
- setup-pr-review
- set up pr review
- add code review workflow
- openhands pr review
---

# Set Up OpenHands PR Review

Add the PR review workflow to a GitHub repository so an OpenHands agent can
review pull requests and post inline comments.

**Docs**: https://docs.all-hands.dev/sdk/guides/github-workflows/pr-review

## Step 1: Create the workflow file

Create `.github/workflows/pr-review.yml` in the target repo. Fetch the latest
example from https://docs.all-hands.dev/sdk/guides/github-workflows/pr-review
and use it as the starting template. The workflow checks out the
`OpenHands/extensions` repo and runs the `plugins/pr-review` composite action.

Key elements the workflow must have:
- `on.pull_request` with appropriate trigger types
- `permissions`: `contents: read`, `pull-requests: write`, `issues: write`
- `concurrency` group per PR number with `cancel-in-progress: true`
- `uses: ./plugins/pr-review` with `llm-model`, `review-style`, `llm-api-key`,
  and `github-token`

## Step 2: Tell the user to add the secret

The workflow requires an `LLM_API_KEY` repository secret. **You cannot create
this — the user must do it manually.**

Tell them:

> To activate the workflow, add your LLM API key as a GitHub repository secret:
> Settings → Secrets and variables → Actions → New repository secret.
> Name it `LLM_API_KEY`. The `GITHUB_TOKEN` is provided automatically.

Do not ask the user for the key value. Just tell them where to put it.

## Step 3: Ask the user for preferences

Present these options and apply any requested changes to the workflow file:

**Review style** (default: `roasted`)
- `roasted` — Linus Torvalds-style, blunt, focuses on data structures and
  simplicity.
- `standard` — balanced, covers style/readability/security.

**When to trigger** (default: on-demand only)
- On-demand: add `review-this` label or request `openhands-agent` as reviewer.
- Automatic: review every new PR. Add `opened` and `ready_for_review` to
  `on.pull_request.types` and matching conditions to the `if:` block.

**Which model** (default: `anthropic/claude-sonnet-4-5-20250929`)
- Any model supported by litellm. Can be a comma-separated list for A/B testing
  (one model selected randomly per review).

**Evidence requirement** (default: `false`)
- When `true`, the reviewer checks the PR description for an Evidence section
  (screenshots for frontend, command output for backend).

## Step 4: Verify

Confirm:
- `.github/workflows/pr-review.yml` exists and is valid YAML
- The `if:` conditions match the triggers in `on.pull_request.types`
- The `secrets.LLM_API_KEY` reference is present in the `with:` block
