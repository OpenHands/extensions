# OpenHands / OpenClaw Demo Walkthrough

This is the shortest concrete demo you can run to prove the skill is doing real
work instead of only describing one.

## Demo prompt

Connect DealWatch, confirm whether the runtime is ready, and compare two
candidate grocery URLs without creating any durable state.

Start with `get_runtime_readiness`. If the runtime is healthy, run
`compare_preview` on the submitted product URLs. Then explain which lane the
user should choose next and why.

## Expected tool sequence

1. `get_runtime_readiness`
2. `compare_preview`
3. optionally `get_builder_starter_pack`

## Visible success criteria

- the agent reports whether the local runtime is ready
- the compare step returns a real preview instead of creating durable state
- the agent names the safest next lane instead of widening into write flows

## What the output should look like

Return a compact answer with:

1. the chosen lane
2. the next 1-3 actions
3. one boundary reminder
4. one exact MCP tool or install snippet
