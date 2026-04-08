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

## What this skill helps the agent do

- install the published DealWatch MCP package
- choose the right read-only tool for the current job
- start with runtime readiness and compare preview before deeper reads
- keep the answer inside the current local-first boundary

## When to use this skill

Use this skill when the user asks to:

- connect DealWatch to OpenHands
- check whether DealWatch is ready for a local read-only session
- compare grocery product URLs before creating durable state
- inspect watch tasks, watch groups, or recovery state without mutating anything

## If the MCP is not connected yet

Open `references/mcp-install.md` and use the published-package config snippet.
Do not assume a repo-local checkout is available.

## Safe-first workflow

1. `get_runtime_readiness`
2. `compare_preview`
3. `get_builder_starter_pack`
4. `list_watch_tasks` or `list_watch_groups`
5. one detail read
6. recovery or notification reads only if the user is already in that lane

## Tool-selection rule

- choose `compare_preview` for “Which URL is the right target?”
- choose `get_runtime_readiness` for “Is the local runtime healthy?”
- choose `get_builder_starter_pack` for “How do I connect the agent?”
- choose watch-task/group reads only after the user already has durable state

## What to return

Return a short answer with:

1. the chosen lane
2. the next 1-3 actions
3. one boundary reminder
4. one exact MCP tool or install snippet

## Guardrails

- no write-side MCP
- no hosted control plane
- no first-party marketplace claim unless the host independently confirms it
- no autonomous recommendation support

## Read next

- `references/mcp-install.md`
- `references/tool-map.md`
- `references/example-tasks.md`
