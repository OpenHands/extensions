# docsiphon Doc Corpus Operator

This folder is a host-native public skill packet for `docsiphon`.

The flagship public story is still:

- GitHub repo front door
- `uvx` quickstart
- release assets / example profiles

This packet exists for host reviewers who need a self-contained folder that
teaches an agent how to run the Docsiphon CLI, export one small documentation
corpus, and inspect the resulting audit artifacts without turning Docsiphon
into a hosted platform or an MCP-first product.

## What this packet teaches

This packet teaches an agent how to:

1. install or invoke Docsiphon through the current CLI-first path
2. run one small, scoped export against a documentation subtree
3. inspect the resulting manifest and report artifacts
4. stay inside the current product boundary instead of promising a generic site
   mirror or hosted browser workflow

## What this packet includes

- `SKILL.md`
- `manifest.yaml`
- `references/README.md`
- `references/INSTALL.md`
- `references/DEMO.md`
- `references/CAPABILITIES.md`
- `references/TROUBLESHOOTING.md`

## First-success path

1. read `SKILL.md`
2. follow `references/INSTALL.md`
3. run the small scoped export in `references/DEMO.md`
4. inspect `manifest.jsonl`, `report.json`, `toc.md`, and `report.html`

## Current registry truth

- `ClawHub`: `not submitted yet`
- `OpenHands/extensions`: `not submitted yet`

This packet is still a **secondary host-native lane**.
It does not replace the current `CLI-first` primary surface.

## What this packet must not claim

- no hosted documentation export platform
- no listed-live ClawHub entry yet
- no listed-live OpenHands/extensions entry yet
- no MCP-first product positioning

## Source of truth

Canonical product truth still lives in:

- `README.md`
- `AGENTS.md`
- `docs/README.md`
