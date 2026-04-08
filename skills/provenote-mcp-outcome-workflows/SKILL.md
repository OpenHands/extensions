---
name: provenote-mcp-outcome-workflows
description: Teach an agent to install Provenote's first-party MCP server, connect it in a host, and run read-first outcome workflows.
version: 1.1.0
triggers:
  - provenote
  - provenote-mcp
  - research thread
  - auditable run
  - source-grounded notes
---

# Provenote MCP Outcome Workflows

Teach the agent how to install, connect, and use Provenote's first-party MCP
server for structured, source-grounded note and research workflows.

## Use this skill when

- the user wants to turn messy long context into structured drafts or research threads
- the host can run a local MCP server
- the user wants inspectable outcomes before broad write automation

## What the agent should know

- Provenote ships a first-party MCP entrypoint: `provenote-mcp`
- the most important read surfaces are drafts, research threads, and auditable runs
- the safest first success path is to inspect existing outcomes before mutating anything

## Start here

1. Read [references/INSTALL.md](references/INSTALL.md)
2. Load the right host config from:
   - [references/OPENHANDS_MCP_CONFIG.json](references/OPENHANDS_MCP_CONFIG.json)
   - [references/OPENCLAW_MCP_CONFIG.json](references/OPENCLAW_MCP_CONFIG.json)
3. Skim the tool surface in [references/CAPABILITIES.md](references/CAPABILITIES.md)
4. Run the demo from [references/DEMO.md](references/DEMO.md)

## Recommended workflow

1. `draft.list`
2. `research_thread.list`
3. `auditable_run.list`
4. Pick one narrow write-oriented action only after the read surfaces make sense

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

## Validation

Before treating the workflow as working, prove all four:

1. the host can execute `provenote-mcp`
2. a read-first tool succeeds
3. one narrow write-oriented workflow succeeds
4. the result maps back to an inspectable repo-owned surface

## Boundaries

- keep Provenote centered on its first-party MCP server
- keep outcome claims tied to inspectable repo-owned artifacts
