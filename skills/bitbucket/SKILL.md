---
name: bitbucket
description: Bitbucket integration hub. Detects whether the repository is on Bitbucket Cloud or Bitbucket Data Center and directs you to the matching detailed skill (bitbucket-cloud or bitbucket-data-center). Use for any Bitbucket repository or pull request task.
triggers:
- bitbucket
---

You are working with **Bitbucket**, which ships as two distinct products that behave
differently:

- **Bitbucket Cloud** (`bitbucket.org`) - authenticates with the `BITBUCKET_TOKEN`
  environment variable.
- **Bitbucket Data Center** (self-hosted Bitbucket Server) - authenticates with the
  `BITBUCKET_DATA_CENTER_TOKEN` environment variable.

They use different REST APIs, repository identifiers, git remote URL formats, and pull
request tools, so you must first determine which one you are on, then load the matching
detailed skill for full instructions.

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

The detection steps below determine which product you are on (Cloud vs Data Center). They
check for an authenticated Bitbucket MCP connection first; only when MCP is unavailable do
they fall back to the token environment variables. If neither is available, ask the user to
authenticate (per the No-authentication option above) rather than assuming a product.

## Step 1 - Detect which Bitbucket you are on

First check for an authenticated Bitbucket MCP connection. If Bitbucket MCP tools are
available in the environment, you already have an authenticated path - use it directly, and
treat the connected product (Cloud or Data Center) as the detected environment.

If no Bitbucket MCP tools are available, detect the product from the token environment
variable. Environment variable names are case-sensitive, so look for it case-insensitively:

```bash
env | grep -i 'bitbucket' || echo "no bitbucket token found"
```

- If a **`BITBUCKET_DATA_CENTER_TOKEN`** variable is set (in any letter case) → you are on
  **Bitbucket Data Center**.
- Otherwise, if a **`BITBUCKET_TOKEN`** variable is set → you are on **Bitbucket Cloud**.
- If neither an MCP connection nor a token is available, ask the user to either connect a
  Bitbucket OAuth MCP server in Canvas or provide the relevant token as a Secret before
  proceeding (do not guess the product).

When you reference the token later, use the exact variable name (and letter case) that
actually exists in the environment.

## Step 2 - Load the detailed skill

Once you know the environment, use the `invoke_skill` tool to load the matching skill for
full instructions on API calls, authenticated git remotes, and opening pull requests. The
detailed skills also carry the MCP-first guidance, so load the matching one even when you
plan to use MCP, and prefer the MCP tools it documents when available:

- Bitbucket Cloud → invoke the **`bitbucket-cloud`** skill.
- Bitbucket Data Center → invoke the **`bitbucket-data-center`** skill.

## Quick reference (fallback)

If you are unable to load the detailed skill, these are the essentials. Always use the
Bitbucket API (not a web browser) and always use the listed PR tool to open a pull request.

| | Bitbucket Cloud | Bitbucket Data Center |
|---|---|---|
| Token env var | `BITBUCKET_TOKEN` | `BITBUCKET_DATA_CENTER_TOKEN` |
| Host | `bitbucket.org` | self-hosted domain |
| REST API base | `https://api.bitbucket.org/2.0` | `https://<host>/rest/api/1.0` |
| Repository identifier | `workspace/repo_slug` | `PROJECT/repo_slug` (project key) |
| Pull request tool | `create_bitbucket_pr` | `create_bitbucket_data_center_pr` |