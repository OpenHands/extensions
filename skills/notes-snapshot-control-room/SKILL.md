---
name: notes-snapshot-control-room
description: This skill should be used when the user asks to connect Apple Notes Snapshot to Codex, Claude Code, OpenClaw, or another local coding host, or when they need repo-scoped guidance that keeps the Apple Notes backup control-room identity and host-proof boundaries honest.
---

# Apple Notes Snapshot Control-Room

Use this skill to connect Apple Notes Snapshot to local coding hosts without
rewriting it into a hosted AI product.

## Identity first

- Apple Notes local-first backup control room for macOS
- `notesctl` is the canonical human entrypoint
- `AI Diagnose` is an advisory sidecar
- `Local Web API` is token-gated and same-machine
- `MCP` is stdio-first and read-only-first

## Preflight before attach claims

Do not treat host registration as proof by itself.

Verify:

1. `./notesctl run --no-status`
2. `./notesctl verify`
3. `./notesctl doctor --json`
4. `./notesctl status --json`

If those fail, classify the issue as local snapshot preflight, not an MCP
transport bug.

## Distribution boundary

- Repo-owned starter packs and local marketplaces are wiring kits.
- They are not the same thing as official public directory listings.
- A fresh named-host attach proof on one machine does not become a universal
  proof for every machine or every host build.

## Best-fit use cases

- Repo-scoped guidance for Codex, Claude Code, OpenClaw, or another local host
- Public skill distribution through an OpenHands or ClawHub-style skill lane
- Public-facing docs or README edits that must keep builder wording honest

## Do not overclaim

- Do not reposition Apple Notes Snapshot as a hosted agent platform.
- Do not claim official marketplace or directory listing unless it truly landed.
- Do not collapse repo-side proof, current-host proof, and public registry
  publication into one sentence.
