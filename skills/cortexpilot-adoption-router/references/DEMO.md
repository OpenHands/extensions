# OpenHands / OpenClaw Demo Walkthrough

This is the shortest concrete demo you can run to prove the skill is doing real
inspection work instead of only describing one.

## Demo prompt

Connect CortexPilot and inspect the current public run ledger. Start with
`list_runs` or `list_workflows`, then inspect one specific run or workflow.
If the user is really asking what is blocked, pivot into `list_queue` or
`get_pending_approvals` and explain the safest next lane.

## Expected tool sequence

1. `list_runs` or `list_workflows`
2. `get_run` or `get_workflow`
3. optionally `list_queue` or `get_pending_approvals`

## Visible success criteria

- the agent names one real run or workflow instead of speaking in the abstract
- the answer stays on the read-only lane
- the agent points the user at the next inspection step instead of inventing a
  write workflow
