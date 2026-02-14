# Discord

Build and automate Discord integrations (bots, webhooks, slash commands, and REST API workflows). Use when the user mentions Discord, a Discord server/guild, channels, webhooks, bot tokens, slash commands/application commands, discord.js, or discord.py.

## Triggers

This skill is activated by the following keywords:

- `discord`
- `discord api`
- `discord bot`
- `discord webhook`
- `discord.js`
- `discord.py`
- `slash command`
- `application command`
- `guild id`
- `channel id`

## Details

This skill focuses on practical Discord automation patterns:

- Prefer **incoming webhooks** for one-way notifications.
- Use **bot tokens + REST API** for richer automation.
- Handle **rate limits** (HTTP 429) by waiting `retry_after` before retrying.

See also: `references/REFERENCE.md`.
