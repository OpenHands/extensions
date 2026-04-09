# ProofTrail MCP Capabilities

These are the current tool families surfaced by ProofTrail's governed MCP
server.

## Best first tools

1. `uiq_catalog`
   - read the top-level capability and surface catalog
2. `uiq_read`
   - inspect one run, artifact, or repo-owned proof surface
3. `uiq_quality_read`
   - summarize failures, quality, and gate posture without mutation
4. `uiq_proof`
   - inspect proof bundles and recovery/evidence surfaces

## Good next actions

- `uiq_run`
- `uiq_run_and_report`
- `uiq_api_workflow`
- `uiq_api_automation`

Use these only after the safe-first catalog and read path is already grounded.

## Useful supporting tools

- `uiq_model_target_capabilities`
- `uiq_compare_perf`
- `uiq_read_proof_report`
- `uiq_export_proof_bundle`
- `uiq_run_deep_load_localhost`

Treat these as follow-through tools, not the first thing a reviewer should see.
