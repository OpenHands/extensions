# First-Success Path

This is the shortest demo that proves the skill does real work instead of only
describing a workflow.

## Demo prompt

Use Movi to inspect the current review-first batch queue. Start with
`jobs.list`, `review_queue.get`, and `manifest.get`. Summarize which batch needs
attention first. If the manifest is present and stable, run `analyze.create` to
produce one analysis artifact. Stop before `manifest.patch_row`,
`manifest.batch_patch`, or `review_rule.apply` unless I explicitly ask for a
change.

## Expected tool sequence

1. `jobs.list`
2. `review_queue.get`
3. `manifest.get`
4. `analyze.create`

## Visible success criteria

- the host attaches the local Movi MCP server
- the agent names at least one real job or review queue item
- the analysis step points back to a real manifest or batch artifact
- the agent keeps the workflow review-first instead of jumping into mutation

## What to check if it fails

1. the host config path still points at the real repo checkout
2. `bash tooling/runtime/bootstrap_env.sh` was run
3. `npm run mcp:tools` returns the tool inventory without errors
