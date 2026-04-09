# First-Success Path

## Demo prompt

Use Prooflane as a repo-native MCP surface. Start with `uiq_catalog` to confirm
the server is attached. Then inspect one run or run summary with `uiq_run` or
`uiq_run_and_report`. If proof artifacts are already present, follow with
`uiq_proof` or `uiq_read_artifact`. Summarize the current lane, the most
important proof artifact, and the next action without claiming a published
marketplace listing.

## Expected tool sequence

1. `uiq_catalog`
2. `uiq_run`
3. `uiq_run_and_report`
4. `uiq_proof` or `uiq_read_artifact`

## Visible success criteria

- the host attaches the repo-native MCP server
- the agent cites one real run or artifact instead of a generic stress-lab
  story
- the answer stays grounded in current repo-native Prooflane surfaces

## What to check if it fails

1. `pnpm mcp:check` still passes
2. `UIQ_MCP_API_BASE_URL` points at a reachable backend if live reads are needed
3. the host config still points at the real repo checkout
