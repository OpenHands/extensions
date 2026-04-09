# Shopflow MCP Troubleshooting

Use these checks before escalating.

## 1. MCP will not start

- run `pnpm install`
- run `pnpm mcp:stdio`
- confirm the command is being run from the real Shopflow repo root

## 2. Capability packets look stale

- rerun the packet-generating commands documented in `docs/ecosystem/examples/`
- re-check `docs/ecosystem/examples/public-mcp-capability-map.json`
- re-check `docs/ecosystem/examples/public-distribution-bundle.ready.md`

## 3. The wording sounds stronger than reality

Stop and re-check:

- `DISTRIBUTION.md`
- `docs/ecosystem/openclaw-comparison.md`
- `docs/ecosystem/public-distribution-bundle.ready.md`

Do not say ClawHub, OpenHands, registry, or Chrome Web Store are live unless
fresh receipts exist.
