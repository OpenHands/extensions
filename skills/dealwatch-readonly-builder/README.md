# DealWatch Read-only Builder

This public skill package turns the current DealWatch builder front door into a
registry-friendly skill surface.

It is meant for host ecosystems that accept skill directories built around a
`SKILL.md` contract plus a manifest.

## What it does

- routes builders to the safe first DealWatch entry path
- keeps the workflow local-first and read-only
- points back to the current builder starter pack and compare preview loop

## What it does not claim

- no hosted DealWatch control plane
- no write-side MCP surface
- no official marketplace listing unless the registry itself confirms one
