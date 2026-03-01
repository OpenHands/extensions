---
name: linear
description: Interact with Linear project management - query issues, update status, create tickets, and manage workflows using the Linear GraphQL API. Use when working with Linear tickets, sprints, or project tracking.
triggers:
- linear
- ticket
- issue tracking
---

# Linear

<IMPORTANT>
Before performing any Linear operations, check if the required environment variable is set:

```bash
[ -n "$LINEAR_API_KEY" ] && echo "LINEAR_API_KEY is set" || echo "LINEAR_API_KEY is NOT set"
```

If LINEAR_API_KEY is missing, ask the user to provide it before proceeding.
</IMPORTANT>

## Authentication

All Linear API requests use GraphQL with the API key in the Authorization header:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{"query": "YOUR_GRAPHQL_QUERY"}'
```

## Common Queries

### Get Assigned Issues (Open)

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "query { viewer { assignedIssues(first: 50, filter: { state: { type: { nin: [\"completed\", \"canceled\"] } } }) { nodes { identifier title priority priorityLabel state { name type } description createdAt updatedAt } } } }"
  }' | jq '.data.viewer.assignedIssues.nodes'
```

### Get Issues by Priority

Priority values: 0 = No priority, 1 = Urgent, 2 = High, 3 = Medium, 4 = Low

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "query { viewer { assignedIssues(first: 50, filter: { priority: { lte: 2 }, state: { type: { nin: [\"completed\", \"canceled\"] } } }) { nodes { identifier title priority priorityLabel state { name } } } } }"
  }' | jq '.data.viewer.assignedIssues.nodes'
```

### Get Issue Details

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "query { issue(id: \"ISSUE_ID\") { identifier title description state { name } priority assignee { name email } labels { nodes { name } } comments { nodes { body createdAt user { name } } } } }"
  }' | jq '.data.issue'
```

### Search Issues by Identifier

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "query { issueSearch(query: \"ALL-1234\", first: 5) { nodes { identifier title state { name } } } }"
  }' | jq '.data.issueSearch.nodes'
```

## Common Mutations

### Update Issue State

First, get available workflow states:
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "query { workflowStates { nodes { id name type } } }"
  }' | jq '.data.workflowStates.nodes'
```

Then update the issue:
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "mutation { issueUpdate(id: \"ISSUE_UUID\", input: { stateId: \"STATE_UUID\" }) { success issue { identifier state { name } } } }"
  }' | jq '.data.issueUpdate'
```

### Add Comment to Issue

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "mutation { commentCreate(input: { issueId: \"ISSUE_UUID\", body: \"Your comment here\" }) { success comment { id body } } }"
  }' | jq '.data.commentCreate'
```

### Create New Issue

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "mutation { issueCreate(input: { teamId: \"TEAM_UUID\", title: \"Issue Title\", description: \"Issue description\", priority: 2 }) { success issue { identifier title url } } }"
  }' | jq '.data.issueCreate'
```

## Get Team Information

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "query { teams { nodes { id name key } } }"
  }' | jq '.data.teams.nodes'
```

## Priority Levels

| Priority | Label | Recommended Action |
|----------|-------|-------------------|
| 1 | Urgent | Work on immediately |
| 2 | High | Work on first |
| 3 | Medium | Normal priority |
| 4 | Low | When time permits |
| 0 | None | Backlog |

## State Types

- `backlog` - Not yet started
- `unstarted` - Todo
- `started` - In Progress
- `completed` - Done
- `canceled` - Won't do

## Documentation

- [Linear API Documentation](https://developers.linear.app/docs/graphql/working-with-the-graphql-api)
- [GraphQL Schema Reference](https://studio.apollographql.com/public/Linear-API/variant/current/schema/reference)
