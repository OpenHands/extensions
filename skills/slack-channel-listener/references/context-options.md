# Context options - what the agent sees

By default the agent receives a structured preamble like:

```
You were triggered by a Slack message in #tim-test-openhands-5.
Triggering user: @tim
Permalink: https://example.slack.com/archives/C.../p...

Thread context (3 prior messages):
  @alice: ...
  @bob: ...
  @tim: ...

Triggering message:
  @tim: @thems-fightin-words please summarise the design discussion above.

Treat the triggering message (with the trigger phrase stripped) as the
user's request and respond to it. When you finish, return your final
answer as your last assistant message - the automation will post it back
to Slack as a threaded reply automatically.
```

Each piece is gated by a configuration flag.

## Flags

| Variable | Default | Effect |
|---|---|---|
| `SLACK_INCLUDE_THREAD_CONTEXT` | `true` | If the triggering message is inside a thread, fetch the parent + prior replies (up to 50) and include them. Adds one `conversations.replies` call. |
| `SLACK_INCLUDE_CHANNEL_RECENT` | `0` | Number of channel messages before the trigger to include. `0` disables. Adds one `conversations.history` call. |
| `SLACK_RESOLVE_USER_IDS` | `true` | Replace `<@U12345>` with `@DisplayName`. Adds one `users.info` call per unique user (cached for the run). |

## Things you might want next (not yet implemented)

These would be additive and live behind their own flags:

| Idea | Sketch |
|---|---|
| `SLACK_INCLUDE_FILES` | Pass `files` metadata from the message (name, mimetype, `url_private`) into the prompt; agent can fetch with the bot token. |
| `SLACK_INCLUDE_REACTIONS` | Pass current reactions on the trigger and thread messages - sometimes a useful priority / sentiment signal. |
| `SLACK_INCLUDE_CHANNEL_TOPIC` | Pull the channel topic/purpose from `conversations.info` so the agent understands the channel's role. |
| `SLACK_STRIP_TRIGGER` | Remove the trigger phrase from the triggering message before passing it to the agent. (Today the agent is told to ignore it.) |

PRs welcome - keep each behind a flag with a safe default.

## Cost considerations

Every extra API call before the agent runs adds latency to the user's
threaded reply. Rough numbers:

- `chat.getPermalink`: ~50 ms.
- `users.info`: ~100 ms each, mostly Slack roundtrip.
- `conversations.replies` (thread context): ~200 ms.
- `conversations.history` (channel context): ~200 ms.

These are all under a second in aggregate for a typical message, but if
you crank `SLACK_INCLUDE_CHANNEL_RECENT` very high or `resolve_user_ids`
across a long thread, you'll feel it. Profile before adding more
enrichment.
