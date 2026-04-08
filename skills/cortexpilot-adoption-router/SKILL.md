---
name: cortexpilot-adoption-router
description: Teach the agent how to connect the published CortexPilot read-only MCP package, choose the right public lane, and use the stable read-only tools without overclaiming hosted or write-capable support.
triggers:
  - cortexpilot
  - cortexpilot setup
  - cortexpilot mcp
  - cortexpilot proof
  - cortexpilot workflow
---

# CortexPilot Adoption Router

Use this skill when the user needs the shortest truthful path into CortexPilot.

## What this skill helps the agent do

- install the published CortexPilot MCP package
- choose the right read-only tool for the current job
- start with one public lane instead of mixing every CortexPilot surface together
- keep the answer inside the current read-only public boundary

## When to use this skill

Use this skill when the user asks to:

- connect CortexPilot to OpenHands
- inspect runs or workflows through the public read-only MCP
- understand which public lane should come first
- inspect approvals, queue state, proof, compare, or incident summaries without
  mutating anything

## If the MCP is not connected yet

Open `references/mcp-install.md` and use the published-package config snippet.
Do not assume the user has a local checkout of the source repo.

## Safe-first workflow

1. `list_runs` or `list_workflows`
2. `get_run` or `get_workflow`
3. `list_queue`, `get_pending_approvals`, or `get_diff_gate_state`
4. `get_run_reports`, `get_compare_summary`, `get_proof_summary`, or
   `get_incident_summary`

## Tool-selection rule

- choose run/workflow reads for “what is happening now?”
- choose queue/approval reads for “what is blocked or pending?”
- choose proof/compare/incident reads only after the user already has one run to
  inspect
- do not mix multiple lanes unless the user explicitly asks for a broader audit

## What to return

Return a short answer with:

1. the chosen lane
2. the next 1-3 actions
3. one boundary reminder
4. one exact MCP tool or install snippet

## Guardrails

- no hosted operator service
- no write-capable public MCP
- no first-party marketplace claim unless the host independently confirms it
- keep `task_contract` as the execution authority for real runs; this MCP is
  read-only inspection only

## Read next

- `references/mcp-install.md`
- `references/tool-map.md`
- `references/example-tasks.md`
