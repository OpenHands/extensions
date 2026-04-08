---
name: cortexpilot-adoption-router
description: Route the current job to the right CortexPilot surface without overclaiming hosted, write-capable MCP, or published plugin support.
---

# Purpose

Use this skill when a coding-agent workflow needs the shortest honest CortexPilot
entrypoint.

The job is to pick the right adoption lane first instead of treating every host
tool as the same kind of plugin system.

# Read Order

1. `README.md`
2. `docs/README.md`
3. `docs/compatibility/index.html`
4. `docs/integrations/index.html`
5. One deeper lane only:
   - `docs/mcp/index.html`
   - `docs/skills/index.html`
   - `docs/builders/index.html`
   - `docs/use-cases/index.html`

# Use It To Choose A Lane

- Start with **read-only MCP** when the first need is machine-readable
  inspection.
- Start with **skills** when the first need is repeatable repo-owned behavior.
- Start with **builders** when the first need is package-level reuse.
- Start with **use cases** when the first need is proof-first product
  understanding.

# Guardrails

- Do not describe CortexPilot as a hosted operator product.
- Do not describe the public MCP surface as write-capable.
- Do not claim this bundle is a published Codex or OpenClaw listing.
- Do not describe Claude Code as if it has a CortexPilot marketplace package.
- Keep `task_contract` as the only execution authority.

# Done Signal

The adoption path is correct only when the chosen lane matches the real job and
the wording stays below official-listing or hosted-product claims.
