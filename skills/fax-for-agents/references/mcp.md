[![Fax for Agents](https://faxforagents.com/brand/logo-512.png)](https://faxforagents.com/)

# Fax for Agents MCP setup

Send and receive faxes through an API or MCP tools.

[Site](https://faxforagents.com/) | [Docs](https://faxforagents.com/docs/quickstart/) | [MCP](https://faxforagents.com/mcp/) | [Dashboard](https://app.faxforagents.com/) | [Pricing](https://faxforagents.com/pricing/) | [Changelog](https://faxforagents.com/changelog/)

[![MIT licence](https://img.shields.io/badge/licence-MIT-1f6feb)](https://github.com/faxforagents/skills/blob/main/LICENSE)
[![Agent Skills](https://img.shields.io/badge/format-Agent%20Skills-6b4fbb)](https://agentskills.io/)

Licence: [MIT](https://github.com/faxforagents/skills/blob/main/LICENSE).

## Connection options

The hosted endpoint is `https://mcp.faxforagents.com/mcp/`.
Keep the trailing slash.
It supports OAuth 2.1 and API key authentication.
Complete the client's browser consent flow for OAuth.
Skill installation alone does not create that connection.

Stdio runs `npx -y faxforagents-mcp` with Node.js 20 or later.
Set `FAXFORAGENTS_API_KEY` using the [skill's setup instructions](../SKILL.md#setup).
Choose one transport per client.
The following commands configure clients and can persist credentials in their local settings.
Keep those settings out of source control.

## Claude Code

Hosted OAuth:

```bash
claude mcp add --transport http faxforagents https://mcp.faxforagents.com/mcp/
```

Open `/mcp` in Claude Code and authenticate the server.

Hosted API key alternative:

```bash
claude mcp add --transport http faxforagents https://mcp.faxforagents.com/mcp/ --header "Authorization: Bearer $FAXFORAGENTS_API_KEY"
```

Stdio alternative:

```bash
claude mcp add faxforagents -e "FAXFORAGENTS_API_KEY=$FAXFORAGENTS_API_KEY" -- npx -y faxforagents-mcp
```

## Codex

Hosted OAuth:

```bash
codex mcp add faxforagents --url https://mcp.faxforagents.com/mcp/
codex mcp login faxforagents
```

Hosted API key alternative:

```bash
codex mcp add faxforagents --url https://mcp.faxforagents.com/mcp/ --bearer-token-env-var FAXFORAGENTS_API_KEY
```

Stdio alternative:

```bash
codex mcp add faxforagents --env "FAXFORAGENTS_API_KEY=$FAXFORAGENTS_API_KEY" -- npx -y faxforagents-mcp
```

See [Codex MCP configuration](https://developers.openai.com/codex/mcp).

## Cursor

Merge this into `.cursor/mcp.json`, or use Cursor's global MCP settings.
Authenticate through Cursor after enabling the hosted server.

```json
{
  "mcpServers": {
    "faxforagents": {
      "url": "https://mcp.faxforagents.com/mcp/"
    }
  }
}
```

For stdio, use this entry instead.
Cursor reads the exported API key through environment interpolation.

```json
{
  "mcpServers": {
    "faxforagents": {
      "command": "npx",
      "args": ["-y", "faxforagents-mcp"],
      "env": {
        "FAXFORAGENTS_API_KEY": "${env:FAXFORAGENTS_API_KEY}"
      }
    }
  }
}
```

See [Cursor MCP configuration](https://cursor.com/docs/context/mcp).

## OpenClaw

Hosted OAuth:

```bash
openclaw mcp add faxforagents --url https://mcp.faxforagents.com/mcp/ --transport streamable-http --auth oauth
openclaw mcp login faxforagents
```

Stdio alternative:

```bash
openclaw mcp add faxforagents --command npx --arg -y --arg faxforagents-mcp --env "FAXFORAGENTS_API_KEY=$FAXFORAGENTS_API_KEY"
```

These commands require an OpenClaw version with the documented MCP registry commands.
See [OpenClaw server configuration](https://docs.openclaw.ai/cli/mcp/registry) and [OAuth setup](https://docs.openclaw.ai/cli/mcp/transports).

## Hermes

Hosted OAuth:

```bash
hermes mcp add faxforagents --url https://mcp.faxforagents.com/mcp/ --auth oauth
hermes mcp login faxforagents
```

Stdio alternative:

```bash
hermes mcp add faxforagents --command npx --env "FAXFORAGENTS_API_KEY=$FAXFORAGENTS_API_KEY" --args -y faxforagents-mcp
```

Keep `--args` last because it consumes the remaining arguments.
See [Hermes MCP guidance](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) and its [CLI definitions](https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/subcommands/mcp.py).

## Verify

Reload the client's server list.
Confirm all 15 tools listed in [SKILL.md](../SKILL.md#hosted-tools).
Call `get_fax_capabilities` and confirm the credential environment before sending.
For sandbox testing, use an `ffa_test_` key and `+15550000001`.
Follow the skill's approval and untrusted-text rules.

The API key and stdio forms follow the [MCP README](https://github.com/faxforagents/mcp#connect).
Client commands were checked against documentation, without authenticated client sessions.
