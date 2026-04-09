---
name: movi-review-first-bundle
description: Teach an agent to install Movi's local MCP server, stay review-first, and use the safest manifest and batch-analysis tools before deeper mutation.
version: 1.0.0
triggers:
  - movi
  - movi organizer
  - review-first batch
  - manifest review
  - openclaw movi
---

# Movi Review-First Bundle

Teach the agent how to install, connect, and use Movi as a local-first
review-first MCP workflow.

## Use this skill when

- the user wants to inspect one batch or review queue before executing anything
- the host can run a local MCP server from a repo checkout
- the operator wants a truthful packet that explains install, attach, proof, and
  safe-first usage without claiming a live listing

## What this package teaches

- how to wire Movi MCP into Codex, Claude Code, OpenHands, or OpenClaw
- which Movi tools are safe first when the work must stay review-first
- how to inspect jobs, manifests, and review rules before calling heavier
  mutation tools
- how to keep listing claims honest while still proving the packet is real

## Start here

1. Read [references/INSTALL.md](references/INSTALL.md)
2. Load the right host config from:
   - [references/OPENHANDS_MCP_CONFIG.json](references/OPENHANDS_MCP_CONFIG.json)
   - [references/OPENCLAW_MCP_CONFIG.json](references/OPENCLAW_MCP_CONFIG.json)
3. Skim the tool surface in [references/CAPABILITIES.md](references/CAPABILITIES.md)
4. Run the first-success path in [references/DEMO.md](references/DEMO.md)

## Safe-first workflow

1. `jobs.list`
2. `review_queue.get`
3. `manifest.get`
4. `analyze.create`
5. only then consider preview or patch-style actions such as:
   - `manifest.patch_row`
   - `manifest.batch_patch`
   - `review_rule.preview`

## Suggested first prompt

Use Movi to inspect the current review-first workload. Start with `jobs.list`,
`review_queue.get`, and `manifest.get`. Summarize which batch needs attention
first. If the manifest looks stable, use `analyze.create` to produce one
analysis artifact. Do not call `manifest.patch_row`, `manifest.batch_patch`, or
`review_rule.apply` unless I explicitly ask for a patch or rule change.

## Success checks

- the host can launch the local Movi MCP server from the provided config
- the packet proves one real job/review queue exists instead of describing an
  imaginary batch
- the first analysis artifact is tied to a real manifest or job record

## Boundaries

- Movi stays a local-first review-first MCP workflow, not a hosted SaaS
- this packet does not claim a live OpenHands or ClawHub listing
- this packet does not bypass `review-first -> dry-run -> execute`

## Local references

- [references/INSTALL.md](references/INSTALL.md)
- [references/CAPABILITIES.md](references/CAPABILITIES.md)
- [references/DEMO.md](references/DEMO.md)
- [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md)
