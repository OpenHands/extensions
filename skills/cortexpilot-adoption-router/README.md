# CortexPilot Adoption Router

This public skill package exposes the current CortexPilot adoption router as a
registry-friendly skill surface.

It is designed for host ecosystems that want a single skill folder with a
`SKILL.md` contract and semver-friendly manifest.

## What it does

- routes operators to the right CortexPilot adoption lane
- keeps read-only MCP vs starter vs builder boundaries honest
- points back to the current public repo and Pages front door

## What it does not claim

- no hosted operator service
- no write-capable public MCP
- no live marketplace / registry listing unless independently confirmed
