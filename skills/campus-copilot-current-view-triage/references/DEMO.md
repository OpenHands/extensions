# OpenHands / OpenClaw Demo Walkthrough

This is the shortest concrete demo you can run to prove the skill is doing real
triage work instead of only existing as prose.

## Demo prompt

Use Campus Copilot to tell the student what to do first right now. Start with
`campus_health`. Then inspect the strongest available snapshot/current-view
surface. If a student question exists, answer it through `ask_campus_copilot`.
Return `top_action`, `why_now`, `evidence_used`, and `trust_gaps`.

## Expected tool sequence

1. `campus_health`
2. one or more `*_snapshot_view` tools
3. optionally `ask_campus_copilot`

## Visible success criteria

- the agent names one concrete first action
- the answer cites the Focus Queue or snapshot surface instead of guessing
- the boundary stays read-only and snapshot-aware
