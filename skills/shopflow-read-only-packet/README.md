# Shopflow Read-only Packet Public Skill

This folder is the public, self-contained skill packet for Shopflow's
read-only MCP surface and packet-oriented distribution lane.

Use it when you want one portable folder that teaches an agent four things:

- how to attach Shopflow's local read-only MCP server
- which capability packets are safe first
- what a good first-success packet loop looks like
- which claims stay outside the repo until a real listing or store publish
  exists

## What this packet includes

- `SKILL.md`
- `manifest.yaml`
- `references/README.md`
- `references/INSTALL.md`
- `references/OPENHANDS_MCP_CONFIG.json`
- `references/OPENCLAW_MCP_CONFIG.json`
- `references/CAPABILITIES.md`
- `references/DEMO.md`
- `references/TROUBLESHOOTING.md`

## Best-fit hosts

- OpenHands/extensions contribution flow
- ClawHub-style skill publication
- repo-local packet import flows that expect one standalone folder

## Current verified state

- the ClawHub skill listing is live
- the OpenHands/extensions lane is still folder-ready, not merged

## What this packet must not claim

- no live OpenHands/extensions listing without fresh PR or read-back
- no official registry, marketplace, or Chrome Web Store listing unless fresh
  receipt exists
- no hosted runtime or public HTTP MCP transport
