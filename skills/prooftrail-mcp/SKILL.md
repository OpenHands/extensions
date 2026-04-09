---
name: prooftrail-mcp
description: Teach an agent to install ProofTrail's governed stdio MCP server, use the safest read and proof tools first, and keep future package or listing claims honest.
version: 0.1.1
triggers:
  - prooftrail
  - prooftrail mcp
  - browser evidence
  - governed recovery
  - uiq proof
---

# ProofTrail MCP Skill

Teach the agent how to install, connect, and use ProofTrail's governed MCP
surface as a browser-evidence and recovery layer.

## Use this skill when

- the host can attach a local stdio MCP server from a repo checkout
- the user needs governed browser-evidence reads before broad automation
- the operator wants a truthful packet that separates current repo-native MCP
  from future package or Docker publication

## What this package teaches

- how to launch ProofTrail's current repo-native MCP server
- how to choose the safest ProofTrail tool families first
- how to move from catalog and read tools into governed run or proof tools
- how to talk about future npm, Docker, or registry surfaces without
  overclaiming publication

## What ProofTrail is

ProofTrail is an evidence-first browser automation and recovery layer.

It helps AI agents and human operators:

- run browser workflows through a governed path
- inspect retained evidence after each run
- recover from failures without pretending the browser layer is a generic bot

## Start here

1. Read [references/INSTALL.md](references/INSTALL.md)
2. Load the right host config from:
   - [references/OPENHANDS_MCP_CONFIG.json](references/OPENHANDS_MCP_CONFIG.json)
   - [references/OPENCLAW_MCP_CONFIG.json](references/OPENCLAW_MCP_CONFIG.json)
3. Skim the tool surface in [references/CAPABILITIES.md](references/CAPABILITIES.md)
4. Run the first-success path in [references/DEMO.md](references/DEMO.md)

## Safe-first workflow

1. `uiq_catalog`
2. `uiq_read`
3. `uiq_quality_read`
4. `uiq_proof`
5. only then widen into:
   - `uiq_run`
   - `uiq_run_and_report`
   - `uiq_api_workflow`
   - `uiq_api_automation`

## Suggested first prompt

Use ProofTrail as a governed browser-evidence layer. Start with `uiq_catalog`
to confirm the MCP surface is attached. Then use `uiq_read` or
`uiq_quality_read` to inspect one existing run or failure surface. If a real run
is already present, follow with `uiq_proof` or `uiq_run_and_report` to show the
retained evidence and summarize the most important next action.

## Current / usable today

Current install path:

1. clone the ProofTrail repo
2. run `pnpm install`
3. point your MCP client at the repo-local stdio command
4. start the MCP bridge with `pnpm mcp:start`

Protocol and auth truth:

- auth = `local-with-optional-backend-token`

## Publish-ready but not yet published

The following install surfaces are planned and not yet published:

- npm package: `@prooftrail/mcp-server`
- Docker image: `ghcr.io/xiaojiou176-open/prooftrail-mcp-server:0.1.1`

Do not describe either surface as live until the package or image is actually
published.

## Success checks

- the host attaches the repo-native MCP server successfully
- the agent cites a real run, artifact, or proof bundle instead of describing a
  generic browser story
- the answer stays grounded in evidence instead of free-writing from memory

## Boundaries

- this packet is not an official plugin
- ProofTrail is not a hosted service
- ProofTrail is not a hosted SaaS service
- ProofTrail is not a hosted MCP endpoint
- this packet does not claim a live OpenHands or ClawHub listing
- future npm or Docker shapes are publish-ready but not yet published

## Local references

- [references/INSTALL.md](references/INSTALL.md)
- [references/CAPABILITIES.md](references/CAPABILITIES.md)
- [references/DEMO.md](references/DEMO.md)
- [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md)
