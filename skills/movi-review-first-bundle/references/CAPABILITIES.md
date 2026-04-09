# Movi MCP Capabilities

These are the current repo-owned Movi MCP tools exposed by `npm run mcp:tools`.

## Best first tools

1. `jobs.list`
   - inspect the current batch queue before choosing a target
2. `review_queue.get`
   - see what is waiting for review-first attention
3. `manifest.get`
   - inspect the current manifest state before proposing any patch
4. `analyze.create`
   - create one analysis artifact without mutating the batch

## Useful follow-through tools

- `jobs.get`
- `report.get`
- `strategy_packs.list`
- `watch_sources.list`
- `inbox.scan`
- `inbox.analyze`

Use these after the first-safe picture is already clear.

## Heavier mutation tools

- `manifest.patch_row`
- `manifest.batch_patch`
- `review_rule.preview`
- `review_rule.apply`
- `apply.preview`

Treat these as gated actions. Do not run them in the first pass unless the user
explicitly asks for a patch or rule change.
