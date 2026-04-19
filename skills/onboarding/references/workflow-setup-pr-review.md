# Set Up PR Review — `setup-pr-review`

Add the OpenHands PR review workflow to a GitHub repository so an agent can
review pull requests and post inline comments.

**Docs**: https://docs.all-hands.dev/sdk/guides/github-workflows/pr-review

## Step 1: Create the workflow file

Create `.github/workflows/pr-review.yml`. Fetch the latest example from the
docs and use it as the starting template.

## Step 2: Configure the LLM

Ask the user whether they use the **OpenHands app** or their **own LLM provider**.

**OpenHands app**: Tell them to get an LLM key from
https://app.all-hands.dev → Account → API Keys → OpenHands LLM Key, add it as
a GitHub secret named `LLM_API_KEY`. Set `llm-model: litellm_proxy/claude-sonnet-4-5-20250929`
and `llm-base-url: https://llm-proxy.app.all-hands.dev`.

**Own LLM provider**: Add their API key as `LLM_API_KEY` secret. Set `llm-model`
to the provider-prefixed model name (e.g. `anthropic/claude-sonnet-4-5-20250929`).

**You cannot create secrets — the user must do it manually.**

## Step 3: Ask the user for preferences

- **Review style**: `roasted` (blunt, Torvalds-style) or `standard` (balanced)
- **When to trigger**: on-demand (add `review-this` label or request reviewer) or automatic (every new PR)
