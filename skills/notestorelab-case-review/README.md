# NoteStore Lab Case Review Public Skill

This folder is the OpenHands/extensions-friendly and ClawHub-style public skill
packet for NoteStore Lab.

## What this skill teaches an agent

This is not just a label for Apple Notes. It teaches an agent five concrete
things:

1. how to install or launch the NoteStore Lab MCP surface
2. how to prove the review flow on public-safe demo artifacts first
3. how to review one copied case root without touching the live Notes store
4. how to ask bounded questions from derived artifacts instead of guessing
5. what the MCP lane gives a host after attach: case-root listing, manifest and
   artifact inspection, bounded case Q&A, and bounded
   verify/report/timeline/export workflows

## What this packet includes

- `SKILL.md`
  - the concise skill entry point for progressive disclosure
- `manifest.yaml`
  - listing metadata for ClawHub-style publication
- `references/README.md`
  - the local index for every supporting file
- `references/INSTALL.md`
  - exact install and MCP wiring examples
- `references/OPENHANDS_MCP_CONFIG.json`
  - a ready-to-edit `mcpServers` snippet
- `references/OPENCLAW_MCP_CONFIG.json`
  - a ready-to-edit `mcp.servers` snippet
- `references/CAPABILITIES.md`
  - the read-mostly case-review tool surface
- `references/DEMO.md`
  - first-success flow, real prompts, and proof/demo links
- `references/TROUBLESHOOTING.md`
  - the first places to check when attach or case-root review fails

## First-success path

If a reviewer wants to understand the skill quickly, use this order:

1. read `SKILL.md`
2. open `references/install-and-mcp.md`
3. run the public-safe proof path from `references/usage-and-proof.md`
4. inspect the public proof links before claiming anything is officially listed

## Demo / proof links

- Landing: https://xiaojiou176-open.github.io/apple-notes-forensics/
- Public proof: https://github.com/xiaojiou176-open/apple-notes-forensics/blob/main/proof.html
- Builder guide: https://github.com/xiaojiou176-open/apple-notes-forensics/blob/main/INTEGRATIONS.md
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

## Best-fit hosts

- OpenHands/extensions contribution flow
- ClawHub-style skill publication
- repo-local skill import flows that expect a standalone folder
- any MCP-aware host that can launch a local stdio server on one explicit case
  root

## What this packet must not claim

- no official OpenHands/extensions listing without fresh PR/read-back
- no live ClawHub listing without fresh host-side read-back
- no hosted Glama deployment, Docker catalog listing, or remote MCP lane
- no direct mutation of the live Apple Notes store

## Source of truth

The canonical skill text still lives at:

- `skills/notestorelab-case-review/SKILL.md`

This folder is a public-facing derived packet. If the canonical skill changes,
copy the updated `SKILL.md` here before publishing.
