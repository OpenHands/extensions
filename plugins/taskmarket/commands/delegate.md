---
allowed-tools: Bash(python:*), Bash(taskmarket:*), Bash(npm:*)
argument-hint: <description and approved budget>
description: Preview and, after explicit approval, delegate a task to TaskMarket
---

# Delegate work to TaskMarket

Use the bundled adapter at
`plugins/taskmarket/scripts/taskmarket.py`. Treat the arguments as a request
to prepare a delegation, not as permission to spend funds.

## Required workflow

1. Extract an exact task description, deliverables, acceptance criteria,
   reward, duration, and tags from **$ARGUMENTS**. If any of these are missing,
   ask the user before writing a task.
2. Remove secrets, private data, credentials, and unauthorized actions from
   the description.
3. Run the adapter's `preview` command and show the complete JSON output,
   including the estimated maximum spend and Base network.
4. Wait for explicit approval of that exact preview. Do not infer approval
   from the original request to delegate.
5. On approval, run the same arguments once with `create --confirm` and the
   user-approved `--max-spend-usdc` value.
6. Return the task ID/API link. Later use `status` and `submissions`; never
   auto-accept or retry an ambiguous payment response.
