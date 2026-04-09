---
name: dealwatch-readonly-builder
description: Teach the agent how to connect the published DealWatch MCP package, choose the right read-only tool, and guide the user through the compare-first safe path without claiming hosted or write-capable features.
triggers:
  - dealwatch
  - dealwatch setup
  - dealwatch mcp
  - compare preview
  - watch group
---

# DealWatch Read-only Builder

Use this skill when the user wants the shortest truthful path into DealWatch.

## What this skill teaches

- how to install the published DealWatch MCP package
- how to choose the right read-only tool for the current job
- how to start with runtime readiness and compare preview before deeper reads
- how to keep the answer inside the current local-first boundary

## When to use this skill

Use this skill when the user asks to:

- connect DealWatch to OpenHands or OpenClaw
- check whether DealWatch is ready for a local read-only session
- compare grocery product URLs before creating durable state
- inspect watch tasks, watch groups, or recovery state without mutating anything

## If the MCP is not connected yet

Open `README.md` in this folder and follow `references/INSTALL.md`.
Do not invent repo-local launch commands when the published package already
exists.

## Safe-first workflow

1. `get_runtime_readiness`
   Use this first when setup, environment, or startup truth is unclear.
2. `compare_preview`
   Use this first when the user wants to compare candidate grocery URLs without
   creating tasks.
3. `get_builder_starter_pack`
   Use this when the user needs the integration contract or host setup path.
4. `list_watch_tasks` or `list_watch_groups`
   Use these after the first-safe path is already clear.
5. `get_watch_task_detail` or `get_watch_group_detail`
   Use these for one deeper read-only follow-up.
6. `get_recovery_inbox`, `get_notification_settings`, or
   `get_store_onboarding_cockpit`
   Use these only after the user is already inside a recovery or operator
   diagnostic workflow.

## Tool-selection rule

- Choose `compare_preview` for “Which URL is the right target?”
- Choose `get_runtime_readiness` for “Is the local runtime healthy?”
- Choose `get_builder_starter_pack` for “How do I connect an agent or host?”
- Choose watch-task/group reads only after the user already has durable state to
  inspect

## What to return

Return a short answer with:

1. the chosen lane
2. the next 1-3 actions
3. one boundary reminder
4. one exact MCP tool or install snippet

## Guardrails

- write-side MCP
- hosted control plane
- official marketplace or registry listing
- autonomous recommendation support

## Read next

- `references/INSTALL.md`
- `references/CAPABILITIES.md`
- `references/DEMO.md`
- `references/TROUBLESHOOTING.md`
