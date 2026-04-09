---
name: notes-snapshot-control-room
description: This skill should be used when the user asks to "connect Apple Notes Snapshot to a host", "run notesctl mcp", "diagnose why Apple Notes Snapshot failed to attach", "separate AI Diagnose from MCP", or "verify the control-room proof path". It teaches local preflight, MCP wiring, capability boundaries, and proof-first usage without turning the repo into a hosted platform.
version: 1.0.2
triggers:
  - notesctl mcp
  - apple notes snapshot
  - ai diagnose
  - local web api
  - attach proof
---

# Apple Notes Snapshot Control-Room

## Purpose

Help a host, plugin, or collaborator consume Apple Notes Snapshot without
rewriting it into a hosted AI platform or a generic assistant product.

## What this skill teaches

- how to acquire `notesctl` from a public checkout when the host does not
  already have it
- how to prove the local control room before touching builder surfaces
- how to wire `notesctl mcp` into a host without pretending there is a remote
  service
- how to separate AI Diagnose, Local Web API, and MCP into three different
  lanes
- how to talk about attach proof honestly

## Keep this identity first

- Apple Notes local-first backup control room for macOS
- `notesctl` is the canonical human entrypoint
- `AI Diagnose` is an advisory sidecar
- `Local Web API` is token-gated and same-machine
- `MCP` is stdio-first and read-only-first

## First-success flow

1. Acquire `notesctl` first using `references/INSTALL.md`.
2. Prove the operator lane first:
   - `./notesctl run --no-status`
   - `./notesctl install --minutes 30 --load`
   - `./notesctl verify`
   - `./notesctl doctor`
3. Only after local state exists, attach the builder lane:
   - `./notesctl ai-diagnose`
   - `./notesctl web`
   - `./notesctl mcp`
4. Keep host proof separate from repo proof.

## MCP capability surface

- post-attach host checks should see `get_status`, `run_doctor`,
  `verify_freshness`, `get_log_health`, `list_recent_runs`, and
  `get_access_policy`
- the repo also documents the `notes-snapshot://recent-runs` resource as a
  first read-back surface
- boundary:
  local stdio only, read-only-first tools/resources, and no hosted runtime

## Preflight before any attach claim

Do not treat host registration as proof by itself.

Verify:

1. `./notesctl run --no-status`
2. `./notesctl verify`
3. `./notesctl doctor --json`
4. `./notesctl status --json`

If those fail, call it a local snapshot preflight problem, not an MCP bug.

## Truthful distribution boundary

- Repo-owned starter packs and local marketplaces are public-ready wiring kits.
- They are not the same thing as official public directory listing.
- A tagged `v0.1.12` named-host attach-proof trail on one machine does not become a universal
  proof for every host build or every machine.

## Example prompts

- "Wire Apple Notes Snapshot MCP into this host and tell me whether the blocker is local preflight or MCP configuration."
- "Explain the difference between AI Diagnose, Local Web API, and MCP in Apple Notes Snapshot."
- "Show me the shortest proof path from first run to MCP attach."
- "Use the control-room skill to explain why a backup loop drifted."

## Best-fit use cases

- Repo-scoped guidance for Codex, Claude Code, OpenClaw, or another local host
- Public skill distribution through a ClawHub-style listing or another
  skill-folder distribution lane
- Public-facing docs or README edits that must keep builder wording honest

## What this skill should not do

- Do not reposition Apple Notes Snapshot as a hosted agent platform.
- Do not claim official marketplace or directory listing unless it truly landed.
- Do not collapse repo-side proof, current-host proof, and public registry
  publication into one sentence.

## Read next

- `references/README.md`
- `references/INSTALL.md`
- `references/OPENHANDS_MCP_CONFIG.json`
- `references/OPENCLAW_MCP_CONFIG.json`
- `references/CAPABILITIES.md`
- `references/DEMO.md`
- `references/TROUBLESHOOTING.md`
