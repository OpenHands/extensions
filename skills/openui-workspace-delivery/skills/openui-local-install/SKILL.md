# OpenUI local install

You are using the repo-owned OpenUI install helper bundle.

## Goal

Help the operator wire OpenUI MCP Studio into a local Claude Code or OpenClaw
flow without overclaiming a hosted runtime or official listing.

## Read first

- `packages/skills-kit/starter-bundles/claude-code.mcp.json`
- `packages/skills-kit/starter-bundles/openclaw.mcp.json`
- `packages/skills-kit/starter-troubleshooting.md`
- `docs/proof-and-faq.md`

## Default route

1. Confirm the repo build output exists.
2. Copy the starter bundle JSON and replace the absolute repo path.
3. Run the proof loop:
   - `openui-mcp-studio surface-guide --json`
   - `openui-mcp-studio ecosystem-guide --json`
   - `npm run repo:doctor`
4. Escalate only if the runtime path or host attach still fails after the
   troubleshooting note has been followed.

## Boundaries

- Treat this as repo-owned install/proof help.
- Do not claim Anthropic marketplace publication or ClawHub publication.
- Do not claim a managed runtime or a hosted API deployment.
