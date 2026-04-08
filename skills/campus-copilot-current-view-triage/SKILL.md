---
name: campus-copilot-current-view-triage
description: Turn one Campus Copilot snapshot or MCP-backed current view into a plain-language what-to-do-first answer for a student.
triggers:
  - campus copilot
  - focus queue
  - current view
  - study triage
---

# Campus Copilot Current View Triage

Use this skill when you need one short answer to the question:

- what should the student do first right now

Think of it as a **student triage card** on top of Campus Copilot's read-only surfaces:

- imported snapshot / current-view JSON
- or one connected Campus Copilot MCP server
- optionally one student question

This skill is for **read-only context and prioritization**. It is not a live-browser or write-action playbook.

## What this skill teaches the agent

- how to tell whether Campus Copilot MCP is available or whether only a snapshot/current-view export is available
- how to use the smallest helpful Campus Copilot surface first instead of expanding into browser automation
- how to turn Focus Queue and recent changes into one clear next step
- how to answer with evidence and trust gaps rather than filling in missing facts

## Runtime you need

- one imported Campus Copilot snapshot or current-view export
- or a connected Campus Copilot MCP server
- if MCP is not connected yet, hand the operator the setup recipe in `references/mcp-setup.md`

## MCP capability map

Campus Copilot exposes a small read-only MCP surface. The tools that matter most for this skill are:

- `campus_health` to confirm the local BFF is alive
- `providers_status` to see whether the cited-answer path is ready
- `ask_campus_copilot` to answer one question over the Campus semantic contract
- `canvas_snapshot_view`, `gradescope_snapshot_view`, `edstem_snapshot_view`, `myuw_snapshot_view` to inspect site slices
- `export_snapshot_artifact` to produce a portable proof artifact

Use the quick mapping in `references/capability-map.md` when you need the full list.

## Inputs to fill in

- `SNAPSHOT_PATH` or one current-view export path
- `QUESTION` if the student wants more than "what now"
- `MCP_STATUS` = connected or not connected

## Steps

1. Decide the strongest available input:
   - MCP-backed current view if Campus Copilot MCP is already connected
   - otherwise the imported snapshot/current-view export
2. Build a short workspace summary:
   - top Focus Queue items
   - what changed recently
   - which site is carrying the most urgency
3. If `QUESTION` exists, answer it through `ask_campus_copilot` or the current-view payload.
4. Return one plain-language recommendation that includes:
   - the first action
   - why it is first
   - evidence used
   - trust gaps
   - the next setup step if MCP was missing

## Good fit

- OpenHands first-pass triage over a Campus Copilot snapshot
- local student-facing "what now" briefs
- repo-local verification that the decision layer is understandable before reopening live browser work

## Output contract

Return these four fields in plain language:

- `top_action`
- `why_now`
- `evidence_used`
- `trust_gaps`

See `references/example-output.md` for a compact example.

## Hard boundary

- stay on imported snapshots or the thin local BFF
- do not claim live browser or session truth from snapshot-only evidence
- do not mutate site state

## Local references

- `references/mcp-setup.md`
- `references/capability-map.md`
- `references/example-output.md`
