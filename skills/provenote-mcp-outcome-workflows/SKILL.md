---
name: provenote-mcp-outcome-workflows
description: Use this skill when you want Provenote's first-party MCP outcome workflows through a host-facing skill packet without overclaiming a live listing or marketplace status.
version: 1.0.0
---

# Provenote MCP Outcome Workflows

Teach the agent how to use Provenote's first-party MCP server for structured,
source-grounded note and research workflows.

## Use this skill when

- the user wants to turn messy long context into structured drafts or research threads
- the user wants auditable outcomes instead of free-form note taking
- the user wants a read-first MCP workflow before narrow write actions

## What the agent should know

- Provenote ships a first-party MCP entrypoint: `provenote-mcp`
- the most important read surfaces are drafts, research threads, and auditable runs
- the safest first success path is to inspect existing outcomes before mutating anything

## Recommended workflow

1. List drafts
2. List research threads
3. List auditable runs
4. Pick one narrow write-oriented action only after the read surfaces make sense

## Good first actions

- summarize the current draft set
- inspect how a research thread maps into a draft
- create or download one auditable run tied to a real repo-owned result

## Safe first mutations

- `research_thread.to_draft`
- `draft.verify`
- `draft.download`
- `auditable_run.create`
- `auditable_run.download`

## Validation

Before treating the workflow as working, prove all four:

1. the host can execute `provenote-mcp`
2. a read-first tool succeeds
3. one narrow write-oriented workflow succeeds
4. the result maps back to an inspectable repo-owned surface

## Boundaries

- keep Provenote centered on its first-party MCP server
- keep outcome claims tied to inspectable repo-owned artifacts
