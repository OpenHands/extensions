---
name: prompt-switchboard-compare-workflows
description: Teach an agent to install Prompt Switchboard's local MCP sidecar, connect it in a host, and run a compare-first browser workflow.
version: 1.1.1
triggers:
  - prompt switchboard
  - prompt-switchboard
  - prompt_switchboard
  - compare-first
  - multi-ai-sidepanel
---

# Prompt Switchboard Compare Workflows

Teach the agent how to install, connect, and use Prompt Switchboard as a
compare-first browser workspace.

## Use this skill when

- the user wants to compare the same prompt across multiple already-open AI chat tabs
- the host can run a local MCP server
- the user wants one inspectable compare artifact before broader automation

## What this package teaches

- how to wire the local Prompt Switchboard MCP sidecar into a host
- which MCP tools are safe and useful first
- how to move from readiness checks to a real compare turn
- how to keep the workflow grounded in a browser-native compare product

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

- Prompt Switchboard stays a local browser workflow, not a hosted service
- the MCP sidecar supports compare workflows; it does not replace the extension
- keep claims grounded in the actual tool surface documented in this package
