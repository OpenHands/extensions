# slack-channel-listener

Set up an OpenHands automation that watches a Slack channel (or many) for a
configurable trigger phrase, runs an agent conversation in response, and
posts the agent's final answer back as a threaded reply.

## Two trigger styles

| Style | When to use | Setup cost |
|---|---|---|
| **Push** (Slack Events API webhook) | Backend is publicly reachable from Slack (OpenHands Cloud, or self-hosted with HTTPS ingress). Lowest latency. | Slack app with Event Subscriptions + signing secret. |
| **Poll** (cron + `conversations.history` or `search.messages`) | Laptop, corporate firewall, or any host without inbound HTTPS. Higher latency = cron interval. | Just a bot/user token; no Slack-app changes. |

The skill auto-detects which path to recommend based on the user's runtime.

## What gets created

- A **custom-automation** tarball uploaded to the OpenHands Automations API.
- One automation per channel scope, with these environment variables baked in:
  - `SLACK_BOT_TOKEN`, optional `SLACK_USER_TOKEN`
  - `SLACK_TRIGGER_PHRASES` (comma-separated)
  - `SLACK_CHANNEL_SCOPE` and one of `SLACK_CHANNEL_ID` / `SLACK_CHANNEL_IDS`
  - `SLACK_REPLY_MODE`, context flags, reaction names
- For push mode: a custom webhook source registered on the automation
  backend (the skill prints the webhook URL the user must paste into Slack's
  *Event Subscriptions* page).

See `SKILL.md` for the guided flow and the files under `references/` for
deep-dives on each path.

## Status

Draft / first iteration. Multi-channel `all-public` and `all-accessible`
modes work end-to-end but have only been exercised against a small Slack
workspace; expect refinements as the skill gets more usage. See the open PR
on `OpenHands/extensions` for known follow-ups.
