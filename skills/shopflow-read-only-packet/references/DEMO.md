# Shopflow MCP First-Success Demo

This is the shortest packet loop that proves the skill is real.

## Demo prompt

Use Shopflow to inspect the current public distribution truth. Start with
`get_integration_surface` and `get_submission_readiness`. If the packet looks
healthy, read `get_public_distribution_bundle` and summarize which part is
repo-ready, which part is owner-only later, and which claim is still out of
bounds.

## Expected tool sequence

1. `get_integration_surface`
2. `get_submission_readiness`
3. `get_public_distribution_bundle`
4. `get_runtime_seam`

## Visible success criteria

- the MCP server launches
- the packet summary points to real repo-owned JSON surfaces
- the answer separates repo-ready from store-ready instead of flattening them
