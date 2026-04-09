---
name: openui-workspace-delivery
description: Teach an agent how to install OpenUI MCP Studio, connect it to a host, and use the core UI generation and review workflow without overclaiming a live marketplace listing.
version: 1.0.0
triggers:
  - openui
  - openui-mcp-studio
  - openui workspace delivery
  - shadcn generation
  - UI shipping
---

# OpenUI Workspace Delivery

Teach the agent how to install, connect, and use OpenUI MCP Studio as a local
MCP-first UI generation and review workspace.

## Use this skill when

- the user wants to generate or review shadcn-style UI from a local MCP server
- the host can run a local `stdio` MCP server
- the user wants one inspectable proof loop before any public claim

## What this packet teaches

- how to wire the local OpenUI MCP server into OpenHands or OpenClaw
- which OpenUI MCP tools are safe and useful first
- how to move from installation to a first proof loop
- how to keep claims grounded in local MCP and repo-owned proof instead of
  marketplace hype

## Start here

1. Read [references/INSTALL.md](references/INSTALL.md)
2. Load the right host config from:
   - [references/OPENHANDS_MCP_CONFIG.json](references/OPENHANDS_MCP_CONFIG.json)
   - [references/OPENCLAW_MCP_CONFIG.json](references/OPENCLAW_MCP_CONFIG.json)
3. Skim the tool surface in [references/CAPABILITIES.md](references/CAPABILITIES.md)
4. Run the proof loop in [references/DEMO.md](references/DEMO.md)
5. If attach or proof fails, use
   [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md)

## Recommended workflow

1. `openui_scan_workspace_profile`
2. `openui_plan_change`
3. `openui_generate_ui`
4. `openui_quality_gate`
5. `openui_build_review_bundle`

## Suggested first prompt

Use OpenUI MCP Studio to inspect this workspace and prepare one safe-first UI
delivery step. Start with `openui_scan_workspace_profile` and
`openui_plan_change`. If the workspace looks healthy, run `openui_generate_ui`
for one small component or page change, then run `openui_quality_gate` and
summarize what a reviewer should inspect next.

## Success checks

- the host can launch the OpenUI MCP server from the provided config
- the workspace scan returns a real profile instead of placeholder text
- the plan/generate flow yields a concrete UI output or change plan
- the proof loop stays inside local MCP and repo-owned evidence

## Boundaries

- OpenUI MCP Studio stays a local MCP and repo-owned proof workflow
- this packet does not claim a live ClawHub listing or a vendor marketplace
  listing
- this packet does not claim a hosted runtime or hosted API publication
