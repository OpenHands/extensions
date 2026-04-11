---
name: docsiphon-doc-corpus-operator
description: Use when an agent needs to run Docsiphon through the CLI-first path, export a small documentation subtree, and inspect the resulting audit artifacts without overclaiming hosted or MCP-first product status.
triggers:
  - docsiphon
  - documentation corpus export
  - llms.txt
  - sitemap
  - manifest.jsonl
  - report.html
---

# docsiphon Doc Corpus Operator

Use this skill when an agent needs to run the current Docsiphon CLI flow and
inspect the resulting export artifacts from a repo checkout or `uvx` path.

## Product truth

- `docsiphon` is currently `CLI-first`
- this packet is a host-native secondary lane
- the packet teaches export and artifact inspection, not a hosted browser
  workflow
- any future MCP-aware surface remains future secondary until it ships its own
  install contract, verification gate, public packet, and lane truth

## Current registry truth

- `ClawHub`: `not submitted yet`
- `OpenHands/extensions`: `not submitted yet`

## First-success flow

1. Follow `references/INSTALL.md`
2. Run the small scoped export in `references/DEMO.md`
3. Inspect `manifest.jsonl`, `report.json`, `toc.md`, and `report.html`
4. Only after the first export works, move to bigger site scopes or custom
   profiles

## Preferred evidence order

1. `references/INSTALL.md`
2. `references/DEMO.md`
3. `references/CAPABILITIES.md`
4. `references/TROUBLESHOOTING.md`

## Truth language

- Good: `CLI-first`
- Good: `scoped export`
- Good: `audit artifacts`
- Good: `host-native secondary lane`
- Forbidden: `hosted platform`
- Forbidden: `listed-live` without fresh host read-back
- Forbidden: `MCP-first`

## Read next

- `references/README.md`
- `references/INSTALL.md`
- `references/DEMO.md`
- `references/CAPABILITIES.md`
- `references/TROUBLESHOOTING.md`
