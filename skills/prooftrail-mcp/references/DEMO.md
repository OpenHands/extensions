# First-Success Path

## Demo prompt

Use ProofTrail as a governed browser-evidence layer. Start with `uiq_catalog`
to confirm the MCP surface is attached. Then use `uiq_read` or
`uiq_quality_read` to inspect one existing run or failure surface. If a real run
is already present, follow with `uiq_proof` or `uiq_run_and_report` to show the
retained evidence and summarize the most important next action.

## Expected tool sequence

1. `uiq_catalog`
2. `uiq_read`
3. `uiq_quality_read`
4. `uiq_proof` or `uiq_run_and_report`

## Visible success criteria

- the host attaches the MCP server successfully
- the agent cites a real repo-owned run, proof bundle, or failure surface
- the answer stays grounded in evidence instead of generic browser-automation
  claims

## What to check if it fails

1. `pnpm mcp:start` starts from the repo root
2. `pnpm mcp:check` passes
3. if you need live backend reads, `UIQ_MCP_API_BASE_URL` points at a reachable
   backend
