# Troubleshooting

## The host cannot attach the MCP server

- confirm the `cwd` points at the real repo checkout
- rerun `pnpm install`
- rerun `pnpm mcp:check`

## The MCP server starts but cannot see live backend state

- confirm whether this task actually needs live backend reads
- if yes, set `UIQ_MCP_API_BASE_URL` and any required token env vars
- otherwise stay on repo-owned proof and artifact surfaces only

## The agent jumps straight into heavy run tools

- restart from `uiq_catalog`, `uiq_read`, and `uiq_quality_read`
- treat `uiq_run` and `uiq_api_automation` as second-pass tools
- keep the first pass evidence-first and read-oriented
