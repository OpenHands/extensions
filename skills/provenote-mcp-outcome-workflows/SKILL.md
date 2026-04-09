---
name: provenote-mcp-outcome-workflows
description: Teach an agent to install Provenote's first-party MCP server, connect it in a host, and run read-first outcome workflows.
version: 1.1.1
triggers:
  - provenote
  - provenote-mcp
  - research thread
  - auditable run
  - source-grounded notes
---

# Provenote MCP Outcome Workflows

Teach the agent how to install, connect, and use Provenote's first-party MCP
server for read-first note and research workflows.

## Use this skill when

- the user wants to turn messy long context into structured drafts or research threads
- the host can run a local MCP server
- the user wants inspectable outcomes before broad write automation

## What this package teaches

- how to launch `provenote-mcp` from a local clone
- how to wire it into OpenHands or OpenClaw
- which read-first MCP tools to use first
- which write actions are narrow and safe to try next

## Start here

1. Read [references/INSTALL.md](references/INSTALL.md)
2. Load the right host config from:
   - [references/OPENHANDS_MCP_CONFIG.json](references/OPENHANDS_MCP_CONFIG.json)
   - [references/OPENCLAW_MCP_CONFIG.json](references/OPENCLAW_MCP_CONFIG.json)
3. Skim the tool surface in [references/CAPABILITIES.md](references/CAPABILITIES.md)
4. Run the demo from [references/DEMO.md](references/DEMO.md)

## Read-first workflow

1. `draft.list`
2. `research_thread.list`
3. `auditable_run.list`
4. only then move to one narrow write-oriented action

## Safe first mutations

- `research_thread.to_draft`
- `draft.verify`
- `draft.download`
- `auditable_run.create`
- `auditable_run.download`

## Suggested first prompt

Use Provenote to inspect the current drafts, research threads, and auditable
runs for this workspace. Start with `draft.list`, `research_thread.list`, and
`auditable_run.list`. After you summarize what already exists, choose one
narrow next step: either convert a research thread into a draft with
`research_thread.to_draft` or verify an existing draft with `draft.verify`.

## Success checks

- the host can launch `provenote-mcp` from the provided config
- the three read-first list calls succeed
- one narrow mutation succeeds and maps back to an inspectable artifact

## Boundaries

- Provenote stays centered on its first-party MCP server
- keep outcome claims tied to inspectable repo-owned artifacts
