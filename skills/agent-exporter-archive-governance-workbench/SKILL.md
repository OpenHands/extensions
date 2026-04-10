---
name: agent-exporter-archive-governance-workbench
description: Use when an agent needs to attach the local agent-exporter stdio bridge, publish a local archive shell, save retrieval reports, or read governance evidence and baseline history from a repo checkout. This skill teaches the archive/retrieval/governance lane split without overclaiming hosted or listed-live status.
triggers:
- agent-exporter
- archive shell
- governance evidence
- semantic retrieval
- hybrid retrieval
- local stdio mcp
---

# agent-exporter Archive Governance Workbench

Use this skill when an agent needs to operate the local `agent-exporter` bridge from a repo checkout.

## What this skill teaches

- how to attach the local stdio bridge
- how to prove the bridge on a safe first-success path
- how to publish a local archive shell
- how to save local retrieval reports
- how to read governance evidence without claiming a hosted platform

## Product truth

- `agent-exporter` is a local-first archive and governance workbench
- the current primary surface is still `CLI-first`
- this OpenHands skill is a secondary public lane
- the bridge exposes archive, retrieval, and governance tools
- browser pages organize proof; they do not execute retrieval

## First-success flow

1. Wire the bridge from a local repo checkout.
2. Call `integration_evidence_policy_list` first.
3. If the workspace already has transcript HTML receipts, call `publish_archive_index`.
4. Move to retrieval or evidence comparison only after the bridge works.

## Example prompts

- "Attach the local agent-exporter bridge and list the available governance policies."
- "Publish the archive shell for this workspace and tell me where it landed."
- "Run semantic retrieval for this workspace and save a local report."
- "Compare two saved integration evidence snapshots and explain the readiness delta."

## Good truth language

- local stdio bridge
- secondary public lane
- archive and governance workbench

## Forbidden truth language

- hosted platform
- listed-live skill without fresh host read-back
- full CLI exposed through MCP
