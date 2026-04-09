# Troubleshooting

## The host cannot attach the MCP server

- confirm the `cwd` points at the real repo checkout
- rerun `pnpm install`
- rerun `pnpm mcp:check` and `pnpm mcp:build`

## The MCP server starts but the live stack is unreachable

- set `UIQ_MCP_API_BASE_URL=http://127.0.0.1:17380`
- confirm the backend health endpoint is reachable
- if the task does not need live API reads, stay on repo-native docs and proof
  surfaces instead

## The agent jumps into advanced tools too early

- restart from `uiq_catalog`
- keep `uiq_run`, `uiq_run_and_report`, and `uiq_proof` as the first-success path
- treat release-analysis and similarity tools as second-pass reviewer aids
