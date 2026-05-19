---
name: slack-channel-listener
description: >-
  Set up an OpenHands automation that listens to a Slack channel (or many)
  for a configurable trigger phrase and starts a new agent conversation
  whenever someone posts it, replying threaded to the triggering message.
  Supports both Slack Events API (push) for publicly-reachable backends and
  cron polling for laptops and firewalled environments.
triggers:
  - slack channel listener
  - slack listener automation
  - listen to slack channel
  - slack trigger phrase
  - slack mention automation
  - /slack-listener
---

# slack-channel-listener

Create an OpenHands automation that watches one or more Slack channels for a
configurable trigger phrase (for example `@thems-fightin-words`, `/triage`,
`hey openhands`) and starts a new agent conversation per match. The agent's
final answer is posted back as a threaded reply to the triggering message.

## Decision flow

Walk the user through these decisions in order. Do not silently pick - ask
each question explicitly and confirm before creating anything.

### Step 1 - confirm goal and trigger phrases

Ask:

1. What channel(s) should be monitored? (one ID, several IDs, "all public
   channels the bot can see", or "every channel my user account can see")
2. What trigger phrase(s) should activate the agent? (one or more strings,
   case-insensitive substring match)
3. Where will this automation run? (OpenHands Cloud, self-hosted with public
   ingress, or a laptop / firewalled host)

Surface that trigger phrases match anywhere in the message text - if they
need exact `@mention` semantics, recommend a leading `@`.

### Step 2 - pick push vs poll

Use this table:

| User's runtime | Recommended | Why |
|---|---|---|
| OpenHands Cloud | Push (Events API) | Backend is publicly reachable; lowest latency. |
| Self-hosted with public HTTPS ingress | Push | Same. Confirm the ingress can receive POST from Slack. |
| Laptop / firewalled host / unsure | Poll | Outbound HTTPS only; works everywhere. |

If the user is unsure whether their backend is reachable, prefer **poll** -
no Slack-app changes are needed.

For multi-channel scope `all-accessible`, **poll is the only mode that
makes sense**; push requires the bot to be invited to each channel. Explain
this and recommend `search.messages` with a user token (requires
`search:read`).

### Step 3 - reply behaviour

Default: `thread` (post the agent's final assistant message as a threaded
reply). Offer `thread+reaction` (also leaves a `👀` reaction on start and a
`✅` on success / `⚠️` on failure) and `none` (silent).

### Step 4 - context options

Defaults are sensible; offer to change only if the user asks. See
`references/context-options.md` for the full list. Common toggles:

- `SLACK_INCLUDE_THREAD_CONTEXT=true` (default) - pull prior thread replies
  when the trigger is inside a thread.
- `SLACK_INCLUDE_CHANNEL_RECENT=0` (default) - set to N to include the N
  most recent channel messages as background.

### Step 5 - gather credentials

You will need:

- A Slack **bot token** (`xoxb-...`) with scopes:
  - `chat:write` - to post the reply.
  - `reactions:read`, `reactions:write` - to mark progress (and, in poll
    mode, for the reaction-based state machine).
  - `channels:history` - to read public channel messages.
  - `groups:history` - if monitoring private channels.
  - `users:read` - if `resolve_user_ids` is enabled (default on).
- For push mode: a Slack **signing secret** and a Slack app with Event
  Subscriptions enabled. Walkthrough: `references/push-setup.md`.
- For poll mode with `scope=all-accessible`: a Slack **user token**
  (`xoxp-...`) with `search:read`. Walkthrough: `references/poll-setup.md`.
- An OpenHands API key (`OPENHANDS_API_KEY` / `OPENHANDS_CLOUD_API_KEY`) for
  the automation API itself.

**Never echo secrets back to the user verbatim** - confirm by length or
prefix instead. Store them as automation environment variables, not in the
tarball.

### Step 6 - assemble and upload

Build a custom-automation tarball that contains the contents of
`plugins/slack-reply/scripts/`. The entrypoint is:

- Push mode: `python agent_event.py`, setup `setup.sh`, trigger `event`.
- Poll mode: `python agent_poll.py`, setup `setup.sh`, trigger `cron`.

See `references/tarball-build.md` for the full step-by-step (fetch the
plugin from this repo, tar it up, upload, then create the automation).

### Step 7 - verify

- Push mode: ask the user to confirm Slack URL verification succeeded
  (Slack's *Event Subscriptions* page shows "Verified" with a green tick).
  Have them post a test message containing the trigger phrase and wait for
  the threaded reply.
- Poll mode: manually dispatch a run via the Automations API and check
  that messages older than `SLACK_POLL_LOOKBACK_MINUTES` aren't acted on.

## Non-goals (out of scope for this skill)

- Interactive Slack components (buttons, modals, slash commands) - the agent
  responds with plain text only.
- Streaming partial agent output to Slack - the reply is posted once when
  the agent goes idle. Update the prompt if you want progress updates.
- Per-user permission enforcement - any user posting the trigger phrase in
  an allowed channel will spawn a conversation. If you need allow/deny
  lists, add a filter to the automation trigger (push) or extend
  `Config.matches_phrase` (poll).

## See also

- `plugins/slack-reply` - the Python building blocks that this skill
  assembles into a tarball.
- `skills/openhands-automation` - the underlying automation API.
- `references/push-setup.md`, `references/poll-setup.md`,
  `references/multi-channel.md`, `references/context-options.md`,
  `references/tarball-build.md` - in this directory.
