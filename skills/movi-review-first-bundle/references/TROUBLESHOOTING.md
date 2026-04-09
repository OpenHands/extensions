# Troubleshooting

## The host cannot attach the MCP server

- confirm the repo path in the host config is real
- run `bash tooling/runtime/bootstrap_env.sh`
- rerun `npm run mcp:tools` from the repo root

## The tool list is empty or incomplete

- confirm the runtime bootstrap finished
- verify the command still points at `tooling/runtime/run_mcp_stdio.sh`
- check whether the current shell has the expected Node environment

## The review-first demo drifts into mutation

- restart from `jobs.list` and `review_queue.get`
- treat `manifest.patch_row`, `manifest.batch_patch`, and `review_rule.apply`
  as operator-approved actions only
- keep `analyze.create` as the last allowed first-pass step
