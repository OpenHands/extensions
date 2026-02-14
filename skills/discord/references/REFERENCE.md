# Discord reference

## Official docs

- Discord Developer Docs (home): https://discord.com/developers/docs/intro
- REST API versioning: `https://discord.com/api/v10` (use v10 endpoints)
- Create Message (REST): https://discord.com/developers/docs/resources/channel#create-message
- Webhooks: https://discord.com/developers/docs/resources/webhook
- OAuth2: https://discord.com/developers/docs/topics/oauth2
- Application Commands (slash commands): https://discord.com/developers/docs/interactions/application-commands
- Rate limits: https://discord.com/developers/docs/topics/rate-limits

## Footguns / gotchas

- Incoming webhook URLs contain a secret token; treat the entire URL like a password.
- If you include request URLs in error logs, sanitize `/webhooks/{id}/{token}` (the token is secret).
- Use `allowed_mentions` to prevent accidental mass pings.
- Respect rate limits. Don’t spin in tight retry loops on 429.

## Common workflows

### 1) Simple notifications (incoming webhook)

1. Create an incoming webhook in the Discord client (channel settings → Integrations → Webhooks).
2. Store it in `DISCORD_WEBHOOK_URL`.
3. POST JSON like `{ "content": "..." }`.

Key points from Discord docs:
- Execute webhook: `POST /webhooks/{webhook.id}/{webhook.token}`.
- Must include at least one of `content`, `embeds`, `components`, `file`, or `poll`.
- Content limit is 2000 characters.
- Use `allowed_mentions` to prevent accidental pings.

### 2) Bot token + REST API

1. Create an app + bot user in the Discord Developer Portal.
2. Invite the bot to a guild using an OAuth2 URL with the `bot` scope.
3. Use `Authorization: Bot $DISCORD_BOT_TOKEN` for REST calls.

For posting messages:
- `POST /channels/{channel_id}/messages`

Helpful debugging hints:
- 401: invalid token / wrong auth header format
- 403: missing permissions in channel (e.g., Send Messages)
- 404: wrong ID or bot doesn’t have access to channel

### 3) Slash commands / interactions

- Command registration is done via HTTP endpoints.
- Use guild commands during development for instant updates.
- If you implement the HTTP interactions endpoint yourself, you must verify request signatures.

### 4) OAuth2 notes

Discord strongly recommends using the `state` parameter to prevent CSRF.

OAuth2 endpoints require `application/x-www-form-urlencoded` content type; JSON is not permitted.

### 5) Rate limits

Don’t hard-code limits; parse headers like:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset-After`
- `X-RateLimit-Bucket`

On HTTP 429:
- Read `Retry-After` / JSON `retry_after`, wait, then retry.

## Suggested environment variables

- `DISCORD_WEBHOOK_URL`
- `DISCORD_BOT_TOKEN`
- `DISCORD_CHANNEL_ID` (optional convenience)
- `DISCORD_GUILD_ID` (optional, for command registration)
- `DISCORD_APPLICATION_ID` (optional, for command registration)
