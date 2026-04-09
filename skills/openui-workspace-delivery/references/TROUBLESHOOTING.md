# OpenUI MCP Studio Troubleshooting

Use these checks before escalating.

## 1. Build output path is missing

- run `npm install`
- run `npm run build`
- confirm `.runtime-cache/build/mcp-server/services/mcp-server/src/main.js`
  exists

## 2. Gemini key is missing

- provide `GEMINI_API_KEY` in the host config
- rerun any local env check you rely on before attaching again

## 3. You only need the shortest proof loop

- run `openui-mcp-studio surface-guide --json`
- run `openui-mcp-studio ecosystem-guide --json`
- run `npm run repo:doctor`

## 4. The claim sounds bigger than reality

Stop and re-check:

- `DISTRIBUTION.md`
- `INTEGRATIONS.md`
- `manifest.yaml`

Do not claim ClawHub, official marketplace, or hosted runtime status unless
fresh read-back exists.
