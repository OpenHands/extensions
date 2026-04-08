---
name: prompt-switchboard-compare-workflows
description: Teach an agent to install Prompt Switchboard's local MCP sidecar, connect it in a host, and run a compare-first browser workflow.
version: 1.1.0
triggers:
  - prompt switchboard
  - prompt-switchboard
  - prompt_switchboard
  - compare-first
  - multi-ai-sidepanel
---

# Prompt Switchboard Compare Workflows

Teach the agent how to install, connect, and use Prompt Switchboard as a local
browser workspace for side-by-side AI comparison.

## Use this skill when

- the user wants to compare the same prompt across multiple already-open AI chat tabs
- the host can run a local MCP server
- the user wants one inspectable compare artifact before broader automation

## What the agent should know

- Prompt Switchboard is a compare-first browser extension workspace
- the MCP sidecar is local and supports readiness, compare, analysis, export, and workflow tools
- the first success path is bridge -> readiness -> compare

## Start here

1. Read [references/INSTALL.md](references/INSTALL.md)
2. Load the right host config from:
   - [references/OPENHANDS_MCP_CONFIG.json](references/OPENHANDS_MCP_CONFIG.json)
   - [references/OPENCLAW_MCP_CONFIG.json](references/OPENCLAW_MCP_CONFIG.json)
3. Skim the tool surface in [references/CAPABILITIES.md](references/CAPABILITIES.md)
4. Run the demo from [references/DEMO.md](references/DEMO.md)

## Recommended workflow

1. `prompt_switchboard.bridge_status`
2. `prompt_switchboard.check_readiness`
3. `prompt_switchboard.compare`
4. `prompt_switchboard.analyze_compare`
5. `prompt_switchboard.run_workflow`

## Suggested first prompt

Use Prompt Switchboard to compare the prompt below across the ready ChatGPT and
Gemini tabs. Start with `prompt_switchboard.bridge_status` and
`prompt_switchboard.check_readiness`. If fewer than two model tabs are ready,
stop and tell me exactly which login or tab-prep step is missing. If two or
more tabs are ready, run `prompt_switchboard.compare` and summarize the most
important wording differences.

## Success checks

- the host can launch the MCP server from the provided config
- `bridge_status` confirms the local bridge is reachable
- `check_readiness` identifies which tabs are ready
- `compare` produces a real session/turn artifact the agent can inspect

## Boundaries

- treat Prompt Switchboard as a local browser workflow, not a hosted platform
- keep claims grounded in the MCP tool surface documented in this package
