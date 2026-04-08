# CortexPilot MCP Tool Map

## Safe-first tools

1. `list_runs`
2. `get_run`
3. `list_workflows`
4. `get_workflow`

Use these first when the job is “inspect current truth”.

## Queue and approval tools

- `list_queue`
- `get_pending_approvals`
- `get_diff_gate_state`

Use these when the job is “inspect blocked or pending work”.

## Proof and incident tools

- `get_run_reports`
- `get_compare_summary`
- `get_proof_summary`
- `get_incident_summary`

Use these after the user already has a specific run in hand.
