# Bitbucket Cloud

Bitbucket Cloud (`bitbucket.org`) specifics — `BITBUCKET_TOKEN` auth, REST API v2,
`workspace/repo_slug` repositories, and the `create_bitbucket_pr` tool.

## Triggers

This skill has no auto-injection triggers. It is **invoke-only**: it is loaded on demand
via the `invoke_skill` tool, normally by the [`bitbucket`](../bitbucket/) hub skill after
it detects a Bitbucket Cloud environment (i.e. `BITBUCKET_TOKEN` is set).

## Authentication

You can interact with Bitbucket Cloud using one of the following methods, in order of
preference:

1. **OAuth MCP Server** (preferred): If authenticated Bitbucket MCP tools are available in
   the environment, use them. MCP tools handle authentication via the configured OAuth
   integration, so no token is needed.
2. **Secret Token**: If a `BITBUCKET_TOKEN` environment variable is set, use it with the
   Bitbucket Cloud API.
3. **No authentication**: If neither is available, ask the user to either connect a
   Bitbucket OAuth MCP server in Canvas, or provide a `BITBUCKET_TOKEN` as a Secret.

Detection is based on the availability of authenticated Bitbucket MCP tools - no specific
MCP server name or tool name is required. When MCP tools are available, prefer them; the
token/direct-API path below remains correct when MCP is unavailable or when raw API/curl
access is explicitly needed.

## Details

See [`SKILL.md`](SKILL.md) for the full content, including authenticated git remote
construction and pull request instructions.
