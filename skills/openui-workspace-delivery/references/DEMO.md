# OpenUI MCP Studio First-Success Demo

This is the shortest proof loop that shows the packet is real.

## Demo prompt

Use OpenUI MCP Studio to inspect this workspace and prepare one safe-first UI
delivery step. Start with `openui_scan_workspace_profile` and
`openui_plan_change`. If the workspace looks healthy, run `openui_generate_ui`
for one small component or page change, then run `openui_quality_gate` and
summarize what a reviewer should inspect next.

## Expected tool sequence

1. `openui_scan_workspace_profile`
2. `openui_plan_change`
3. `openui_generate_ui`
4. `openui_quality_gate`
5. `openui_build_review_bundle`

## Visible success criteria

- the MCP server launches from the provided config
- the workspace profile is real and repo-specific
- the generation step produces a concrete UI payload or change plan
- the quality gate reports repo-owned findings instead of placeholder prose
