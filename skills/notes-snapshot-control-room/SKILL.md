---
name: notes-snapshot-control-room
description: Use this public skill when you want a repo-scoped Apple Notes Snapshot guide that keeps the control-room identity first, requires local preflight before attach claims, and separates official listing claims from repo-owned starter packs, local marketplaces, and host-specific proof.
version: 1.0.0
---

# Apple Notes Snapshot Control-Room

## Purpose

Help a host, plugin, or collaborator consume Apple Notes Snapshot without
rewriting it into a hosted AI platform or a generic assistant product.

## Keep this identity first

- Apple Notes local-first backup control room for macOS
- `notesctl` is the canonical human entrypoint
- `AI Diagnose` is an advisory sidecar
- `Local Web API` is token-gated and same-machine
- `MCP` is stdio-first and read-only-first

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
