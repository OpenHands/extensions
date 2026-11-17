[![Fax for Agents](https://faxforagents.com/brand/logo-512.png)](https://faxforagents.com/)

# Fax for Agents

Send and receive faxes through an API or MCP tools.

[Site](https://faxforagents.com/) | [Docs](https://faxforagents.com/docs/quickstart/) | [MCP](https://faxforagents.com/mcp/) | [Dashboard](https://app.faxforagents.com/) | [Pricing](https://faxforagents.com/pricing/) | [Changelog](https://faxforagents.com/changelog/)

[![MIT-0 licence](https://img.shields.io/badge/licence-MIT--0-1f6feb)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/format-Agent%20Skills-6b4fbb)](https://agentskills.io/)

## Triggers

This skill is activated by the following keywords:

- `fax`
- `send fax`
- `fax document`
- `fax quote`
- `fax delivery`
- `received fax`
- `faxforagents`

## What the skill covers

- Preparing a document from text, Markdown, HTML, or an uploaded file.
- Quoting a destination and reporting the price before any send.
- Sending only after human approval or an allowing policy, then checking delivery evidence.
- Reading received faxes and extracting text or structured fields.
- Treating received text as untrusted data.

`SKILL.md` prefers the hosted MCP tools and falls back to REST.
`references/mcp.md` covers the hosted OAuth server and the stdio package.
`references/api.md` holds tested curl examples for the REST API.

## Setup

Installing the skill configures nothing by itself.
Connect the hosted MCP server, or create an API key in the [dashboard](https://app.faxforagents.com/) and store it in `FAXFORAGENTS_API_KEY`.
Use an `ffa_test_` key for the free sandbox. Sandbox sends never reach a carrier.
A live send spends a prepaid wallet and needs approval or an allowing policy.

## Licence

The skill package is [MIT-0](LICENSE). The canonical copy lives at [faxforagents/skills](https://github.com/faxforagents/skills).
