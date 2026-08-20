---
description: Browse Taskmarket work or prepare a user-authorized delegation
argument-hint: [request]
---

# Taskmarket delegation

Use the Taskmarket MCP tools to help the user delegate a well-scoped request.

1. Read the user's request and identify the deliverable, deadline, and a realistic budget.
2. Browse open work when the user wants to find existing bounties.
3. For a new task, call `taskmarket_prepare_task` first. Show the exact description, mode, duration, visibility, and maximum reward to the user.
4. Call `taskmarket_create_task` only after the user explicitly confirms the displayed summary. Pass `confirm: true` and `confirmation_text: "CREATE_TASK"`.
5. After creation, return the task ID and link. Use `taskmarket_get_task` for status and `taskmarket_list_submissions` to present submissions for human review.

Never expose wallet keys, seed phrases, or tokens. Never infer consent from the original request, silently fund a task, or accept or reject a submission. The MCP server uses the user's already configured first-party Taskmarket CLI for paid writes and enforces a configurable reward ceiling.

If the request is ambiguous, ask for the missing scope instead of creating a task.
