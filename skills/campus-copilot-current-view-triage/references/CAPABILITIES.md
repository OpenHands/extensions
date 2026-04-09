# Campus Copilot Capability Map

This skill intentionally stays on the read-only Campus Copilot surfaces.

## Core MCP tools

- `campus_health`
- `providers_status`
- `ask_campus_copilot`
- `canvas_snapshot_view`
- `gradescope_snapshot_view`
- `edstem_snapshot_view`
- `myuw_snapshot_view`
- `export_snapshot_artifact`

## Best default order

1. `campus_health`
2. one or more `*_snapshot_view` tools
3. `ask_campus_copilot` if a question exists
4. `export_snapshot_artifact` only if the operator needs a saved proof artifact
