---
name: dealwatch-readonly-builder
description: Safe-first builder route for DealWatch. Start with runtime readiness and the builder starter pack before deeper reads.
---

# DealWatch Read-only Builder

Use DealWatch as a local-first, read-only decision backend.

## Safe First Flow

1. `get_runtime_readiness`
2. `get_builder_starter_pack`
3. `compare_preview`
4. one read-only detail route

## Do Not Assume

- write-side MCP
- hosted control plane
- official marketplace or registry listing
- autonomous recommendation support
