---
name: slack-reply
description: >-
  Building blocks for Slack-triggered OpenHands automations. Provides the
  agent entrypoint scripts, Slack API helpers, prompt assembly from a Slack
  event payload, and a post-run threaded reply back to the triggering
  message. Intended to be packaged into a custom-automation tarball by the
  `slack-channel-listener` skill, not loaded directly into a Conversation.
triggers:
  - slack reply
  - slack thread reply
  - slack-reply plugin
---

# slack-reply

A reusable bundle of Python scripts that turn an incoming Slack message into an
OpenHands `Conversation` run and post the agent's final reply back as a
threaded message.

This plugin is **not** a runtime `Plugin` you load via `PluginSource(...)` -
it is a code template consumed by the `slack-channel-listener` skill, which
copies these scripts into a custom-automation tarball and uploads it via the
OpenHands Automations API.

## Contents

| File | Purpose |
|---|---|
| `scripts/setup.sh` | Installs `uv`, the OpenHands SDK, and `slack_sdk` in the automation sandbox. |
| `scripts/slack_client.py` | Thin wrappers over the Slack Web API: history, replies, postMessage, reactions, permalinks, user resolution. |
| `scripts/prompt.py` | Turns a Slack event payload (or polled message) plus optional thread/channel context into the initial agent prompt. |
| `scripts/agent_event.py` | Entrypoint for **push-mode** automations. Reads the Slack event from `AUTOMATION_EVENT_PAYLOAD`, runs the agent, posts the result back. |
| `scripts/agent_poll.py` | Entrypoint for **poll-mode** automations. Scans matching messages since the configured lookback, claims each via the state store, runs the agent, posts the result back. |
| `scripts/state.py` | Pluggable state store with two backends: `KVApiStore` (preferred, uses the platform automation KV store; activated when `AUTOMATION_KV_TOKEN` is set per [OpenHands/automation#69](https://github.com/OpenHands/automation/pull/69)) and `SQLiteStore` (fallback, writes to `$SLACK_STATE_DIR/slack-listener.sqlite3`). Used by poll-mode for idempotent claim/done/failed bookkeeping across cron runs. |
| `scripts/config.py` | Loads automation-level config (trigger phrases, channel scope, context options, reply behaviour, state directory) from environment variables. |

## Configuration (environment variables read at runtime)

All variables are baked into the automation by `slack-channel-listener` when
it creates the automation; users should not edit them by hand.

| Variable | Required | Meaning |
|---|---|---|
| `SLACK_BOT_TOKEN` | yes (push + poll) | Bot token with `chat:write`, `reactions:read`, `reactions:write`, and the appropriate `channels:history` / `groups:history` / `search:read` scopes. |
| `SLACK_TRIGGER_PHRASES` | yes | Comma-separated list of phrases that activate the agent (case-insensitive substring match, e.g. `@thems-fightin-words,/triage`). |
| `SLACK_CHANNEL_SCOPE` | yes | One of `single` (then `SLACK_CHANNEL_ID` must be set), `list` (`SLACK_CHANNEL_IDS` comma-separated), `all-public`, `all-accessible`. |
| `SLACK_CHANNEL_ID` | conditional | Single channel ID when scope = `single`. |
| `SLACK_CHANNEL_IDS` | conditional | Comma-separated channel IDs when scope = `list`. |
| `SLACK_INCLUDE_THREAD_CONTEXT` | no (default `true`) | If the trigger is inside a thread, include the parent + prior replies in the prompt. |
| `SLACK_INCLUDE_CHANNEL_RECENT` | no (default `0`) | Include this many recent channel messages before the trigger as context. |
| `SLACK_RESOLVE_USER_IDS` | no (default `true`) | Replace `<@U…>` mentions with `@DisplayName` in the assembled prompt. |
| `SLACK_REPLY_MODE` | no (default `thread`) | `none` (don't post back), `thread` (threaded reply under triggering message), `thread+reaction` (also adds a `👀` on start and `✅` on finish). |
| `SLACK_ACK_REACTION` | no (default `eyes`) | Reaction emoji posted when work starts (used by `thread+reaction`). |
| `SLACK_DONE_REACTION` | no (default `white_check_mark`) | Reaction emoji posted on success. |
| `SLACK_FAIL_REACTION` | no (default `warning`) | Reaction emoji posted on failure. |
| `SLACK_POLL_LOOKBACK_MINUTES` | no (default `15`) | Poll mode only: how far back the cron run scans for matching messages on each tick. Set comfortably above your cron interval. |
| `SLACK_STATE_DIR` | no (default `/automation/storage/state`) | Poll mode only, SQLite backend only: directory holding `slack-listener.sqlite3`. Must survive across automation runs. If the path isn't writable, the script falls back to a tempdir and logs a warning (state will not persist). Ignored when the platform KV store is available. |
| `AUTOMATION_KV_TOKEN` | injected by the dispatcher | Poll mode only, KV backend selector: when present (i.e. the automation was created with `enable_kv_store: true` on a runtime that ships [OpenHands/automation#69](https://github.com/OpenHands/automation/pull/69)) state is persisted via the platform KV store and `SLACK_STATE_DIR` is ignored. |
| `AUTOMATION_API_URL` / `OPENHANDS_CLOUD_API_URL` | injected by the dispatcher | Base URL the KV backend talks to. Resolved in that order; if neither is set the KV backend cannot start. |

## How "post on idle" works

The script awaits `conversation.run()` (which blocks until the agent
terminates - finished, awaiting user input, or errored) and then reads the
last assistant message from `conversation.state.events`. There is no
in-Conversation hook system needed for this; the post-run boundary in the
script is the idle boundary.

For error paths (exception during `run()`, or the agent leaving in
`AgentExecutionStatus.ERROR`), the script posts a short failure summary with
the `SLACK_FAIL_REACTION`. This guarantees the user gets a reply on Slack
even when the agent fails.

## See also

- `skills/slack-channel-listener` - the guided flow that uses this plugin.
- `skills/openhands-automation` - the underlying automation API documentation.
