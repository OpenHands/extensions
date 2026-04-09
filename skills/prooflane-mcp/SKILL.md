# Prooflane MCP Skill

Use this skill when an agent needs to **clone, install, configure, verify, and
use Prooflane's current MCP and local product surfaces** without overclaiming
package-registry or hosted distribution that does not exist yet.

## Use When

- You want to evaluate Prooflane from the canonical public repository.
- You want to connect Codex, Claude Code, OpenClaw, or another MCP-capable
  client to Prooflane's repo-native MCP server.
- You need a truthful walkthrough for local UI first-look, MCP setup, and
  governed run verification.

## Truthful Boundaries

- Prooflane is public and distribution-ready on GitHub today.
- The MCP server is real and repo-native today.
- The package shape `@uiq/mcp-server` / `prooflane-mcp` is publish-ready, but
  it is **not published to npm yet**.
- MCP today means **stdio only**.
- Local stdio startup does **not** use OAuth; protected HTTP/API and
  automation surfaces keep the existing token/header contract.
- Prooflane is **not** currently a hosted SaaS service.
- This skill is a generic in-repo scaffold. It is **not** a published skill
  marketplace artifact yet.

## Prerequisites

- Git
- Node.js 20+
- pnpm
- Python 3.12+
- A local shell session in the repository root

## Canonical Repo

```bash
git clone https://github.com/xiaojiou176-open/ui-automation-control-plane.git
cd ui-automation-control-plane
```

## Install

```bash
./scripts/setup.sh
```

If you already trust the workspace toolchain and only need JS dependencies:

```bash
pnpm install
```

## First Local Product Win

Launch the local stress-lab shell:

```bash
./scripts/dev-up.sh
```

What success looks like:

- Command Center on `http://127.0.0.1:17373`
- API health on `http://127.0.0.1:17380/health/`
- A visible Stress Lab surface with Runs & Blocks, Flow Studio, and Advanced Review

## Repo-Native MCP Start (Today)

Start the current MCP server from the repository:

```bash
pnpm mcp:start
```

This is the truthful installation path today.

## Publish-Ready Package Shape (Not Published Yet)

Once the MCP package is actually published, the intended command shape is:

```bash
npx -y @uiq/mcp-server
```

or:

```bash
pnpm dlx @uiq/mcp-server
```

Do **not** claim this package is published until registry publication really happens.

## Minimal MCP Client Configuration

### Repo-native today

```json
{
  "mcpServers": {
    "uiq": {
      "command": "pnpm",
      "args": ["mcp:start"],
      "cwd": "/ABSOLUTE/PATH/TO/REPO",
      "env": {
        "UIQ_MCP_API_BASE_URL": "http://127.0.0.1:18080",
        "UIQ_MCP_TOOL_GROUPS": "advanced,analysis,proof"
      }
    }
  }
}
```

### Publish-ready package shape (not live yet)

```json
{
  "mcpServers": {
    "uiq": {
      "command": "npx",
      "args": ["-y", "@uiq/mcp-server"],
      "env": {
        "UIQ_MCP_API_BASE_URL": "http://127.0.0.1:18080",
        "UIQ_MCP_TOOL_GROUPS": "advanced,analysis,proof"
      }
    }
  }
}
```

## Environment Variables

- `UIQ_MCP_API_BASE_URL`
  Use this to point MCP at a different backend lane.
- `UIQ_MCP_TOOL_GROUPS`
  Use this to opt into optional MCP tool groups.
- `UIQ_MCP_PERFECT_MODE`
  Keeps stricter MCP defaults.
- `AUTOMATION_API_TOKEN`
  Needed only when token-protected HTTP/API surfaces are enabled.

## Minimal Verification

Run these from the repo root:

```bash
pnpm mcp:check
pnpm mcp:build
pnpm mcp:package:smoke
pnpm mcp:doc:contract
pnpm mcp:smoke
```

Expected result:

- TypeScript check passes
- build emits `services/mcp-server/dist/`
- package smoke keeps the stdio server alive through startup
- docs contract passes
- MCP smoke passes

## Start here

1. Read [references/INSTALL.md](references/INSTALL.md)
2. Load the right host config from:
   - [references/OPENHANDS_MCP_CONFIG.json](references/OPENHANDS_MCP_CONFIG.json)
   - [references/OPENCLAW_MCP_CONFIG.json](references/OPENCLAW_MCP_CONFIG.json)
3. Skim the tool surface in [references/CAPABILITIES.md](references/CAPABILITIES.md)
4. Run the first review loop from [references/DEMO.md](references/DEMO.md)
5. If attach or proof fails, use
   [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md)
