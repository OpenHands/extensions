# Slack Channel Monitor

Create a cron automation that polls up to 10 Slack channels every minute and
starts an OpenHands conversation whenever a configurable trigger phrase is
detected.

## Triggers

This skill is activated by keywords:

- `monitor a Slack channel`
- `watch Slack for messages`
- `Slack bot that responds to mentions`
- `OpenHands Slack integration`
- `trigger OpenHands from Slack`
- `respond to @openhands in Slack`
- `poll Slack channels`

## Features

- **Token auto-detection**: works with a bot token (`SLACK_BOT_TOKEN`) or a
  user token (`SLACK_USER_TOKEN`); informs the user if neither is present
- **Channel name resolution**: resolves `#channel-name` to IDs, with graceful
  handling of permission errors
- **Configurable trigger phrase**: defaults to `@openhands`; any low-collision
  phrase works (e.g. `jazz hands`, `take-me-to-funky-town`)
- **Efficient polling**: single `search.messages` call for multi-channel user
  tokens with `search:read`; falls back to one `conversations.history` call
  per channel for bot tokens
- **Triggered follow-ups**: Slack thread replies that repeat the trigger phrase
  are forwarded to the existing OpenHands conversation
- **Watch window**: completed conversations keep watching their Slack thread for
  short follow-up periods, with quiet threads backed off automatically
- **Reaction acknowledgement**: adds a 👀 to every message containing the
  trigger phrase
- **Conversation link**: posts a link to the new conversation in the Slack
  thread immediately on trigger detection
- **Automatic summaries**: when the conversation reaches a terminal state the
  agent's final response is posted back to the thread; error/stuck states
  receive a clear error notice
- **Persistent state**: conversation tracking and poll timestamps are stored
  in `automation-state/slack_poller_{automation_id}.json` across runs

## Prerequisites

Set at least one of the following in **OpenHands Settings - Secrets**:

| Secret | Token type | Minimum scopes |
|--------|-----------|----------------|
| `SLACK_BOT_TOKEN` | Bot (`xoxb-`) | `channels:history`, `channels:read`, `reactions:write`, `chat:write` |
| `SLACK_USER_TOKEN` | User (`xoxp-`) | Same as bot, plus `search:read` for multi-channel efficiency |

Optional:

| Secret | Default | Purpose |
|--------|---------|---------|
| `OPENHANDS_URL` | `http://localhost:8000` | Base URL for conversation links posted in Slack |

## Quick Start

Ask OpenHands:

> "Monitor the #dev-help and #support Slack channels and start a conversation
> whenever someone says @openhands"

The skill will:

1. Verify your Slack token is available
2. Resolve channel names to IDs
3. Confirm the trigger phrase (or use the default `@openhands`)
4. Generate and upload a customised automation script by copying the template
   and changing only the configuration constants
5. Create the automation with cron schedule `* * * * *`

## How It Works

Each cron run (every minute):

1. Fetches new messages from all monitored channels
2. Adds 👀 to any message containing the trigger phrase
3. Creates an OpenHands conversation with the message and recent channel
   context as the initial prompt; posts a link to the conversation in the
   Slack thread
4. Forwards triggered replies in tracked threads to the existing conversation,
   while ignoring replies that do not contain the trigger phrase
5. Checks active conversations - posts the agent's final response back to
   Slack when the conversation completes, then watches briefly for triggered
   follow-up replies

## See Also

- [SKILL.md](SKILL.md) - Full setup workflow and runtime behaviour reference
- [references/slack-api.md](references/slack-api.md) - Token types, required
  scopes, endpoint reference, and rate limits
- [references/state-schema.md](references/state-schema.md) - State file schema
  and conversation lifecycle diagram
