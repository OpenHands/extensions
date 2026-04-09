# OpenUI MCP Studio Capabilities

OpenUI MCP Studio exposes a local UI generation and review workflow.

## Core workflow tools

- `openui_scan_workspace_profile`
- `openui_plan_change`
- `openui_generate_ui`
- `openui_convert_react_shadcn`
- `openui_make_react_page`
- `openui_apply_files`
- `openui_quality_gate`
- `openui_next_smoke`
- `openui_ship_react_page`

## Delivery-intelligence tools

- `openui_build_acceptance_pack`
- `openui_build_review_bundle`
- `openui_ship_feature_flow`

## Supporting tools

- `openui_refine_ui`
- `openui_review_uiux`
- `openui_list_models`
- `openui_embed_content`

## Recommended first-use order

1. `openui_scan_workspace_profile`
2. `openui_plan_change`
3. `openui_generate_ui`
4. `openui_quality_gate`
5. `openui_build_review_bundle`

## Boundary

- good fit: local MCP-first UI generation, review, and proof
- not a fit: claiming hosted runtime, official marketplace listing, or a vendor
  managed install surface
