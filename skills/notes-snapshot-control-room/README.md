# Apple Notes Snapshot Control-Room

OpenHands skill for the Apple Notes Snapshot local-first backup control room on
macOS.

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

- operators who want a calmer Apple Notes backup loop on their own Mac
- repo-scoped guidance for hosts that consume a stdio-first MCP server
- public skill-folder distribution lanes that need an honest control-room story

## What this skill does not claim

- no hosted runtime or Docker lane for the full product
- no universal attach proof on every machine
- no official marketplace listing unless a host-side read-back confirms it
