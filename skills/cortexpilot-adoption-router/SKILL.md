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

## What this skill teaches

- how to install the published CortexPilot MCP package
- how to choose the right read-only tool for the current job
- how to start with one public lane instead of mixing every surface together
- how to keep the answer inside the current read-only public boundary

## When to use this skill

Use this skill when the user asks to:

- connect CortexPilot to OpenHands or OpenClaw
- inspect runs or workflows through the public read-only MCP
- understand which public CortexPilot lane to choose first
- inspect approvals, queue state, proof, compare, or incident summaries without
  mutating anything

## If the MCP is not connected yet

Open `README.md` in this folder and follow `references/INSTALL.md`.
Do not invent repo-local startup paths when the published package already
exists.

## Safe-first workflow

1. `list_runs` or `list_workflows`
   Use these first when the user needs the top-level ledger.
2. `get_run` or `get_workflow`
   Use these after the user already has the specific run or workflow to inspect.
3. `list_queue`, `get_pending_approvals`, or `get_diff_gate_state`
   Use these for queue, approval, or diff-gate posture.
4. `get_run_reports`, `get_compare_summary`, `get_proof_summary`, or
   `get_incident_summary`
   Use these after the user is already inside one run and needs a specific
   proof-oriented read model.

## Tool-selection rule

- Choose run/workflow reads for “what is happening now?”
- Choose queue/approval reads for “what is blocked or pending?”
- Choose compare/proof/incident reads for “what evidence exists for this run?”
- Do not mix multiple lanes unless the user explicitly asks for a broader audit

## What to return

Return a short answer with:

1. the chosen lane
2. the next 1-3 actions
3. one boundary reminder
4. one exact MCP tool or install snippet

## Guardrails

- Do not describe CortexPilot as a hosted operator product.
- Do not describe the public MCP surface as write-capable.
- Do not claim a first-party marketplace listing unless that host independently
  confirms it.
- Keep `task_contract` as the execution authority for real runs; this MCP is
  read-only inspection only.

## Read next

- `references/INSTALL.md`
- `references/CAPABILITIES.md`
- `references/DEMO.md`
- `references/TROUBLESHOOTING.md`
