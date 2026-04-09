# Apple Notes Snapshot Control-Room

This folder is the public skill packet for Apple Notes Snapshot's local-first
backup control room.

## What this skill teaches an agent

- how to acquire `notesctl` from a public checkout or reuse an existing one
- how to prove the operator lane before touching builder surfaces
- how to wire `notesctl mcp` into a local host
- how to separate AI Diagnose, Local Web API, and MCP into honest lanes
- how to talk about attach proof without overstating what is universal

## First-success path

1. Read `SKILL.md`
2. Open `references/install-and-attach.md`
3. Acquire `notesctl`, then run the proof path from
   `references/usage-and-proof.md`
4. Only then attach the MCP lane or explain host-specific boundaries

## Demo / proof links

- Landing: https://xiaojiou176-open.github.io/apple-notes-snapshot/
- Quickstart: https://xiaojiou176-open.github.io/apple-notes-snapshot/quickstart/
- Proof page: https://xiaojiou176-open.github.io/apple-notes-snapshot/proof/
- MCP guide: https://xiaojiou176-open.github.io/apple-notes-snapshot/mcp/
- For Agents: https://xiaojiou176-open.github.io/apple-notes-snapshot/for-agents/

## Visual demo

![Apple Notes Snapshot first-success run flow](https://raw.githubusercontent.com/xiaojiou176-open/apple-notes-snapshot/main/assets/readme/run-flow.gif)

- Quick visual proof:
  the skill now points to a concrete run-flow demo, not just prose-only setup
  instructions.

## MCP capability surface

- Post-attach checks:
  `get_status`, `run_doctor`, `verify_freshness`, `get_log_health`,
  `list_recent_runs`, and `get_access_policy`
- First resource to read back:
  `notes-snapshot://recent-runs`
- Boundary:
  local stdio only, read-only-first tools/resources, and no hosted runtime

## Best fit

- operators who want a bounded Apple Notes backup loop on their own Mac
- repo-scoped guidance for hosts that consume a stdio-first MCP server
- public skill-folder distribution lanes that need an honest control-room story

## What this skill does not claim

- no hosted runtime or Docker lane for the full product
- no universal attach proof on every machine
- no official marketplace listing unless a host-side read-back confirms it

## What this packet includes

- `SKILL.md`
  - the agent-facing workflow entry
- `README.md`
  - the human-facing packet overview
- `manifest.yaml`
  - registry-style metadata for host skill registries
- `references/README.md`
  - the local index for every supporting file
- `references/INSTALL.md`
  - install and host wiring guidance
- `references/OPENHANDS_MCP_CONFIG.json`
  - a ready-to-edit `mcpServers` snippet
- `references/OPENCLAW_MCP_CONFIG.json`
  - a ready-to-edit `mcp.servers` snippet
- `references/CAPABILITIES.md`
  - the MCP capability map and safe-first order
- `references/DEMO.md`
  - the first-success walkthrough and expected output shape
- `references/TROUBLESHOOTING.md`
  - the first places to check when preflight or attach fails
