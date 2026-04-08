# Campus Copilot Capability Map

This skill is intentionally narrow. It does not need every tool every time.

## Core MCP tools

- `campus_health`: verify that the local Campus Copilot BFF is alive
- `providers_status`: check whether cited-answer providers are ready
- `ask_campus_copilot`: answer one student question over the Campus semantic contract
- `canvas_snapshot_view`: inspect Canvas snapshot records
- `gradescope_snapshot_view`: inspect Gradescope snapshot records
- `edstem_snapshot_view`: inspect EdStem snapshot records
- `myuw_snapshot_view`: inspect MyUW snapshot records
- `export_snapshot_artifact`: export a portable snapshot artifact

## Best default order

1. `campus_health`
2. one or more `*_snapshot_view` tools
3. `ask_campus_copilot` if a question exists
4. `export_snapshot_artifact` only if the operator needs a saved proof artifact
