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
and use it as the starting template. The workflow calls the
`OpenHands/extensions/plugins/pr-review` composite action directly.

## Step 2: Configure the LLM

Ask the user whether they are using the **OpenHands app** (app.all-hands.dev)
or their **own LLM provider** (e.g. Anthropic, OpenAI directly).

### OpenHands app (default)

OpenHands app users already have access to an LLM API key through the
OpenHands litellm proxy. Tell them:

> Go to https://app.all-hands.dev → Account → API Keys → OpenHands LLM Key, and copy your key.
> Then add it as a GitHub repository secret:
> Settings → Secrets and variables → Actions → New repository secret.
> Name it `LLM_API_KEY`.

Set these inputs in the workflow `with:` block:
- `llm-model: litellm_proxy/claude-sonnet-4-5-20250929`
- `llm-base-url: https://llm-proxy.app.all-hands.dev`

### Own LLM provider

If the user has their own API key (e.g. from Anthropic or OpenAI), tell them
to add it as a repository secret named `LLM_API_KEY` using the same path
above. Leave `llm-base-url` unset and set `llm-model` to the provider-prefixed
model name (e.g. `anthropic/claude-sonnet-4-5-20250929`).

**You cannot create secrets — the user must do it manually.** Do not ask for
the key value. Just tell them where to put it.

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

After applying these, ask the user if they want to explore additional options
(model selection, evidence requirements, custom review skills, observability).
If yes, walk them through it — use the docs as a reference:
https://docs.all-hands.dev/sdk/guides/github-workflows/pr-review
If not, you're done.
