# Switchyard MCP Troubleshooting

Use these checks before escalating.

## 1. MCP will not start

- run `pnpm install`
- run `pnpm run test:mcp:smoke`
- confirm the runtime base URL is reachable

## 2. The provider looks empty

- run `switchyard.providers.list`
- confirm you chose the right provider name
- run `switchyard.provider.status` before asking for deeper diagnostics

## 3. The answer sounds too strong

Stop and re-check:

- `DISTRIBUTION.md`
- `INTEGRATIONS.md`
- `docs/api/mcp-readonly-server.md`

If the wording drifts from `partial`, `read-only`, or `package-ready`, the
packet is overclaiming.
