# NoteStore Lab Case Review

OpenHands skill for reviewing one NoteStore Lab Apple Notes case root without
turning the workflow into a hosted service.

## What this skill teaches an agent

- how to install or launch the NoteStore Lab MCP surface
- how to prove the workflow on public-safe demo artifacts first
- how to inspect one case root at a time using derived artifacts first
- how to ask bounded, evidence-backed questions instead of guessing
- what the MCP lane gives a host after attach: case-root listing, manifest and
  artifact inspection, bounded case Q&A, and bounded verify/report/timeline or
  public-safe-export workflows

## First-success path

1. Read `SKILL.md`
2. Open `references/install-and-mcp.md`
3. Run the public-safe proof flow from `references/usage-and-proof.md`
4. Only after that, point the MCP command at one explicit case root

## Demo / proof links

- Landing: https://xiaojiou176-open.github.io/apple-notes-forensics/
- Public proof: https://github.com/xiaojiou176-open/apple-notes-forensics/blob/main/proof.html
- Builder guide: https://github.com/xiaojiou176-open/apple-notes-forensics/blob/main/INTEGRATIONS.md
- Distribution boundary: https://github.com/xiaojiou176-open/apple-notes-forensics/blob/main/DISTRIBUTION.md
- Releases: https://github.com/xiaojiou176-open/apple-notes-forensics/releases

## Visual demo

![NoteStore Lab public demo surface](https://raw.githubusercontent.com/xiaojiou176-open/apple-notes-forensics/main/assets/readme/hero-public-demo.png)

- Quick visual proof: the public demo already shows the bounded review flow on
  safe artifacts before a host ever points the MCP lane at a real copied case
  root.

## MCP capability surface

- Read-only review lane:
  `list_case_roots`, `inspect_case_manifest`, `select_case_evidence`,
  `inspect_case_artifact`, and `ask_case`
- Bounded workflows:
  `run_verify`, `run_report`, `build_timeline`, and `public_safe_export`
- Boundary:
  one explicit case root at a time, local stdio transport, and no live Notes
  store mutation path

## Best fit

- copied-evidence Apple Notes investigations on macOS
- one bounded case root at a time
- derived-artifact-first AI review and case Q&A
- local stdio MCP hosts that need the same review-safe surfaces as the CLI

## What this skill does not claim

- no official OpenHands listing beyond this registry entry
- no live Notes store access
- no hosted or multi-tenant Notes recovery platform
- no remote MCP deployment
