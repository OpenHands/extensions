---
name: provenote-mcp-outcome-workflows
description: Use this skill when you want Provenote's first-party MCP outcome workflows through a host-facing skill packet without overclaiming a live listing or marketplace status.
version: 1.0.0
---

# Provenote MCP Outcome Workflows

## Purpose

Help an OpenHands user consume Provenote's first-party MCP surfaces without
rewriting the repo into a hosted platform or a generic public skills catalog.

## Read-first workflow

1. list drafts
2. list research threads
3. list auditable runs
4. only then move to one narrow write-oriented action

## Safe first mutations

- `research_thread.to_draft`
- `draft.verify`
- `draft.download`
- `auditable_run.create`
- `auditable_run.download`

## Validation

Before calling this skill working, prove all four:

1. the host can execute `provenote-mcp`
2. a read-first tool succeeds
3. one narrow write-oriented workflow succeeds
4. the result maps back to an inspectable repo-owned surface

## Boundary

- public-ready host-facing skill packet from this repository
- not a live OpenHands/extensions listing yet
- not a live ClawHub listing yet
- not a public skills catalog or marketplace surface by itself
