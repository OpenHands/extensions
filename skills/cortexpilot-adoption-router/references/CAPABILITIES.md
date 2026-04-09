# CortexPilot MCP Capabilities

These are the stable read-only tools exposed by the published CortexPilot MCP.

## Safe-first tools

1. `list_runs`
   - use first when the user needs the current run ledger
2. `get_run`
   - use when the user already has one run identifier and needs the run snapshot
3. `list_workflows`
   - use when the user needs the current workflow ledger
4. `get_workflow`
   - use when the user already has one workflow identifier

## Queue and approval tools

- `list_queue`
- `get_pending_approvals`
- `get_diff_gate_state`

Use these when the user is inspecting queue state, pending approvals, or diff
gate posture.

## Proof and incident tools

- `get_run_reports`
- `get_compare_summary`
- `get_proof_summary`
- `get_incident_summary`

Use these after the user is already inside a specific run and wants the proof,
compare, or incident read model.
