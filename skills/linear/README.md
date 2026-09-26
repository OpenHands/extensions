# Linear

Interact with Linear project management - query issues, update status, create tickets, and manage workflows using the Linear GraphQL API. Use when working with Linear tickets, sprints, or project tracking.

## Triggers

This skill is activated by the following keywords:

- `linear`
- `ticket`
- `issue tracking`

## Details

You can interact with Linear using one of the following methods, in order of preference:

1. **OAuth MCP Server** (preferred): If authenticated Linear MCP tools are available in the
   environment, use them for Linear operations. MCP tools handle authentication via the
   configured OAuth integration, so no API key is needed.
2. **Secret API Key**: If a `LINEAR_API_KEY` environment variable is set, use it with the
   Linear GraphQL API, as described below.
3. **No authentication**: If neither is available, ask the user to either:
   - Connect a Linear OAuth MCP server in Canvas, OR
   - Provide a `LINEAR_API_KEY` as a Secret

Detection is based on the availability of authenticated Linear MCP tools - no specific
MCP server name or tool name is required. When MCP tools are available, prefer them;
the direct GraphQL flows below remain the correct path when MCP is unavailable or when
you explicitly need raw API/curl access.

<IMPORTANT>
You can use `curl` with the `LINEAR_API_KEY` to interact with Linear's GraphQL API.
ALWAYS use the Linear API for operations instead of a web browser.
Before performing any Linear operations, verify the API key is available by checking the environment variable.
</IMPORTANT>

## Features

- **Query Issues**: Get assigned issues, filter by priority, search by identifier
- **Update State**: Change issue status with workflow state lookup
- **Comments**: Add comments to issues
- **Create Issues**: Create new tickets with proper team assignment
- **Reference**: Priority levels, state types, API documentation links

## Important Concepts

### Linear Identifiers

Linear uses two types of identifiers for issues:

- **Human-readable identifier** (e.g., `ALL-1234`): Displayed to users, used in search queries
- **UUID** (e.g., `a1b2c3d4-e5f6-7890-abcd-ef1234567890`): Required for all mutations

**Important workflow**: When updating issues:
1. Search using the human-readable identifier
2. Extract the UUID from the query result
3. Use the UUID in mutation operations

### Priority Levels

| Priority | Label | Description |
|----------|-------|-------------|
| 1 | Urgent | Work on immediately |
| 2 | High | Work on first |
| 3 | Medium | Normal priority |
| 4 | Low | When time permits |
| 0 | None | Backlog |

## Documentation

- [Linear API Documentation](https://developers.linear.app/docs/graphql/working-with-the-graphql-api)
- [GraphQL Schema Reference](https://studio.apollographql.com/public/Linear-API/variant/current/schema/reference)
