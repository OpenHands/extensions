# Bitbucket

Bitbucket integration **hub** skill. It detects whether the repository is on Bitbucket
Cloud or Bitbucket Data Center and directs the agent to the matching detailed skill.

## Triggers

This skill is activated by the following keywords:

- `bitbucket`
- `git`

## Why a hub skill?

Bitbucket ships as two products that behave differently — **Bitbucket Cloud**
(`bitbucket.org`) and **Bitbucket Data Center** (self-hosted Bitbucket Server). They use
different token environment variables, REST APIs, repository identifiers, git remote URL
formats, and pull request tools.

This hub triggers broadly (on `git`/`bitbucket`) so it loads for any Bitbucket task — even
when the words "data center" never appear. It then:

1. **Detects** the environment by checking which token variable is present
   (`BITBUCKET_DATA_CENTER_TOKEN` → Data Center, else `BITBUCKET_TOKEN` → Cloud). The check
   is case-insensitive so it is robust to env-var casing differences.
2. **Hands off** to the matching detailed skill via the `invoke_skill` tool:
   - Bitbucket Cloud → [`bitbucket-cloud`](../bitbucket-cloud/)
   - Bitbucket Data Center → [`bitbucket-data-center`](../bitbucket-data-center/)

## Authentication

You can interact with Bitbucket using one of the following methods, in order of preference:

1. **OAuth MCP Server** (preferred): If authenticated Bitbucket MCP tools are available in
   the environment, use them for Bitbucket operations. MCP tools handle authentication via
   the configured OAuth integration, so no token is needed.
2. **Secret Token**: If the relevant token environment variable is set
   (`BITBUCKET_TOKEN` for Cloud, `BITBUCKET_DATA_CENTER_TOKEN` for Data Center), use it
   with the Bitbucket API, as described in the detailed skills.
3. **No authentication**: If neither is available, ask the user to either:
   - Connect a Bitbucket OAuth MCP server in Canvas, OR
   - Provide the relevant token as a Secret

Detection is based on the availability of authenticated Bitbucket MCP tools - no specific
MCP server name or tool name is required. When MCP tools are available, prefer them; the
token/direct-API flows in the detailed skills remain the correct path when MCP is
unavailable or when you explicitly need raw API/curl access.

The hub also carries a small quick-reference table as a fallback in case the detailed skill
cannot be loaded.

See [`SKILL.md`](SKILL.md) for the full content.