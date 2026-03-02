# Linear

Interact with Linear project management - query issues, update status, create tickets, and manage workflows using the Linear GraphQL API. Use when working with Linear tickets, sprints, or project tracking.

## Triggers

This skill is activated by the following keywords:

- `linear`
- `ticket`
- `issue tracking`

## Details

You need access to an environment variable, `LINEAR_API_KEY`, which allows you to interact with the Linear API.

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
