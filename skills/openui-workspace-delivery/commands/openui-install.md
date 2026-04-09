# OpenUI install

Use this bundle when you want the shortest honest path to add OpenUI MCP Studio
to a local Claude Code or OpenClaw workflow.

1. Build the repo if the runtime path is missing.
   - `npm install`
   - `npm run build`
2. Open the repo-owned starter bundles.
   - `packages/skills-kit/starter-bundles/claude-code.mcp.json`
   - `packages/skills-kit/starter-bundles/openclaw.mcp.json`
3. Copy the starter JSON into your local host config and replace
   `/ABS/PATH/openui-mcp-studio` with the real checkout path.
4. Keep the truth boundary visible.
   - This bundle helps with install and proof.
   - It does not prove an official marketplace listing or hosted runtime.
